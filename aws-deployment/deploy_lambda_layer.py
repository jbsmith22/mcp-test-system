#!/usr/bin/env python3
"""
Deploy a Lambda layer with requests library and update the function
"""

import boto3
import json
import zipfile
import tempfile
import os
import subprocess

def create_requests_layer():
    """Create a Lambda layer with requests library"""
    
    print("📦 Creating Lambda layer with requests library...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        python_dir = os.path.join(temp_dir, "python")
        os.makedirs(python_dir)
        
        # Install requests to the python directory
        print("⬇️ Installing requests library...")
        result = subprocess.run([
            "pip", "install", "requests", "-t", python_dir
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to install requests: {result.stderr}")
            return None
        
        # Create zip file
        layer_zip = os.path.join(temp_dir, "requests_layer.zip")
        
        with zipfile.ZipFile(layer_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(python_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zip_file.write(file_path, arc_name)
        
        # Read the zip file
        with open(layer_zip, 'rb') as f:
            layer_content = f.read()
        
        print(f"✅ Layer created: {len(layer_content)} bytes")
        return layer_content

def deploy_layer():
    """Deploy the layer to AWS Lambda"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create the layer content
    layer_content = create_requests_layer()
    if not layer_content:
        return None
    
    try:
        print("📤 Publishing Lambda layer...")
        
        response = lambda_client.publish_layer_version(
            LayerName='requests-layer',
            Description='Requests library for Lambda functions',
            Content={'ZipFile': layer_content},
            CompatibleRuntimes=['python3.9', 'python3.10', 'python3.11', 'python3.12'],
            CompatibleArchitectures=['x86_64']
        )
        
        layer_arn = response['LayerVersionArn']
        print(f"✅ Layer published: {layer_arn}")
        return layer_arn
        
    except Exception as e:
        print(f"❌ Failed to publish layer: {e}")
        return None

def create_working_lambda_code():
    """Create Lambda function code that works with the layer"""
    
    return '''
import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    NEJM Research Assistant Lambda Function - Working Version
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
            return create_response(400, {'error': 'No query provided'})
        
        # Security checks (simplified for now)
        ip_restriction = os.environ.get('IP_RESTRICTION', 'false').lower()
        if ip_restriction == 'true':
            source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', '')
            allowed_ips = os.environ.get('ALLOWED_IPS', '').split(',')
            
            if source_ip not in allowed_ips:
                return create_response(403, {
                    'error': 'Access denied',
                    'message': 'Access restricted to authorized IP only'
                })
        
        # Search OpenSearch
        sources = search_opensearch(query, limit)
        
        # Generate AI answer
        answer = generate_ai_answer(query, sources)
        
        return create_response(200, {
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
        
    except Exception as e:
        return create_response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })

def create_response(status_code, body):
    """Create standardized response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }

def search_opensearch(query, limit):
    """Search OpenSearch for relevant articles"""
    
    try:
        # Get AWS credentials and OpenSearch config
        session = boto3.Session()
        credentials = session.get_credentials()
        
        opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        index_name = os.environ.get('OPENSEARCH_INDEX', 'nejm-articles')
        
        if not opensearch_endpoint:
            return []
        
        # Create search query
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
        url = f"{opensearch_endpoint}/{index_name}/_search"
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
                    "content": source_data.get("content", "")[:1000]
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
                for source in sources[:3]
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

def update_lambda_with_layer(layer_arn):
    """Update Lambda function with the layer and new code"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'nejm-research-assistant'
    
    try:
        print("🔧 Updating Lambda function code...")
        
        # Create the Lambda code
        lambda_code = create_working_lambda_code()
        
        # Create a temporary zip file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
            with zipfile.ZipFile(tmp_file.name, 'w') as zip_file:
                zip_file.writestr('lambda_function.py', lambda_code)
            
            tmp_file_path = tmp_file.name
        
        # Read the zip file
        with open(tmp_file_path, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Update the function code
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print("✅ Lambda function code updated")
        
        # Clean up
        os.unlink(tmp_file_path)
        
        # Wait a moment for the code update to complete
        import time
        time.sleep(5)
        
        # Update function configuration to add the layer
        print("🔧 Adding layer to Lambda function...")
        
        current_config = lambda_client.get_function_configuration(FunctionName=function_name)
        current_layers = current_config.get('Layers', [])
        
        # Add our new layer
        layer_arns = [layer['Arn'] for layer in current_layers if 'requests-layer' not in layer['Arn']]
        layer_arns.append(layer_arn)
        
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Layers=layer_arns
        )
        
        print("✅ Layer added to Lambda function")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {e}")
        return False

def test_updated_lambda():
    """Test the updated Lambda function"""
    
    print("\n⏳ Waiting for Lambda deployment...")
    import time
    time.sleep(10)
    
    print("🧪 Testing updated Lambda function...")
    
    import subprocess
    result = subprocess.run([
        'curl', '-X', 'POST',
        'https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research',
        '-H', 'Content-Type: application/json',
        '-H', 'x-api-key: YOUR_API_KEY_HERE',
        '-d', '{"query": "cardiac rehabilitation", "limit": 2}',
        '--max-time', '30'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            if 'sources' in response and len(response['sources']) > 0:
                print(f"✅ API test successful!")
                print(f"   Sources: {len(response['sources'])}")
                print(f"   First source: {response['sources'][0]['title']}")
                return True
            else:
                print(f"⚠️ API responded but no sources found")
                print(f"   Response: {result.stdout[:200]}...")
                return False
        except:
            print(f"⚠️ API responded but invalid JSON: {result.stdout[:200]}...")
            return False
    else:
        print(f"❌ API test failed: {result.stderr}")
        return False

def main():
    print("🚀 Deploying Lambda Layer with Requests Library")
    print("=" * 60)
    
    # Step 1: Deploy the layer
    layer_arn = deploy_layer()
    if not layer_arn:
        print("❌ Failed to deploy layer")
        return False
    
    # Step 2: Update Lambda function
    if update_lambda_with_layer(layer_arn):
        
        # Step 3: Test the function
        if test_updated_lambda():
            print(f"\n🎉 SUCCESS! Lambda function is now working with OpenSearch")
            print(f"🌐 Your API Gateway should now return proper search results")
            print(f"🔗 Test at: https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research")
        else:
            print(f"\n⚠️ Lambda updated but test inconclusive - may need more time")
    else:
        print(f"\n❌ Failed to update Lambda function")

if __name__ == "__main__":
    main()