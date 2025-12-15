#!/usr/bin/env python3
"""
Create AWS Lambda function for NEJM article ingestion
"""

import boto3
import json
import zipfile
import tempfile
import os

def create_ingestion_lambda_code():
    """Create the NEJM ingestion Lambda function code"""
    
    lambda_code = '''
import json
import boto3
import requests
from opensearchpy import OpenSearch, RequestsHttpConnection
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import os
from datetime import datetime
import re
import xml.etree.ElementTree as ET

def lambda_handler(event, context):
    """
    NEJM Article Ingestion Lambda Function
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
        
        # Extract parameters
        context_name = body.get('context', 'nejm-ai')
        limit = body.get('limit', 10)
        dry_run = body.get('dry_run', False)
        
        print(f"Starting ingestion: context={context_name}, limit={limit}, dry_run={dry_run}")
        
        # Get NEJM credentials
        userid, apikey = get_nejm_credentials()
        if not userid or not apikey:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'NEJM API credentials not found',
                    'message': 'Check AWS Secrets Manager configuration'
                })
            }
        
        # Fetch recent articles
        articles = fetch_recent_articles(userid, apikey, context_name, limit)
        
        if not articles:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'message': 'No articles found',
                    'context': context_name,
                    'articles_found': 0
                })
            }
        
        # Process articles
        results = []
        success_count = 0
        
        for article in articles:
            try:
                # Extract metadata
                metadata = extract_article_metadata(article)
                
                if dry_run:
                    results.append({
                        'doi': metadata.get('doi'),
                        'title': metadata.get('title'),
                        'status': 'ready_for_ingestion'
                    })
                    success_count += 1
                else:
                    # Get full content and ingest
                    success = ingest_article_to_opensearch(userid, apikey, article, context_name)
                    
                    results.append({
                        'doi': metadata.get('doi'),
                        'title': metadata.get('title'),
                        'status': 'success' if success else 'failed'
                    })
                    
                    if success:
                        success_count += 1
                        
            except Exception as e:
                print(f"Error processing article: {e}")
                results.append({
                    'doi': article.get('doi', 'unknown'),
                    'title': article.get('text', 'unknown')[:50],
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': f'Ingestion complete',
                'context': context_name,
                'articles_found': len(articles),
                'articles_processed': len(results),
                'successful_ingestions': success_count,
                'dry_run': dry_run,
                'results': results,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        }
        
    except Exception as e:
        print(f"Lambda error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def get_nejm_credentials():
    """Get NEJM credentials from AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='nejm-api-credentials')
        credentials = json.loads(response['SecretString'])
        return credentials.get('userid'), credentials.get('apikey')
    except Exception as e:
        print(f"Error getting NEJM credentials: {e}")
        return None, None

def fetch_recent_articles(userid, apikey, context_name, limit):
    """Fetch recent articles from NEJM API"""
    
    headers = {
        "apiuser": userid,
        "apikey": apikey,
        "User-Agent": "NEJM-Research-Assistant-Lambda/1.0"
    }
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    params = {
        "context": context_name,
        "objectType": f"{context_name}-article",
        "sortBy": "pubdate-descending",
        "pageLength": min(limit, 100),
        "startPage": 1,
        "showFacets": "N"
    }
    
    try:
        response = requests.get(f"{base_url}/api/v1/simple", 
                              params=params, 
                              headers=headers,
                              timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            print(f"NEJM API error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"Error fetching articles: {e}")
        return []

def get_article_content(userid, apikey, doi, context_name):
    """Get full article content from NEJM API"""
    
    headers = {
        "apiuser": userid,
        "apikey": apikey,
        "User-Agent": "NEJM-Research-Assistant-Lambda/1.0"
    }
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    params = {
        "context": context_name,
        "doi": doi,
        "format": "json"
    }
    
    try:
        response = requests.get(f"{base_url}/api/v1/content", 
                              params=params, 
                              headers=headers,
                              timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Content API error for {doi}: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error fetching content for {doi}: {e}")
        return None

def extract_article_metadata(article):
    """Extract standardized metadata from NEJM API response"""
    metadata = {
        'title': article.get('text', article.get('title', 'Unknown Title')),
        'doi': article.get('doi'),
        'date': article.get('pubdate'),
        'abstract': article.get('displayAbstract', ''),
        'authors': article.get('stringAuthors', ''),
        'journal': article.get('journal', ''),
        'article_type': article.get('articleType', []),
        'source': f"nejm-api-{article.get('journal', 'unknown')}"
    }
    
    # Extract year from date
    if metadata['date']:
        try:
            year_match = re.search(r'(\\d{4})', str(metadata['date']))
            if year_match:
                metadata['year'] = int(year_match.group(1))
        except:
            pass
    
    return metadata

def extract_text_from_jats_xml(xml_content):
    """Extract readable text from JATS XML"""
    
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Define namespace map for NEJM JATS
        namespaces = {
            'xlink': 'http://www.w3.org/1999/xlink',
            'oasis': 'http://www.niso.org/standards/z39-96/ns/oasis-exchange/table'
        }
        
        text_parts = []
        
        # Extract title
        title_elem = root.find('.//article-title')
        if title_elem is not None:
            title_text = ''.join(title_elem.itertext()).strip()
            if title_text:
                text_parts.append(f"Title: {title_text}")
        
        # Extract abstract
        abstract_elem = root.find('.//abstract')
        if abstract_elem is not None:
            abstract_text = ''.join(abstract_elem.itertext()).strip()
            if abstract_text:
                text_parts.append(f"Abstract: {abstract_text}")
        
        # Extract body content
        body_elem = root.find('.//body')
        if body_elem is not None:
            # Get all text content from body, excluding references
            body_text = []
            for elem in body_elem.iter():
                if elem.tag not in ['ref', 'xref', 'sup'] and elem.text:
                    body_text.append(elem.text.strip())
                if elem.tail:
                    body_text.append(elem.tail.strip())
            
            body_content = ' '.join([t for t in body_text if t])
            if body_content:
                text_parts.append(f"Content: {body_content}")
        
        return '\\n\\n'.join(text_parts)
        
    except Exception as e:
        print(f"Error parsing JATS XML: {e}")
        return ""

def ingest_article_to_opensearch(userid, apikey, article, context_name):
    """Ingest article into OpenSearch"""
    
    try:
        # Extract metadata
        metadata = extract_article_metadata(article)
        
        if not metadata.get('doi'):
            print(f"No DOI found for article: {metadata.get('title')}")
            return False
        
        # Get full content
        content_data = get_article_content(userid, apikey, metadata['doi'], context_name)
        
        # Prepare text content
        text_parts = []
        
        # Add metadata text
        if metadata.get('title'):
            text_parts.append(f"Title: {metadata['title']}")
        
        if metadata.get('abstract'):
            text_parts.append(f"Abstract: {metadata['abstract']}")
        
        # Add full content if available
        if content_data and 'document' in content_data:
            jats_xml = content_data['document']
            if jats_xml:
                full_text = extract_text_from_jats_xml(jats_xml)
                if full_text:
                    text_parts.append(full_text)
        
        # Fallback to search result text
        if not text_parts or len('\\n\\n'.join(text_parts)) < 100:
            if article.get('text'):
                text_parts.append(f"Content: {article['text']}")
        
        full_content = '\\n\\n'.join(text_parts)
        
        if not full_content.strip():
            print(f"No content available for: {metadata.get('title')}")
            return False
        
        # Create embeddings using Bedrock
        embeddings = create_embeddings(full_content)
        if not embeddings:
            print(f"Failed to create embeddings for: {metadata.get('title')}")
            return False
        
        # Prepare document for OpenSearch
        doc = {
            'title': metadata.get('title', ''),
            'doi': metadata.get('doi', ''),
            'abstract': metadata.get('abstract', ''),
            'content': full_content,
            'year': metadata.get('year'),
            'authors': metadata.get('authors', ''),
            'source': metadata.get('source', ''),
            'article_type': metadata.get('article_type', []),
            'journal': metadata.get('journal', ''),
            'ingestion_date': datetime.utcnow().isoformat(),
            'content_vector': embeddings
        }
        
        # Insert into OpenSearch
        return insert_into_opensearch(doc, metadata['doi'])
        
    except Exception as e:
        print(f"Error ingesting article: {e}")
        return False

def create_embeddings(text):
    """Create embeddings using AWS Bedrock"""
    
    try:
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Truncate text if too long (Titan has limits)
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        response = bedrock_client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({
                "inputText": text
            })
        )
        
        result = json.loads(response['body'].read())
        return result.get('embedding', [])
        
    except Exception as e:
        print(f"Error creating embeddings: {e}")
        return None

def insert_into_opensearch(doc, doi):
    """Insert document into OpenSearch"""
    
    try:
        # Get OpenSearch client
        opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        index_name = os.environ.get('OPENSEARCH_INDEX', 'nejm-articles')
        
        if not opensearch_endpoint:
            print("OpenSearch endpoint not configured")
            return False
        
        # Create OpenSearch client with AWS auth
        session = boto3.Session()
        credentials = session.get_credentials()
        
        client = OpenSearch(
            hosts=[opensearch_endpoint.replace('https://', '')],
            http_auth=('', ''),  # Use IAM auth
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            http_compress=True
        )
        
        # Use DOI as document ID (replace special characters)
        doc_id = doi.replace('/', '_').replace('.', '_')
        
        # Insert document
        response = client.index(
            index=index_name,
            id=doc_id,
            body=doc
        )
        
        print(f"Inserted article: {doc['title']}")
        return response.get('result') == 'created' or response.get('result') == 'updated'
        
    except Exception as e:
        print(f"Error inserting into OpenSearch: {e}")
        return False
'''
    
    return lambda_code

