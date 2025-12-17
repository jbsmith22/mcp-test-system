#!/usr/bin/env python3
"""
Deploy Complete MCP-Compatible Lambda Function
This Lambda acts as the MCP server backend, accessible via API Gateway
"""

import boto3
import json
import zipfile
import io
import os

def create_mcp_lambda_code():
    """Create the complete MCP-compatible Lambda function"""
    
    lambda_code = '''
import json
import boto3
import requests
import os
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from typing import Dict, List, Any, Optional

# Configuration
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT', 'https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com')
INDEX_NAME = os.environ.get('INDEX_NAME', 'nejm-articles')
BEDROCK_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)
secrets_client = boto3.client('secretsmanager', region_name=BEDROCK_REGION)

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json'
}


class NEJMResearchEngine:
    """Complete NEJM Research Assistant with RAG, vector search, and article management"""
    
    def __init__(self):
        self.opensearch_endpoint = OPENSEARCH_ENDPOINT
        self.index_name = INDEX_NAME
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
    
    def _opensearch_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated request to OpenSearch"""
        url = f"{self.opensearch_endpoint}{path}"
        request = AWSRequest(method=method, url=url, data=json.dumps(data) if data else None)
        if data:
            request.headers['Content-Type'] = 'application/json'
        SigV4Auth(self.credentials, 'es', BEDROCK_REGION).add_auth(request)
        
        if method == 'GET':
            response = requests.get(url, headers=dict(request.headers))
        else:
            response = requests.post(url, headers=dict(request.headers), data=json.dumps(data) if data else None)
        
        response.raise_for_status()
        return response.json()
    
    def get_embedding(self, text: str) -> Dict:
        """Get embedding from Bedrock Titan"""
        try:
            response = bedrock_runtime.invoke_model(
                modelId='amazon.titan-embed-text-v1',
                body=json.dumps({"inputText": text})
            )
            result = json.loads(response['body'].read())
            embedding = result['embedding']
            
            return {
                "vector": embedding,
                "dimension": len(embedding),
                "model": "amazon.titan-embed-text-v1",
                "text_length": len(text),
                "vector_norm": sum(x*x for x in embedding) ** 0.5
            }
        except Exception as e:
            return {"error": str(e)}
    
    def search_articles(self, query: str, limit: int = 10, threshold: float = 0.5) -> Dict:
        """Search articles with full vector visibility"""
        
        # Get query embedding
        query_emb = self.get_embedding(query)
        if "error" in query_emb:
            return {"error": f"Failed to get embedding: {query_emb['error']}"}
        
        # Search OpenSearch - using text search with vector embedding info
        try:
            search_body = {
                "size": limit,
                "_source": ["title", "doi", "abstract", "year", "source", "content", "api_metadata"],
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "abstract^2", "content"]
                    }
                }
            }
            
            results = self._opensearch_request('POST', f'/{self.index_name}/_search', search_body)
            hits = results.get('hits', {}).get('hits', [])
            
            # Group by article
            articles = {}
            for hit in hits:
                score = hit['_score']  # k-NN score is already normalized
                if score < threshold:
                    continue
                
                source = hit['_source']
                doi = source.get('doi', '')
                title = source.get('title', 'Unknown')
                key = doi if doi else title
                
                if key not in articles or score > articles[key]['score']:
                    articles[key] = {
                        "title": title,
                        "doi": doi,
                        "year": source.get('year'),
                        "source": source.get('source', 'unknown'),
                        "relevance_score": round(score * 100, 2),
                        "abstract": source.get('abstract', '')[:300],
                        "score": score
                    }
            
            sorted_articles = sorted(articles.values(), key=lambda x: x['score'], reverse=True)
            
            return {
                "query": {
                    "text": query,
                    "embedding": {
                        "model": query_emb["model"],
                        "dimension": query_emb["dimension"],
                        "vector_norm": query_emb["vector_norm"],
                        "vector_preview": query_emb["vector"][:10]
                    }
                },
                "results": sorted_articles[:limit],
                "total_found": len(sorted_articles),
                "search_params": {
                    "limit": limit,
                    "threshold": threshold
                }
            }
        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}
    
    def ask_research_question(self, question: str, limit: int = 10, threshold: float = 0.4) -> Dict:
        """Ask research question with AI-generated answer"""
        
        # Search for relevant articles
        search_result = self.search_articles(question, limit, threshold)
        
        if "error" in search_result:
            return search_result
        
        if not search_result["results"]:
            return {"error": "No relevant articles found"}
        
        # Build context from results
        context_parts = []
        for i, article in enumerate(search_result["results"][:5], 1):
            context_parts.append(
                f"[Source {i}] {article['title']} ({article['relevance_score']}% relevant): "
                f"{article['abstract']}"
            )
        
        context = "\\n\\n".join(context_parts)
        
        # Generate answer with Claude
        try:
            prompt = f"""Based on the following medical research sources, please answer this question: {question}

Sources:
{context}

Please provide a comprehensive answer based on these sources. Be specific and cite which sources support your points."""
            
            response = bedrock_runtime.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            answer = result['content'][0]['text']
            
            return {
                "question": question,
                "answer": answer,
                "sources": search_result["results"][:5],
                "total_sources": len(search_result["results"]),
                "query_embedding": search_result["query"]["embedding"]
            }
        except Exception as e:
            return {"error": f"Failed to generate answer: {str(e)}"}
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            # Get total count
            count_result = self._opensearch_request('POST', f'/{self.index_name}/_count', {"query": {"match_all": {}}})
            total_count = count_result.get('count', 0)
            
            # Get source breakdown
            agg_body = {
                "size": 0,
                "aggs": {
                    "sources": {
                        "terms": {"field": "source.keyword", "size": 20}
                    }
                }
            }
            agg_result = self._opensearch_request('POST', f'/{self.index_name}/_search', agg_body)
            
            sources = {}
            for bucket in agg_result.get('aggregations', {}).get('sources', {}).get('buckets', []):
                sources[bucket['key']] = bucket['doc_count']
            
            return {
                "total_articles": total_count,
                "sources": sources,
                "index_name": self.index_name,
                "status": "healthy"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_article_by_doi(self, doi: str) -> Dict:
        """Get article by DOI"""
        try:
            search_body = {
                "query": {"term": {"doi.keyword": doi}},
                "size": 1
            }
            
            result = self._opensearch_request('POST', f'/{self.index_name}/_search', search_body)
            hits = result.get('hits', {}).get('hits', [])
            
            if not hits:
                return {"error": f"Article not found: {doi}"}
            
            article = hits[0]['_source']
            return {
                "doi": doi,
                "title": article.get('title', ''),
                "abstract": article.get('abstract', ''),
                "year": article.get('year'),
                "source": article.get('source'),
                "content": article.get('content', '')[:1000]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def compare_embeddings(self, text1: str, text2: str) -> Dict:
        """Compare embeddings between two texts"""
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        
        if "error" in emb1 or "error" in emb2:
            return {"error": "Failed to get embeddings"}
        
        vec1 = emb1["vector"]
        vec2 = emb2["vector"]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        similarity = dot_product / (emb1["vector_norm"] * emb2["vector_norm"])
        
        return {
            "text1": {"content": text1, "norm": emb1["vector_norm"], "preview": vec1[:10]},
            "text2": {"content": text2, "norm": emb2["vector_norm"], "preview": vec2[:10]},
            "similarity": similarity,
            "similarity_percent": round(similarity * 100, 2)
        }


# Initialize engine
engine = NEJMResearchEngine()


def lambda_handler(event, context):
    """Main Lambda handler - routes to appropriate tool"""
    
    # Handle OPTIONS for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'message': 'CORS preflight'})}
    
    try:
        # Parse request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        tool = body.get('tool', body.get('type', 'search'))
        
        print(f"Tool requested: {tool}")
        print(f"Request body: {json.dumps(body)}")
        
        # Route to appropriate handler
        if tool == 'search_articles' or tool == 'search':
            result = engine.search_articles(
                body.get('query', ''),
                body.get('limit', 10),
                body.get('threshold', 0.5)
            )
        
        elif tool == 'ask_research_question' or tool == 'ask':
            result = engine.ask_research_question(
                body.get('question', body.get('query', '')),
                body.get('limit', 10),
                body.get('threshold', 0.4)
            )
        
        elif tool == 'get_database_stats' or tool == 'statistics' or tool == 'stats':
            result = engine.get_database_stats()
        
        elif tool == 'get_article_by_doi':
            result = engine.get_article_by_doi(body.get('doi', ''))
        
        elif tool == 'compare_embeddings':
            result = engine.compare_embeddings(
                body.get('text1', ''),
                body.get('text2', '')
            )
        
        else:
            result = {"error": f"Unknown tool: {tool}"}
        
        # Return response
        if "error" in result:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps(result)
            }
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
'''
    
    return lambda_code


