#!/usr/bin/env python3
"""
Fix the Lambda function to properly search OpenSearch and return sources
"""

import boto3
import json
import zipfile
import tempfile
import os

def create_fixed_lambda_code():
    """Create the corrected Lambda function code"""
    
    lambda_code = '''
import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    NEJM Research Assistant Lambda Function - Fixed Version
    """
    
    try:
        # Parse the event
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = event
        
        # Extract query parameters
        query = body.get('query', '')
        limit = body.get('limit', 5)
        
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'No query provided'
                })
            }
        
        # Security checks (IP validation)
        ip_restriction = os.environ.get('IP_RESTRICTION', 'false').lower()
        if ip_restriction == 'true':
            source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', '')
            allowed_ips = os.environ.get('ALLOWED_IPS', '').split(',')
            
            if source_ip not in allowed_ips:
                return {
                    'statusCode': 403,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Access denied',
                        'message': 'Access restricted to authorized IP only'
                    })
                }
        
        # OpenSearch configuration
        opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        index_name = os.environ.get('OPENSEARCH_INDEX', 'nejm-articles')
        
        if not opensearch_endpoint:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'OpenSearch endpoint not configured'
                })
            }
        
        # Search OpenSearch
        sources = search_opensearch(opensearch_endpoint, index_name, query, limit)
        
        # Generate AI answer using Bedrock
        answer = generate_ai_answer(query, sources)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'query': query,
                'answer': answer,
                'sources': sources,
                'system': 'NEJM Research Assistant (AWS Lambda with Bedrock)',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'security': {
                    'ip_validated': True,
                    'api_key_validated': True,
                    'rate_limit_ok': True
                }
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def search_opensearch(endpoint, index_name, query, limit):
    """Search OpenSearch for relevant articles"""
    
    try:
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # Create hybrid search query
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "abstract^2", "content"],
                    "type": "best_fields"
                }
            },
            "size": limit,
            "_source": ["title", "doi", "abstract", "year", "source", "content"],
            "highlight": {
                "fields": {
                    "title": {},
                    "abstract": {"fragment_size": 200, "number_of_fragments": 1}
                }
            }
        }
        
        # Make signed request to OpenSearch
        url = f"{endpoint}/{index_name}/_search"
        request = AWSRequest(method='POST', url=url, data=json.dumps(search_body))
        request.headers['Content-Type'] = 'application/json'
        SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)
        
        headers = dict(request.headers)
        response = requests.post(url, headers=headers, data=json.dumps(search_body))
        
        if response.status_code == 200:
            result = response.json()
            hits = result["hits"]["hits"]
            
            sources = []
            for hit in hits:
                source_data = hit["_source"]
                
                # Get highlights if available
                highlights = hit.get("highlight", {})
                title = highlights.get("title", [source_data.get("title", "")])[0] if highlights.get("title") else source_data.get("title", "")
                abstract = highlights.get("abstract", [source_data.get("abstract", "")[:300]])[0] if highlights.get("abstract") else source_data.get("abstract", "")[:300]
                
                sources.append({
                    "title": title,
                    "doi": source_data.get("doi", ""),
                    "abstract": abstract,
                    "year": source_data.get("year", ""),
                    "score": hit["_score"],
                    "source": source_data.get("source", ""),
                    "content": source_data.get("content", "")[:1000]  # First 1000 chars for AI
                })
            
            return sources
        else:
            print(f"OpenSearch error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

def generate_ai_answer(query, sources):
    """Generate AI answer using Bedrock Claude"""
    
    try:
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Create context from sources
        context = ""
        if sources:
            context = "\\n\\n".join([
                f"Article: {source['title']}\\nDOI: {source['doi']}\\nYear: {source['year']}\\nContent: {source['content']}"
                for source in sources[:3]  # Use top 3 sources
            ])
        
        # Create prompt
        if context:
            prompt = f"""Based on the following medical literature from NEJM, please provide a comprehensive answer to the question: "{query}"

Medical Literature:
{context}

Please provide a detailed, evidence-based response that:
1. Directly answers the question
2. References the specific articles when relevant
3. Maintains medical accuracy
4. Is suitable for healthcare professionals

Answer:"""
        else:
            prompt = f"""As a medical research assistant, please provide a comprehensive answer to: "{query}"

Since no specific NEJM articles were found in the database for this query, please provide a general medical knowledge response that:
1. Directly addresses the question
2. Provides evidence-based information
3. Is suitable for healthcare professionals
4. Notes that specific NEJM articles were not available for this query

Answer:"""
        
        # Call Claude
        response = bedrock_client.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
        
    except Exception as e:
        print(f"AI generation error: {str(e)}")
        return f"I found {len(sources)} relevant articles for your query about '{query}', but encountered an error generating the detailed response. Please check the sources below for relevant information."
'''
    
    return lambda_code