def create_ingestion_lambda():
    """Create the NEJM ingestion Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'nejm-content-ingestion'
    
    try:
        print("🔧 Creating NEJM ingestion Lambda function...")
        
        # Create the Lambda code
        lambda_code = create_ingestion_lambda_code()
        
        # Create a temporary zip file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
            with zipfile.ZipFile(tmp_file.name, 'w') as zip_file:
                zip_file.writestr('lambda_function.py', lambda_code)
            
            tmp_file_path = tmp_file.name
        
        # Read the zip file
        with open(tmp_file_path, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Get account ID for IAM role
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            print("📤 Updating existing Lambda function...")
            
            # Update function code
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            
        except lambda_client.exceptions.ResourceNotFoundException:
            print("📤 Creating new Lambda function...")
            
            # Create new function
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.12',
                Role=f'arn:aws:iam::{account_id}:role/nejm-research-lambda-role',
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Timeout=900,  # 15 minutes
                MemorySize=1024,
                Environment={
                    'Variables': {
                        'OPENSEARCH_ENDPOINT': 'https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com',
                        'OPENSEARCH_INDEX': 'nejm-articles'
                    }
                }
            )
        
        print("✅ Lambda function created/updated successfully")
        
        # Clean up
        os.unlink(tmp_file_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating Lambda function: {e}")
        return False

def test_ingestion_lambda():
    """Test the ingestion Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    test_payload = {
        "context": "nejm-ai",
        "limit": 2,
        "dry_run": True
    }
    
    try:
        print("🧪 Testing ingestion Lambda function...")
        
        response = lambda_client.invoke(
            FunctionName='nejm-content-ingestion',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            
            print(f"✅ Lambda test successful!")
            print(f"   Articles found: {body.get('articles_found', 0)}")
            print(f"   Articles processed: {body.get('articles_processed', 0)}")
            print(f"   Dry run: {body.get('dry_run', False)}")
            
            if body.get('results'):
                print(f"   Sample results:")
                for i, article in enumerate(body['results'][:2], 1):
                    print(f"     {i}. {article.get('title', 'Unknown')[:60]}...")
                    print(f"        DOI: {article.get('doi', 'N/A')}")
                    print(f"        Status: {article.get('status', 'Unknown')}")
            
            return True
        else:
            print(f"❌ Lambda test failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Lambda test error: {e}")
        return False

def main():
    print("🔧 Creating NEJM Article Ingestion Lambda Function")
    print("=" * 60)
    
    # Step 1: Create Lambda function
    if create_ingestion_lambda():
        
        # Step 2: Wait for deployment
        print("\\n⏳ Waiting for Lambda deployment...")
        import time
        time.sleep(10)
        
        # Step 3: Test the function
        if test_ingestion_lambda():
            print(f"\\n🎉 SUCCESS! NEJM ingestion Lambda is ready")
            print(f"🔗 Function name: nejm-content-ingestion")
            print(f"📋 Usage examples:")
            print(f"   • Dry run: {{'context': 'nejm-ai', 'limit': 5, 'dry_run': true}}")
            print(f"   • Real ingestion: {{'context': 'nejm-ai', 'limit': 10}}")
            print(f"   • Different context: {{'context': 'nejm', 'limit': 5}}")
        else:
            print(f"\\n⚠️ Lambda created but test failed - may need more time")
    else:
        print(f"\\n❌ Failed to create Lambda function")

if __name__ == "__main__":
    main()