def deploy_lambda():
    """Deploy the MCP Lambda function"""
    
    print("🚀 Deploying MCP-Compatible Lambda Function...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create Lambda code
    lambda_code = create_mcp_lambda_code()
    
    # Create ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', lambda_code)
    
    zip_buffer.seek(0)
    
    # Update Lambda function
    try:
        response = lambda_client.update_function_code(
            FunctionName='nejm-research-assistant',
            ZipFile=zip_buffer.read()
        )
        
        print(f"✅ Lambda function updated successfully")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Runtime: {response['Runtime']}")
        print(f"   Last Modified: {response['LastModified']}")
        
        # Update environment variables
        lambda_client.update_function_configuration(
            FunctionName='nejm-research-assistant',
            Timeout=120,
            MemorySize=512,
            Environment={
                'Variables': {
                    'OPENSEARCH_ENDPOINT': 'https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com',
                    'INDEX_NAME': 'nejm-articles'
                }
            }
        )
        
        print("✅ Lambda configuration updated")
        print("\n📋 Available Tools (via API Gateway):")
        print("   - search_articles: Semantic search with vector visibility")
        print("   - ask_research_question: AI-powered Q&A with Claude")
        print("   - get_database_stats: Database statistics")
        print("   - get_article_by_doi: Retrieve specific article")
        print("   - compare_embeddings: Compare text embeddings")
        
        print("\n🌐 API Endpoint:")
        print("   https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research")
        
        print("\n📝 Example Usage:")
        print("""
curl -X POST https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research \\
  -H "Content-Type: application/json" \\
  -d '{
    "tool": "search_articles",
    "query": "AI in clinical documentation",
    "limit": 5
  }'
        """)
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying Lambda: {e}")
        return False


if __name__ == "__main__":
    deploy_lambda()
