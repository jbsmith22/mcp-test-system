#!/usr/bin/env python3
"""
Update the Lambda function to handle statistics requests properly
"""

import boto3
import json

def create_updated_lambda_code():
    """Create updated Lambda function code that handles both search and stats"""
    
    lambda_code = '''
import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import os

def lambda_handler(event, context):
    """
    Handle both search and statistics requests
    """
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight'})
        }
    
    try:
        # Parse request body
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = event
        
        # Check for statistics request
        if body.get('type') == 'statistics' or body.get('query') == 'stats':
            return handle_statistics_request(headers)
        else:
            return handle_search_request(body, headers)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }

def handle_statistics_request(headers):
    """Handle statistics/count requests"""
    
    try:
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # OpenSearch configuration
        opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        index_name = "nejm-articles"
        
        # Get total count using _count API
        count_body = {"query": {"match_all": {}}}
        
        url = f"{opensearch_endpoint}/{index_name}/_count"
        request = AWSRequest(method='POST', url=url, data=json.dumps(count_body))
        request.headers['Content-Type'] = 'application/json'
        SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)
        
        response = requests.post(url, headers=dict(request.headers), data=json.dumps(count_body))
        
        if response.status_code != 200:
            raise Exception(f"OpenSearch count error: {response.status_code}")
        
        count_result = response.json()
        total_count = count_result.get('count', 0)
        
        # Get source breakdown using aggregations
        agg_body = {
            "size": 0,
            "aggs": {
                "sources": {
                    "terms": {
                        "field": "source.keyword",
                        "size": 20
                    }
                }
            }
        }
        
        url = f"{opensearch_endpoint}/{index_name}/_search"
        request = AWSRequest(method='POST', url=url, data=json.dumps(agg_body))
        request.headers['Content-Type'] = 'application/json'
        SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)
        
        response = requests.post(url, headers=dict(request.headers), data=json.dumps(agg_body))
        
        source_breakdown = {}
        if response.status_code == 200:
            agg_result = response.json()
            buckets = agg_result.get('aggregations', {}).get('sources', {}).get('buckets', [])
            for bucket in buckets:
                source_breakdown[bucket['key']] = bucket['doc_count']
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'type': 'statistics',
                'total_articles': total_count,
                'source_breakdown': source_breakdown,
                'database_size_mb': round(total_count * 0.1, 1),
                'timestamp': context.aws_request_id if 'context' in globals() else 'unknown'
            })
        }
        
    except Exception as e:
        print(f"Statistics error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'Failed to get statistics: {str(e)}'
            })
        }

def handle_search_request(body, headers):
    """Handle regular search requests (existing functionality)"""
    
    # IP Security Check
    source_ip = None
    if 'requestContext' in event and 'identity' in event['requestContext']:
        source_ip = event['requestContext']['identity'].get('sourceIp')
    
    # List of allowed IPs
    allowed_ips = ['108.20.28.24']  # Your current IP
    
    if source_ip and source_ip not in allowed_ips:
        return {
            'statusCode': 403,
            'headers': headers,
            'body': json.dumps({
                'error': 'Access denied',
                'source_ip': source_ip,
                'message': 'Your IP address is not authorized to access this service'
            })
        }
    
    # Extract query parameters
    query = body.get('query', '')
    max_results = min(int(body.get('max_results', 10)), 50)
    
    if not query:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Query parameter is required'})
        }
    
    try:
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # OpenSearch configuration
        opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        index_name = "nejm-articles"
        
        # Create search body with both text and vector search
        search_body = {
            "size": max_results,
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "abstract^2", "content", "authors"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "_source": ["title", "doi", "abstract", "authors", "year", "source", "journal"],
            "highlight": {
                "fields": {
                    "title": {},
                    "abstract": {},
                    "content": {}
                },
                "fragment_size": 150,
                "number_of_fragments": 2
            }
        }
        
        # Make signed request to OpenSearch
        url = f"{opensearch_endpoint}/{index_name}/_search"
        request = AWSRequest(method='POST', url=url, data=json.dumps(search_body))
        request.headers['Content-Type'] = 'application/json'
        SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)
        
        response = requests.post(url, headers=dict(request.headers), data=json.dumps(search_body))
        
        if response.status_code != 200:
            raise Exception(f"OpenSearch error: {response.status_code}")
        
        search_results = response.json()
        
        # Extract sources for AI processing
        sources = []
        for hit in search_results['hits']['hits']:
            source_doc = hit['_source']
            
            # Get highlighted text if available
            highlight_text = ""
            if 'highlight' in hit:
                for field, highlights in hit['highlight'].items():
                    highlight_text += " ".join(highlights) + " "
            
            sources.append({
                'title': source_doc.get('title', 'Unknown Title'),
                'doi': source_doc.get('doi', ''),
                'abstract': source_doc.get('abstract', ''),
                'authors': source_doc.get('authors', ''),
                'year': source_doc.get('year'),
                'source': source_doc.get('source', ''),
                'journal': source_doc.get('journal', ''),
                'relevance_score': hit['_score'],
                'highlight': highlight_text.strip()
            })
        
        # Generate AI response using Bedrock
        if sources:
            # Prepare context for AI
            context_text = "\\n\\n".join([
                f"Title: {s['title']}\\nAuthors: {s['authors']}\\nAbstract: {s['abstract'][:500]}..."
                for s in sources[:5]  # Use top 5 sources for context
            ])
            
            # Call Bedrock for AI response
            bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            
            prompt = f"""Based on the following medical research articles, provide a comprehensive answer to the question: "{query}"

Research Articles:
{context_text}

Please provide a detailed, evidence-based response that:
1. Directly answers the question
2. References specific findings from the articles
3. Maintains scientific accuracy
4. Highlights any limitations or areas needing further research

Answer:"""

            response = bedrock_client.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            ai_answer = result['content'][0]['text']
        else:
            ai_answer = f"I couldn't find any relevant articles for '{query}'. Try different keywords or check the spelling."
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'query': query,
                'answer': ai_answer,
                'sources': sources,
                'total_found': len(sources)
            })
        }
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'Search failed: {str(e)}'
            })
        }
'''
    
    return lambda_code

def update_lambda_function():
    """Update the Lambda function with statistics support"""
    
    print("🔄 Updating Lambda function to support statistics...")
    
    # Create the updated code
    lambda_code = create_updated_lambda_code()
    
    # Create deployment package
    import zipfile
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
        with zipfile.ZipFile(tmp_file.name, 'w') as zip_file:
            zip_file.writestr('lambda_function.py', lambda_code)
        
        zip_path = tmp_file.name
    
    try:
        # Update Lambda function
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        with open(zip_path, 'rb') as zip_data:
            response = lambda_client.update_function_code(
                FunctionName='nejm-research-assistant',
                ZipFile=zip_data.read()
            )
        
        print(f"✅ Lambda function updated successfully!")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Last Modified: {response['LastModified']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {e}")
        return False
        
    finally:
        # Clean up temp file
        if os.path.exists(zip_path):
            os.unlink(zip_path)

if __name__ == "__main__":
    print("🚀 Updating NEJM Research Lambda for Statistics Support")
    print("=" * 60)
    
    success = update_lambda_function()
    
    if success:
        print(f"\n🎉 SUCCESS! Lambda function now supports:")
        print(f"   📊 Statistics requests (type: 'statistics')")
        print(f"   🔍 Regular search requests")
        print(f"   📈 Direct OpenSearch count queries")
        print(f"   📋 Source breakdown aggregations")
    else:
        print(f"\n❌ Failed to update Lambda function")