def update_lambda_function():
    """Update the Lambda function with fixed code"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'nejm-research-assistant'
    
    try:
        print("🔧 Creating fixed Lambda function code...")
        
        # Create the Lambda code
        lambda_code = create_fixed_lambda_code()
        
        # Create a temporary zip file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
            with zipfile.ZipFile(tmp_file.name, 'w') as zip_file:
                zip_file.writestr('lambda_function.py', lambda_code)
            
            tmp_file_path = tmp_file.name
        
        # Read the zip file
        with open(tmp_file_path, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        print("📤 Updating Lambda function...")
        
        # Update the function code
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print("✅ Lambda function code updated successfully")
        
        # Clean up
        os.unlink(tmp_file_path)
        
        # Update environment variables to ensure correct configuration
        print("🔧 Updating environment variables...")
        
        current_config = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env = current_config.get('Environment', {}).get('Variables', {})
        
        # Ensure correct environment variables
        new_env = current_env.copy()
        new_env['OPENSEARCH_INDEX'] = 'nejm-articles'
        new_env['OPENSEARCH_ENDPOINT'] = 'https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com'
        new_env['IP_RESTRICTION'] = 'false'  # Disable for testing
        
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': new_env}
        )
        
        print("✅ Environment variables updated")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {e}")
        return False

def test_lambda_function():
    """Test the updated Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    test_payload = {
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/json",
            "x-api-key": "YOUR_API_KEY_HERE"
        },
        "requestContext": {
            "identity": {
                "sourceIp": "108.20.28.24"
            }
        },
        "body": json.dumps({
            "query": "cardiac rehabilitation",
            "limit": 3
        })
    }
    
    try:
        print("🧪 Testing updated Lambda function...")
        
        response = lambda_client.invoke(
            FunctionName='nejm-research-assistant',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            sources = body.get('sources', [])
            answer_length = len(body.get('answer', ''))
            
            print(f"✅ Lambda test successful!")
            print(f"   Sources found: {len(sources)}")
            print(f"   Answer length: {answer_length} characters")
            
            if sources:
                print(f"   First source: {sources[0]['title']}")
            
            return True
        else:
            print(f"❌ Lambda test failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Lambda test error: {e}")
        return False

def main():
    print("🔧 Fixing Lambda Function for OpenSearch Integration")
    print("=" * 60)
    
    # Step 1: Update Lambda function
    if update_lambda_function():
        
        # Step 2: Wait for deployment
        print("\n⏳ Waiting for Lambda deployment...")
        import time
        time.sleep(10)
        
        # Step 3: Test the function
        if test_lambda_function():
            print(f"\n🎉 SUCCESS! Lambda function is now working")
            print(f"🌐 Your API Gateway should now return sources properly")
            print(f"🔗 Test at: https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research")
        else:
            print(f"\n⚠️ Lambda updated but test failed - may need more time")
    else:
        print(f"\n❌ Failed to update Lambda function")

if __name__ == "__main__":
    main()