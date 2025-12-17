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
import time
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
        """Search articles with full vector visibility and debug info"""
        
        debug_info = {
            "embedding_generation": {},
            "opensearch_query": {},
            "result_processing": {}
        }
        
        # Step 1: Get query embedding
        print(f"🔢 Generating embedding for query: '{query}'")
        embedding_start = time.time()
        query_emb = self.get_embedding(query)
        embedding_duration = time.time() - embedding_start
        
        debug_info["embedding_generation"] = {
            "query_text": query,
            "query_length": len(query),
            "duration_ms": round(embedding_duration * 1000, 2),
            "successful": "error" not in query_emb
        }
        
        if "error" in query_emb:
            debug_info["embedding_generation"]["error"] = query_emb["error"]
            return {"error": f"Failed to get embedding: {query_emb['error']}", "debug_info": debug_info}
        
        debug_info["embedding_generation"].update({
            "model": query_emb["model"],
            "dimension": query_emb["dimension"],
            "vector_norm": query_emb["vector_norm"],
            "vector_preview": query_emb["vector"][:10]
        })
        
        # Step 2: Search OpenSearch with hybrid approach (vector + text)
        print(f"🔍 Searching OpenSearch with hybrid vector + text search")
        search_start = time.time()
        
        try:
            # Try k-NN vector search first, fall back to text search if it fails
            # OpenSearch k-NN syntax - try different approaches
            vector_search_body = {
                "size": limit,
                "_source": ["title", "doi", "abstract", "year", "source", "content", "api_metadata"],
                "query": {
                    "bool": {
                        "should": [
                            {
                                "knn": {
                                    "vector": {
                                        "vector": query_emb["vector"],
                                        "k": limit * 2
                                    }
                                }
                            },
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^3", "abstract^2", "content"],
                                    "boost": 0.3
                                }
                            }
                        ]
                    }
                }
            }
            
            debug_info["opensearch_query"] = {
                "index_name": self.index_name,
                "search_body": vector_search_body,
                "query_type": "hybrid_vector_text",
                "vector_dimensions": query_emb["dimension"],
                "fields_searched": ["embedding (k-NN)", "title^3", "abstract^2", "content"],
                "size_limit": limit,
                "k_value": limit * 2
            }
            
            try:
                # Try vector search first
                print(f"🔍 Attempting k-NN vector search with {len(query_emb['vector'])} dimensions")
                results = self._opensearch_request('POST', f'/{self.index_name}/_search', vector_search_body)
                print(f"✅ Vector search successful")
            except Exception as vector_error:
                print(f"⚠️ Vector search failed: {str(vector_error)}")
                
                # Let's try to get more details about the error and database structure
                try:
                    # Check if embedding field exists by looking at mapping
                    mapping_result = self._opensearch_request('GET', f'/{self.index_name}/_mapping')
                    print(f"📋 Index mapping retrieved")
                    
                    # Check if any documents have embeddings
                    sample_query = {
                        "size": 1,
                        "_source": ["title", "vector"],
                        "query": {"exists": {"field": "vector"}}
                    }
                    sample_result = self._opensearch_request('POST', f'/{self.index_name}/_search', sample_query)
                    embedding_docs = sample_result.get('hits', {}).get('total', {}).get('value', 0)
                    print(f"📊 Documents with embeddings: {embedding_docs}")
                    
                    # Also check what fields actually exist in documents
                    any_doc_query = {
                        "size": 1,
                        "query": {"match_all": {}}
                    }
                    any_doc_result = self._opensearch_request('POST', f'/{self.index_name}/_search', any_doc_query)
                    if any_doc_result.get('hits', {}).get('hits'):
                        sample_doc = any_doc_result['hits']['hits'][0]['_source']
                        available_fields = list(sample_doc.keys())
                        print(f"📋 Available fields in documents: {available_fields}")
                        debug_info["opensearch_query"]["available_fields"] = available_fields
                    
                    debug_info["opensearch_query"]["mapping_check"] = "success"
                    debug_info["opensearch_query"]["embedding_docs_count"] = embedding_docs
                    
                    if embedding_docs > 0:
                        sample_doc = sample_result.get('hits', {}).get('hits', [])
                        if sample_doc:
                            vector = sample_doc[0].get('_source', {}).get('vector')
                            if vector:
                                debug_info["opensearch_query"]["sample_vector_length"] = len(vector) if isinstance(vector, list) else "not_array"
                                debug_info["opensearch_query"]["sample_vector_type"] = type(vector).__name__
                                print(f"📏 Sample vector length: {len(vector) if isinstance(vector, list) else 'not array'}")
                    
                except Exception as debug_error:
                    print(f"🔍 Debug query failed: {str(debug_error)}")
                    debug_info["opensearch_query"]["debug_error"] = str(debug_error)
                
                # Fall back to text-only search
                text_search_body = {
                    "size": limit,
                    "_source": ["title", "doi", "abstract", "year", "source", "content", "api_metadata"],
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "abstract^2", "content"]
                        }
                    }
                }
                
                debug_info["opensearch_query"]["query_type"] = "text_fallback"
                debug_info["opensearch_query"]["search_body"] = text_search_body
                debug_info["opensearch_query"]["vector_error"] = str(vector_error)
                
                results = self._opensearch_request('POST', f'/{self.index_name}/_search', text_search_body)
            search_duration = time.time() - search_start
            
            debug_info["opensearch_query"]["duration_ms"] = round(search_duration * 1000, 2)
            debug_info["opensearch_query"]["raw_hits"] = len(results.get('hits', {}).get('hits', []))
            debug_info["opensearch_query"]["opensearch_response"] = {
                "took": results.get('took', 0),
                "timed_out": results.get('timed_out', False),
                "total_hits": results.get('hits', {}).get('total', {})
            }
            
            hits = results.get('hits', {}).get('hits', [])
            
            # Step 3: Process results
            print(f"📊 Processing {len(hits)} search results")
            processing_start = time.time()
            
            # Group by article
            articles = {}
            filtered_count = 0
            
            for i, hit in enumerate(hits):
                score = hit['_score']
                source = hit['_source']
                
                print(f"  📄 Hit {i+1}: {source.get('title', 'Unknown')[:50]}... (Score: {score:.3f})")
                
                if score < threshold:
                    filtered_count += 1
                    continue
                
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
                        "score": score,
                        "opensearch_score": score,
                        "full_abstract": source.get('abstract', ''),  # Keep full abstract for debug
                        "content": source.get('content', ''),  # Include FULL content for RAG
                        "content_preview": source.get('content', '')[:200] if source.get('content') else None  # Keep preview for display
                    }
            
            sorted_articles = sorted(articles.values(), key=lambda x: x['score'], reverse=True)
            processing_duration = time.time() - processing_start
            
            debug_info["result_processing"] = {
                "raw_hits": len(hits),
                "filtered_by_threshold": filtered_count,
                "unique_articles": len(articles),
                "final_results": len(sorted_articles[:limit]),
                "threshold_used": threshold,
                "duration_ms": round(processing_duration * 1000, 2),
                "score_distribution": {
                    "highest": max([a["score"] for a in sorted_articles]) if sorted_articles else 0,
                    "lowest": min([a["score"] for a in sorted_articles]) if sorted_articles else 0,
                    "average": sum([a["score"] for a in sorted_articles]) / len(sorted_articles) if sorted_articles else 0
                }
            }
            
            total_duration = embedding_duration + search_duration + processing_duration
            print(f"✅ Search completed in {total_duration:.2f}s, found {len(sorted_articles)} articles")
            
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
                },
                "debug_info": debug_info,
                "total_processing_time_ms": round(total_duration * 1000, 2)
            }
        except Exception as e:
            search_duration = time.time() - search_start
            debug_info["opensearch_query"]["duration_ms"] = round(search_duration * 1000, 2)
            debug_info["opensearch_query"]["error"] = str(e)
            return {"error": f"Search failed: {str(e)}", "debug_info": debug_info}
    def ask_research_question(self, question: str, limit: int = 10, threshold: float = 0.4) -> Dict:
        """Ask research question with AI-generated answer - with detailed debug info"""
        
        debug_info = {
            "step1_search": {},
            "step2_context_building": {},
            "step3_prompt_construction": {},
            "step4_llm_invocation": {},
            "step5_response_processing": {}
        }
        
        # Step 1: Search for relevant articles
        print(f"🔍 Step 1: Searching for articles with question: '{question}'")
        search_start = time.time()
        search_result = self.search_articles(question, limit, threshold)
        search_duration = time.time() - search_start
        
        debug_info["step1_search"] = {
            "question": question,
            "search_params": {"limit": limit, "threshold": threshold},
            "duration_ms": round(search_duration * 1000, 2),
            "articles_found": len(search_result.get("results", [])),
            "search_successful": "error" not in search_result
        }
        
        if "error" in search_result:
            debug_info["step1_search"]["error"] = search_result["error"]
            return {"error": search_result["error"], "debug_info": debug_info}
        
        if not search_result["results"]:
            debug_info["step1_search"]["error"] = "No relevant articles found"
            return {"error": "No relevant articles found", "debug_info": debug_info}
        
        # Step 2: Build context from results
        print(f"📚 Step 2: Building context from {len(search_result['results'])} articles")
        context_start = time.time()
        
        context_parts = []
        selected_articles = search_result["results"][:3]  # Top 3 articles with full content
        
        for i, article in enumerate(selected_articles, 1):
            # Include full article content for comprehensive RAG context
            full_content = ""
            # Use full content field (not the preview)
            content_field = article.get('content') or article.get('content_preview') or ""
            if content_field:
                # Use the FULL content, not just excerpts - this is what the local version did
                full_content = f"\\n\\nFull Article Content:\\n{content_field}"
            
            source_text = f"[Source {i}] {article['title']} ({article['relevance_score']}% relevant):\\n\\nAbstract: {article['abstract']}{full_content}"
            context_parts.append(source_text)
            print(f"  📄 Source {i}: {article['title'][:50]}... (Score: {article['relevance_score']}%)")
        
        context = "\\n\\n".join(context_parts)
        context_duration = time.time() - context_start
        
        debug_info["step2_context_building"] = {
            "articles_selected": len(selected_articles),
            "context_length_chars": len(context),
            "context_length_words": len(context.split()),
            "duration_ms": round(context_duration * 1000, 2),
            "articles_metadata": [
                {
                    "title": article["title"],
                    "relevance_score": article["relevance_score"],
                    "abstract_length": len(article["abstract"]),
                    "full_content_length": len(article.get("content", "") or article.get("content_preview", "")),
                    "doi": article.get("doi", "N/A")
                }
                for article in selected_articles
            ],
            "full_context": context,  # Include the actual context for debugging
            "content_approach": "full_article_content"  # Indicate we're using full content
        }
        
        # Step 3: Construct the prompt for Claude
        print(f"🤖 Step 3: Constructing prompt for Claude")
        prompt_start = time.time()
        
        prompt = f"""Based on the following medical research sources, please answer this question: {question}

Sources:
{context}

Please provide a comprehensive answer based on these sources. Be specific and cite which sources support your points."""
        
        prompt_duration = time.time() - prompt_start
        
        debug_info["step3_prompt_construction"] = {
            "question": question,
            "prompt_length_chars": len(prompt),
            "prompt_length_words": len(prompt.split()),
            "sources_included": len(selected_articles),
            "duration_ms": round(prompt_duration * 1000, 2),
            "full_prompt": prompt  # Include the actual prompt for debugging
        }
        
        # Step 4: Invoke Claude LLM
        print(f"🧠 Step 4: Invoking Claude 3.5 Sonnet")
        llm_start = time.time()
        
        try:
            bedrock_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = bedrock_runtime.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
                body=json.dumps(bedrock_request)
            )
            
            llm_duration = time.time() - llm_start
            
            debug_info["step4_llm_invocation"] = {
                "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "max_tokens": 2000,
                "duration_ms": round(llm_duration * 1000, 2),
                "request_successful": True,
                "bedrock_request": bedrock_request  # Include the actual request
            }
            
            # Step 5: Process Claude's response
            print(f"📝 Step 5: Processing Claude's response")
            processing_start = time.time()
            
            result = json.loads(response['body'].read())
            answer = result['content'][0]['text']
            
            processing_duration = time.time() - processing_start
            
            debug_info["step5_response_processing"] = {
                "answer_length_chars": len(answer),
                "answer_length_words": len(answer.split()),
                "duration_ms": round(processing_duration * 1000, 2),
                "claude_response_raw": result,  # Include Claude's raw response
                "final_answer": answer  # Include the processed answer
            }
            
            total_duration = search_duration + context_duration + prompt_duration + llm_duration + processing_duration
            
            print(f"✅ Research question completed in {total_duration:.2f}s")
            
            return {
                "question": question,
                "answer": answer,
                "sources": search_result["results"][:5],
                "total_sources": len(search_result["results"]),
                "query_embedding": search_result["query"]["embedding"],
                "debug_info": debug_info,
                "total_processing_time_ms": round(total_duration * 1000, 2)
            }
            
        except Exception as e:
            llm_duration = time.time() - llm_start
            debug_info["step4_llm_invocation"] = {
                "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "duration_ms": round(llm_duration * 1000, 2),
                "request_successful": False,
                "error": str(e)
            }
            return {"error": f"Failed to generate answer: {str(e)}", "debug_info": debug_info}
    def get_database_stats(self) -> Dict:
        """Get database statistics with enhanced source breakdown"""
        try:
            # Get total count
            count_result = self._opensearch_request('POST', f'/{self.index_name}/_count', {"query": {"match_all": {}}})
            total_count = count_result.get('count', 0)
            
            # Try multiple field variations for source breakdown
            source_fields_to_try = ["source.keyword", "source", "api_metadata.source"]
            sources = {}
            
            for field in source_fields_to_try:
                try:
                    agg_body = {
                        "size": 0,
                        "aggs": {
                            "sources": {
                                "terms": {"field": field, "size": 20}
                            }
                        }
                    }
                    agg_result = self._opensearch_request('POST', f'/{self.index_name}/_search', agg_body)
                    
                    buckets = agg_result.get('aggregations', {}).get('sources', {}).get('buckets', [])
                    if buckets:  # If we got results, use this field
                        for bucket in buckets:
                            sources[bucket['key']] = bucket['doc_count']
                        break  # Stop trying other fields
                except Exception as e:
                    print(f"Failed to aggregate on field {field}: {str(e)}")
                    continue
            
            # If aggregation failed, try a different approach - sample some documents
            if not sources:
                try:
                    sample_body = {
                        "size": 100,
                        "_source": ["source", "api_metadata.source"],
                        "query": {"match_all": {}}
                    }
                    sample_result = self._opensearch_request('POST', f'/{self.index_name}/_search', sample_body)
                    
                    source_counts = {}
                    for hit in sample_result.get('hits', {}).get('hits', []):
                        source_data = hit.get('_source', {})
                        source_value = (source_data.get('source') or 
                                      source_data.get('api_metadata', {}).get('source') or 
                                      'unknown')
                        source_counts[source_value] = source_counts.get(source_value, 0) + 1
                    
                    # Extrapolate to full dataset
                    sample_size = len(sample_result.get('hits', {}).get('hits', []))
                    if sample_size > 0:
                        for source_name, count in source_counts.items():
                            estimated_count = int((count / sample_size) * total_count)
                            sources[source_name] = estimated_count
                            
                except Exception as e:
                    print(f"Failed to sample documents for source breakdown: {str(e)}")
            
            # Calculate database size estimate (rough)
            database_size_mb = max(1, int(total_count * 0.1))  # Rough estimate: 100KB per article
            
            # Get vector dimensions from a sample document
            vector_dimensions = 1536  # Default for Titan
            try:
                sample_body = {
                    "size": 1,
                    "_source": ["embedding"],
                    "query": {"exists": {"field": "embedding"}}
                }
                sample_result = self._opensearch_request('POST', f'/{self.index_name}/_search', sample_body)
                hits = sample_result.get('hits', {}).get('hits', [])
                if hits and 'embedding' in hits[0].get('_source', {}):
                    embedding = hits[0]['_source']['embedding']
                    if isinstance(embedding, list):
                        vector_dimensions = len(embedding)
            except Exception as e:
                print(f"Failed to get vector dimensions: {str(e)}")
            
            return {
                "total_articles": total_count,
                "source_breakdown": sources,  # Changed from "sources" to "source_breakdown"
                "database_size_mb": database_size_mb,
                "vector_dimensions": vector_dimensions,
                "index_name": self.index_name,
                "status": "healthy",
                "embedding_model": "amazon.titan-embed-text-v1"
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
    
    def _get_nejm_credentials(self):
        """Get NEJM API credentials from AWS Secrets Manager"""
        try:
            response = secrets_client.get_secret_value(SecretId='nejm-api-credentials')
            credentials = json.loads(response['SecretString'])
            return f"{credentials['userid']}|{credentials['apikey']}"
        except Exception as e:
            print(f"❌ Could not get NEJM credentials: {e}")
            return None
    
    def _get_current_article_count_for_source(self, source: str) -> int:
        """Get current count of articles from this source in the database"""
        try:
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"source.keyword": f"nejm-api-{source}"}},
                            {"prefix": {"source.keyword": f"nejm-api-{source}"}}
                        ]
                    }
                },
                "size": 0
            }
            result = self._opensearch_request('POST', f'/{self.index_name}/_search', search_body)
            count = result.get('hits', {}).get('total', {}).get('value', 0)
            print(f"📊 Current database has {count} articles from source: {source}")
            return count
        except Exception as e:
            print(f"⚠️ Could not get current article count: {e}")
            return 0

    def _fetch_nejm_articles_with_offset(self, context: str, target_count: int, api_key: str) -> List[Dict]:
        """Fetch articles from NEJM API using smart offset to avoid duplicates"""
        user_id, key = api_key.split('|', 1)
        headers = {
            "apiuser": user_id,
            "apikey": key
        }
        
        # Map source to proper context
        context_map = {
            "nejm": "nejm",
            "nejm-ai": "nejm-ai", 
            "catalyst": "catalyst",
            "clinician": "clinician",
            "evidence": "evidence"
        }
        api_context = context_map.get(context, "nejm-ai")
        
        endpoint = "https://onesearch-api.nejmgroup-qa.org/api/v1/simple"
        
        # Get current count to calculate offset
        current_count = self._get_current_article_count_for_source(context)
        
        # Strategy: First try to get new articles (page 1), then use offset for older articles
        collected_articles = []
        
        print(f"🎯 Strategy: Get {target_count} articles from {context}")
        print(f"   Current database has {current_count} articles from this source")
        
        # Step 1: Try to get newest articles first (they're most likely to be new)
        print(f"📥 Step 1: Fetching newest articles...")
        
        params = {
            "context": api_context,
            "objectType": f"{api_context}-article",
            "sortBy": "pubdate-descending",
            "pageLength": min(target_count * 2, 50),  # Get extra to account for potential duplicates
            "startPage": 1,
            "showFacets": "N"
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                newest_articles = data.get('results', [])
                print(f"   📄 Got {len(newest_articles)} newest articles")
                
                # Filter out duplicates from newest articles
                for article in newest_articles:
                    doi = article.get('doi', '')
                    title = article.get('text', article.get('title', ''))
                    
                    if not self._check_article_exists(doi, title):
                        collected_articles.append(article)
                        print(f"   ✅ New article: {title[:50]}...")
                        
                        if len(collected_articles) >= target_count:
                            break
                
                print(f"   📊 Found {len(collected_articles)} new articles from newest batch")
        
        except Exception as e:
            print(f"   ❌ Error fetching newest articles: {e}")
        
        # Step 2: If we need more articles, use offset to get older ones
        if len(collected_articles) < target_count:
            remaining_needed = target_count - len(collected_articles)
            print(f"📥 Step 2: Need {remaining_needed} more articles, using offset...")
            
            # Calculate starting page based on current database count
            # Each page has ~50 articles, so start after what we likely have
            offset_page = max(1, (current_count // 50) + 1)
            
            print(f"   🔍 Starting from page {offset_page} (offset for {current_count} existing articles)")
            
            pages_to_try = 3  # Try a few pages to get enough articles
            
            for page_offset in range(pages_to_try):
                current_page = offset_page + page_offset
                
                params = {
                    "context": api_context,
                    "objectType": f"{api_context}-article",
                    "sortBy": "pubdate-descending",
                    "pageLength": 50,
                    "startPage": current_page,
                    "showFacets": "N"
                }
                
                try:
                    response = requests.get(endpoint, params=params, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        offset_articles = data.get('results', [])
                        
                        if not offset_articles:
                            print(f"   ⚠️ No more articles available at page {current_page}")
                            break
                        
                        print(f"   📄 Page {current_page}: Got {len(offset_articles)} articles")
                        
                        # Add articles (they should be older and not in our database)
                        page_added = 0
                        for article in offset_articles:
                            doi = article.get('doi', '')
                            title = article.get('text', article.get('title', ''))
                            
                            # Quick check - but older articles are less likely to be duplicates
                            if not self._check_article_exists(doi, title):
                                collected_articles.append(article)
                                page_added += 1
                                print(f"   ✅ Older article: {title[:50]}...")
                                
                                if len(collected_articles) >= target_count:
                                    break
                        
                        print(f"   📊 Added {page_added} articles from page {current_page}")
                        
                        if len(collected_articles) >= target_count:
                            break
                        
                        # Small delay between requests
                        time.sleep(0.3)
                        
                    else:
                        print(f"   ❌ API error on page {current_page}: {response.status_code}")
                        break
                        
                except Exception as e:
                    print(f"   ❌ Error fetching page {current_page}: {e}")
                    break
        
        final_count = len(collected_articles)
        print(f"✅ Collection complete: Found {final_count} articles for ingestion")
        
        return collected_articles[:target_count]
    
    def _fetch_nejm_articles(self, context: str, count: int, api_key: str) -> List[Dict]:
        """Fetch articles using smart offset strategy"""
        return self._fetch_nejm_articles_with_offset(context, count, api_key)
    
    def _process_nejm_article(self, raw_article: Dict, source: str) -> Dict:
        """Process raw NEJM API article into our format"""
        # Extract metadata from NEJM API response
        title = raw_article.get('text', raw_article.get('title', 'Unknown Title'))
        abstract = raw_article.get('displayAbstract', raw_article.get('abstract', ''))
        doi = raw_article.get('doi', '')
        
        # Extract year from pubdate
        year = "2025"  # Default
        if raw_article.get('pubdate'):
            try:
                date_str = str(raw_article['pubdate'])
                if len(date_str) >= 4 and date_str[:4].isdigit():
                    year = date_str[:4]
            except (ValueError, TypeError):
                pass
        
        # Build content from available fields
        content_parts = []
        if title:
            content_parts.append(f"Title: {title}")
        if abstract:
            content_parts.append(f"Abstract: {abstract}")
        
        # Add any additional text content from the API response
        if raw_article.get('snippet'):
            content_parts.append(f"Snippet: {raw_article['snippet']}")
        
        # Try to get full content if DOI is available
        if doi:
            try:
                full_content = self._fetch_full_article_content(doi, source)
                if full_content:
                    content_parts.append(f"Full Content: {full_content}")
            except Exception as e:
                print(f"    Note: Could not fetch full content for {doi}: {e}")
        
        content = "\\n\\n".join(content_parts)
        
        # Create a more unique ID to avoid conflicts
        import uuid
        unique_id = str(uuid.uuid4())
        
        return {
            "id": unique_id,
            "title": title,
            "abstract": abstract,
            "content": content,
            "doi": doi,
            "year": year,
            "source": f"nejm-api-{source}",
            "authors": raw_article.get('authors', []) if isinstance(raw_article.get('authors'), list) else [],
            "publication": raw_article.get('publication', source.upper()),
            "volume": str(raw_article.get('volume', '')),
            "issue": str(raw_article.get('issue', '')),
            "ingestion_timestamp": time.time(),
            "content_format": "nejm_api_real",
            "api_metadata": {k: v for k, v in raw_article.items() if isinstance(v, (str, int, float, bool, list, dict))}  # Clean metadata
        }
    
    def _fetch_full_article_content(self, doi: str, context: str) -> str:
        """Fetch full article content using NEJM content API"""
        api_key = self._get_nejm_credentials()
        if not api_key:
            return ""
        
        user_id, key = api_key.split('|', 1)
        headers = {
            "apiuser": user_id,
            "apikey": key
        }
        
        endpoint = "https://onesearch-api.nejmgroup-qa.org/api/v1/content"
        params = {
            "context": context,
            "doi": doi,
            "format": "json"
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                document = data.get('document', '')
                # Extract text from JATS XML document (simplified)
                if document:
                    # Basic text extraction - in production, you'd parse XML properly
                    import re
                    text = re.sub(r'<[^>]+>', ' ', document)  # Remove XML tags
                    text = re.sub(r'\\s+', ' ', text).strip()  # Clean whitespace
                    return text[:8000]  # Limit for embedding
            return ""
        except Exception as e:
            print(f"    Warning: Could not fetch full content for {doi}: {e}")
            return ""

    def _check_article_exists(self, doi: str, title: str) -> bool:
        """Check if article already exists in database (optimized)"""
        try:
            # Only check by DOI if available (faster and more reliable)
            if doi:
                search_body = {
                    "query": {"term": {"doi.keyword": doi}},
                    "size": 0  # We only need the count, not the documents
                }
                result = self._opensearch_request('POST', f'/{self.index_name}/_search', search_body)
                return result.get('hits', {}).get('total', {}).get('value', 0) > 0
            
            # Skip title check for performance - DOI is more reliable anyway
            return False
            
        except Exception as e:
            # If we can't check, assume it doesn't exist to avoid blocking ingestion
            return False

    def ingest_articles(self, source: str = "nejm", count: int = 10) -> Dict:
        """Ingest new articles from NEJM API with automatic vectorization"""
        try:
            print(f"🔄 Starting real NEJM API ingestion of {count} articles from {source}")
            
            # Get NEJM API credentials
            api_key = self._get_nejm_credentials()
            if not api_key:
                return {"error": "NEJM API credentials not available in AWS Secrets Manager"}
            
            # Fetch unique articles from NEJM API (already filtered for duplicates)
            raw_articles = self._fetch_nejm_articles(source, count, api_key)
            if not raw_articles:
                return {"error": f"No new articles found from NEJM API for source: {source}. All recent articles may already be in the database."}
            
            print(f"📥 Found {len(raw_articles)} new unique articles from NEJM API")
            
            ingested_articles = []
            skipped_reasons = {
                "no_content": 0,
                "embedding_failed": 0,
                "indexing_failed": 0
            }
            
            # Process each unique article from NEJM API
            for i, raw_article in enumerate(raw_articles):
                print(f"  📄 Processing article {i+1}/{len(raw_articles)}: {raw_article.get('text', 'Unknown')[:50]}...")
                
                # Extract and format article data
                article = self._process_nejm_article(raw_article, source)
                
                # Check if article has content
                if not article['content'].strip():
                    print(f"    ⚠️ No content available, skipping")
                    skipped_reasons["no_content"] += 1
                    continue
                
                # Create embedding text - use full content up to Titan's limit
                full_content = article['content'][:8000] if article.get('content') else ''
                embedding_text = f"Title: {article['title']} Abstract: {article['abstract']} Content: {full_content}"
                
                # Generate vector embedding
                print(f"    🔢 Generating embedding...")
                embedding_result = self.get_embedding(embedding_text)
                
                if "error" not in embedding_result:
                    article["vector"] = embedding_result["vector"]
                    article["vector_timestamp"] = time.time()
                    article["vector_model"] = embedding_result["model"]
                    print(f"    ✅ Vector generated ({embedding_result['dimension']} dimensions)")
                else:
                    print(f"    ❌ Vector generation failed: {embedding_result['error']}")
                    skipped_reasons["embedding_failed"] += 1
                    continue
                
                # Store in OpenSearch with retry logic
                indexed_successfully = False
                retry_count = 0
                max_retries = 2
                
                while not indexed_successfully and retry_count <= max_retries:
                    try:
                        # Clean the article data before indexing - be very conservative
                        clean_article = {
                            "title": str(article.get("title", "Unknown Title"))[:500],  # Conservative limit
                            "abstract": str(article.get("abstract", ""))[:1000],  # Conservative limit
                            "content": str(article.get("content", ""))[:5000],  # Conservative limit
                            "doi": str(article.get("doi", "")),
                            "year": str(article.get("year", "2025")),
                            "source": str(article.get("source", f"nejm-api-{source}")),
                            "authors": [],  # Simplify - empty array for now
                            "publication": str(article.get("publication", source.upper())),
                            "ingestion_timestamp": time.time(),
                            "content_format": "nejm_api_clean",
                            "vector": article["vector"] if "vector" in article and isinstance(article["vector"], list) else [],
                            "vector_timestamp": time.time(),
                            "vector_model": article.get("vector_model", "amazon.titan-embed-text-v1")
                        }
                        
                        # Ensure vector is valid
                        if not clean_article["vector"] or len(clean_article["vector"]) != 1536:
                            raise Exception(f"Invalid vector: length {len(clean_article.get('vector', []))}, expected 1536")
                        
                        # Index the article with vector (let OpenSearch generate ID)
                        index_result = self._opensearch_request('POST', f'/{self.index_name}/_doc', clean_article)
                        print(f"    ✅ Article indexed successfully")
                        
                        ingested_articles.append({
                            "title": article["title"][:100],  # Truncate for response
                            "doi": article["doi"],
                            "authors": article["authors"],
                            "vector_dimensions": len(article["vector"]),
                            "ingestion_status": "success"
                        })
                        
                        indexed_successfully = True
                        
                    except Exception as index_error:
                        retry_count += 1
                        error_msg = str(index_error)
                        print(f"    ❌ Indexing attempt {retry_count} failed: {error_msg[:200]}")
                        
                        if retry_count <= max_retries:
                            print(f"    🔄 Retrying in 1 second...")
                            time.sleep(1)
                        else:
                            print(f"    ❌ Final indexing failure after {max_retries} retries")
                            skipped_reasons["indexing_failed"] += 1
                
                # Small delay between articles
                time.sleep(0.5)
            
            # Create detailed summary
            total_processed = len(raw_articles)
            total_skipped = sum(skipped_reasons.values())
            
            print(f"📊 Ingestion Summary:")
            print(f"   Unique articles found: {total_processed}")
            print(f"   Successfully ingested: {len(ingested_articles)}")
            print(f"   Skipped - No content: {skipped_reasons['no_content']}")
            print(f"   Skipped - Embedding failed: {skipped_reasons['embedding_failed']}")
            print(f"   Skipped - Indexing failed: {skipped_reasons['indexing_failed']}")
            
            success_rate = (len(ingested_articles) / count * 100) if count > 0 else 0
            
            return {
                "source": source,
                "requested_count": count,
                "found_unique_count": total_processed,
                "ingested_count": len(ingested_articles),
                "skipped_count": total_skipped,
                "skip_reasons": skipped_reasons,
                "success_rate": round(success_rate, 1),
                "articles": ingested_articles,
                "status": "completed",
                "message": f"Successfully ingested {len(ingested_articles)} of {count} requested articles from {source} ({success_rate:.1f}% success rate)"
            }
            
        except Exception as e:
            return {"error": f"Ingestion failed: {str(e)}"}
    
    def vectorize_existing_articles(self, limit: int = 50) -> Dict:
        """Vectorize existing articles that don't have embeddings"""
        try:
            print(f"🔍 Finding articles without vectors (limit: {limit})")
            
            # Find articles without vectors
            query = {
                "size": limit,
                "_source": ["id", "title", "abstract", "content"],
                "query": {
                    "bool": {
                        "must_not": {
                            "exists": {"field": "vector"}
                        }
                    }
                }
            }
            
            result = self._opensearch_request('POST', f'/{self.index_name}/_search', query)
            hits = result.get('hits', {}).get('hits', [])
            
            if not hits:
                return {
                    "message": "All articles already have vectors",
                    "vectorized_count": 0,
                    "total_processed": 0
                }
            
            vectorized_count = 0
            failed_count = 0
            
            for hit in hits:
                article_id = hit['_id']
                source = hit['_source']
                
                print(f"  📄 Vectorizing: {source.get('title', 'Unknown')[:50]}...")
                
                # Create embedding text - use full content up to Titan's limit
                full_content = source.get('content', '')[:8000] if source.get('content') else ''
                embedding_text = f"Title: {source.get('title', '')} Abstract: {source.get('abstract', '')} Content: {full_content}"
                
                if not embedding_text.strip():
                    print(f"    ⚠️ No content to embed, skipping")
                    failed_count += 1
                    continue
                
                # Generate embedding
                embedding_result = self.get_embedding(embedding_text)
                
                if "error" in embedding_result:
                    print(f"    ❌ Vector generation failed")
                    failed_count += 1
                    continue
                
                # Update article with vector
                update_body = {
                    "doc": {
                        "vector": embedding_result["vector"],
                        "vector_timestamp": time.time(),
                        "vector_model": embedding_result["model"]
                    }
                }
                
                try:
                    self._opensearch_request('POST', f'/{self.index_name}/_update/{article_id}', update_body)
                    print(f"    ✅ Vector added ({embedding_result['dimension']} dimensions)")
                    vectorized_count += 1
                except Exception as update_error:
                    print(f"    ❌ Update failed: {str(update_error)}")
                    failed_count += 1
                
                # Small delay
                time.sleep(0.1)
            
            return {
                "total_processed": len(hits),
                "vectorized_count": vectorized_count,
                "failed_count": failed_count,
                "message": f"Vectorized {vectorized_count} articles, {failed_count} failed"
            }
            
        except Exception as e:
            return {"error": f"Vectorization failed: {str(e)}"}
    


# Initialize engine
engine = NEJMResearchEngine()


def lambda_handler(event, context):
    """Main Lambda handler - supports both MCP and direct tool calls"""
    
    # Handle OPTIONS for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'message': 'CORS preflight'})}
    
    try:
        # Parse request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        print(f"Request body: {json.dumps(body)}")
        
        # Handle MCP-style requests
        if body.get('method') == 'tools/call':
            # MCP format: {"method": "tools/call", "params": {"name": "tool_name", "arguments": {...}}}
            tool_name = body['params']['name']
            arguments = body['params'].get('arguments', {})
            
            print(f"MCP Tool requested: {tool_name}")
            print(f"MCP Arguments: {json.dumps(arguments)}")
            
            # Route to appropriate handler
            if tool_name == 'search_articles':
                result = engine.search_articles(
                    arguments.get('query', ''),
                    arguments.get('max_results', 10),
                    arguments.get('threshold', 0.5)
                )
            
            elif tool_name == 'ask_research_question':
                result = engine.ask_research_question(
                    arguments.get('question', ''),
                    arguments.get('max_sources', 10),
                    arguments.get('threshold', 0.4)
                )
            
            elif tool_name == 'get_database_stats':
                result = engine.get_database_stats()
            
            elif tool_name == 'get_article_by_doi':
                result = engine.get_article_by_doi(arguments.get('doi', ''))
            
            elif tool_name == 'compare_embeddings':
                result = engine.compare_embeddings(
                    arguments.get('text1', ''),
                    arguments.get('text2', '')
                )
            
            elif tool_name == 'ingest_articles':
                result = engine.ingest_articles(
                    arguments.get('source', 'nejm'),
                    arguments.get('count', 10)
                )
            
            elif tool_name == 'vectorize_existing_articles':
                result = engine.vectorize_existing_articles(
                    arguments.get('limit', 50)
                )
            
            else:
                result = {"error": f"Unknown MCP tool: {tool_name}"}
            
            # Return MCP-style response
            if "error" in result:
                return {
                    'statusCode': 400,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({
                        "error": result["error"],
                        "isError": True
                    })
                }
            
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": False
                })
            }
        
        else:
            # Legacy direct tool calls
            tool = body.get('tool', body.get('type', 'search'))
            
            print(f"Direct tool requested: {tool}")
            
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
            
            elif tool == 'ingest_articles' or tool == 'ingestion':
                result = engine.ingest_articles(
                    body.get('source', 'nejm'),
                    body.get('count', 10)
                )
            
            elif tool == 'vectorize_existing_articles' or tool == 'vectorize':
                result = engine.vectorize_existing_articles(
                    body.get('limit', 50)
                )
            
            else:
                result = {"error": f"Unknown tool: {tool}"}
            
            # Return direct response
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
