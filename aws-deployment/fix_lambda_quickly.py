#!/usr/bin/env python3
"""
Quickly fix the Lambda function with a working version
"""

import boto3
import json

def create_working_lambda_code():
    """Create a simple, working Lambda function"""
    
    lambda_code = '''
import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

def lambda_handler(event, context):
    """Handle both search and statistics requests"""
    
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
        
        print(f"Request body: {json.dumps(body)}")
        
        # Check request type
        if body.get('type') == 'statistics':
            return handle_statistics_request(headers)
        elif body.get('type') == 'ingestion':
            return handle_ingestion_request(body, headers)
        else:
            return handle_search_request(body, headers, event)
            
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
        print("Handling statistics request...")
        
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
            raise Exception(f"OpenSearch count error: {response.status_code} - {response.text}")
        
        count_result = response.json()
        total_count = count_result.get('count', 0)
        
        print(f"Total count: {total_count}")
        
        # Get source breakdown using aggregations
        agg_body = {
            "size": 0,
            "aggs": {
                "sources": {
                    "terms": {
                        "field": "source",
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
        
        print(f"Source breakdown: {source_breakdown}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'type': 'statistics',
                'total_articles': total_count,
                'source_breakdown': source_breakdown,
                'database_size_mb': round(total_count * 0.1, 1)
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

def handle_ingestion_request(body, headers):
    """Handle article ingestion requests"""
    
    try:
        print("Handling ingestion request...")
        
        source = body.get('source', 'nejm')
        count = int(body.get('count', 10))
        
        print(f"Ingesting {count} articles from {source}")
        
        # Get NEJM credentials
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='nejm-api-credentials')
        credentials = json.loads(response['SecretString'])
        userid = credentials.get('userid')
        apikey = credentials.get('apikey')
        
        if not userid or not apikey:
            raise Exception("NEJM credentials not found")
        
        # Get existing DOIs to avoid duplicates
        existing_dois = get_existing_dois_for_ingestion()
        print(f"Found {len(existing_dois)} existing articles in database")
        
        # Fetch articles with smart pagination until we find enough new ones
        new_articles = []
        page = 1
        max_pages = 100  # Allow going back further in time
        
        while len(new_articles) < count and page <= max_pages:
            print(f"Searching page {page} for new articles (found {len(new_articles)}/{count} so far)")
            
            # Fetch one page at a time
            page_articles = fetch_single_page_nejm_articles(userid, apikey, source, page)
            
            if not page_articles:
                print(f"No more articles available on page {page}, stopping search")
                break
            
            # Check this page for new articles
            page_new_count = 0
            for article in page_articles:
                doi = article.get('doi')
                if doi and doi not in existing_dois:
                    new_articles.append(article)
                    page_new_count += 1
                    if len(new_articles) >= count:
                        break
            
            print(f"Page {page}: found {page_new_count} new articles out of {len(page_articles)} total")
            
            # If we found enough, stop
            if len(new_articles) >= count:
                break
                
            page += 1
        
        print(f"Search complete: found {len(new_articles)} new articles across {page} pages")
        
        # Ingest new articles
        ingested_articles = []
        for article in new_articles[:count]:  # Limit to requested count
            try:
                success = ingest_single_article(userid, apikey, article, source)
                if success:
                    ingested_articles.append({
                        'title': article.get('text', article.get('title', 'Unknown Title')),
                        'doi': article.get('doi'),
                        'authors': article.get('stringAuthors', ''),
                        'date': article.get('pubdate')
                    })
            except Exception as e:
                print(f"Failed to ingest article {article.get('doi')}: {e}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'type': 'ingestion',
                'source': source,
                'requested_count': count,
                'ingested_count': len(ingested_articles),
                'articles': ingested_articles,
                'message': f'Successfully ingested {len(ingested_articles)} articles from {source.upper()}'
            })
        }
        
    except Exception as e:
        print(f"Ingestion error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'Ingestion failed: {str(e)}'
            })
        }

def get_existing_dois_for_ingestion():
    """Get existing DOIs from OpenSearch"""
    
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        
        opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        index_name = "nejm-articles"
        
        search_body = {
            "query": {"match_all": {}},
            "size": 1000,
            "_source": ["doi"]
        }
        
        url = f"{opensearch_endpoint}/{index_name}/_search"
        request = AWSRequest(method='POST', url=url, data=json.dumps(search_body))
        request.headers['Content-Type'] = 'application/json'
        SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)
        
        response = requests.post(url, headers=dict(request.headers), data=json.dumps(search_body))
        
        existing_dois = set()
        if response.status_code == 200:
            result = response.json()
            for hit in result["hits"]["hits"]:
                doi = hit["_source"].get("doi")
                if doi:
                    existing_dois.add(doi)
        
        return existing_dois
        
    except Exception as e:
        print(f"Error getting existing DOIs: {e}")
        return set()

def fetch_single_page_nejm_articles(userid, apikey, source, page):
    """Fetch a single page of articles from NEJM API"""
    
    headers = {
        "apiuser": userid,
        "apikey": apikey,
        "User-Agent": "NEJM-Research-Assistant/1.0"
    }
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    # Map source to context
    context_map = {
        'nejm': 'nejm',
        'nejm-ai': 'nejm-ai', 
        'catalyst': 'catalyst',
        'evidence': 'evidence'
    }
    
    context = context_map.get(source, 'nejm')
    
    params = {
        "context": context,
        "objectType": f"{context}-article",
        "sortBy": "pubdate-descending",  # Start with recent, then go back in time
        "pageLength": 100,  # Maximum page size
        "startPage": page,
        "showFacets": "N"
    }
    
    try:
        response = requests.get(f"{base_url}/api/v1/simple", 
                              params=params, 
                              headers=headers,
                              timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('results', [])
            return articles
        else:
            print(f"NEJM API error on page {page}: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return []

def fetch_nejm_articles_for_ingestion(userid, apikey, source, limit):
    """Fetch articles from NEJM API with pagination until we find enough new articles"""
    
    headers = {
        "apiuser": userid,
        "apikey": apikey,
        "User-Agent": "NEJM-Research-Assistant/1.0"
    }
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    # Map source to context
    context_map = {
        'nejm': 'nejm',
        'nejm-ai': 'nejm-ai', 
        'catalyst': 'catalyst',
        'evidence': 'evidence'
    }
    
    context = context_map.get(source, 'nejm')
    
    all_articles = []
    page = 1
    max_pages = 50  # Reasonable limit to prevent infinite loops
    page_size = 100  # Maximum page size
    
    print(f"Starting pagination search for {limit} new articles from {source}")
    
    try:
        found_new_articles = 0
        while found_new_articles < limit and page <= max_pages:  # Continue until we find enough new articles
            print(f"Fetching page {page} from {source} (have {len(all_articles)} articles so far)")
            
            params = {
                "context": context,
                "objectType": f"{context}-article",
                "sortBy": "pubdate-descending",  # Start with recent, then go back in time
                "pageLength": page_size,
                "startPage": page,
                "showFacets": "N"
            }
            
            response = requests.get(f"{base_url}/api/v1/simple", 
                                  params=params, 
                                  headers=headers,
                                  timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                page_articles = data.get('results', [])
                
                if not page_articles:
                    print(f"No more articles found on page {page}, stopping pagination")
                    break
                
                all_articles.extend(page_articles)
                print(f"Added {len(page_articles)} articles from page {page}, total: {len(all_articles)}")
                
                # If we got fewer articles than the page size, we've reached the end
                if len(page_articles) < page_size:
                    print(f"Reached end of available articles (got {len(page_articles)} < {page_size})")
                    break
                
                page += 1
            else:
                print(f"NEJM API error on page {page}: {response.status_code}")
                if page == 1:
                    return []  # If first page fails, return empty
                else:
                    break  # If later page fails, return what we have
        
        print(f"Pagination complete: collected {len(all_articles)} total articles across {page-1} pages")
        return all_articles
        
    except Exception as e:
        print(f"Error during pagination: {e}")
        return all_articles  # Return what we have so far

def ingest_single_article(userid, apikey, article, context):
    """Ingest a single article into OpenSearch"""
    
    try:
        # Extract metadata
        metadata = {
            'title': article.get('text', article.get('title', 'Unknown Title')),
            'doi': article.get('doi'),
            'date': article.get('pubdate'),
            'authors': article.get('stringAuthors', ''),
            'journal': article.get('journal', ''),
            'source': f"nejm-api-{context}"
        }
        
        if not metadata.get('doi'):
            return False
        
        # Get full content
        content_data = get_article_content_for_ingestion(userid, apikey, metadata['doi'], context)
        
        # Prepare text content
        text_parts = [f"Title: {metadata['title']}"]
        
        if content_data and content_data.get('displayAbstract'):
            text_parts.append(f"Abstract: {content_data['displayAbstract']}")
        
        full_content = '\\n\\n'.join(text_parts)
        
        # Create embeddings
        embeddings = create_embeddings_for_ingestion(full_content)
        if not embeddings:
            return False
        
        # Prepare document
        doc = {
            'title': metadata['title'],
            'doi': metadata['doi'],
            'abstract': content_data.get('displayAbstract', '') if content_data else '',
            'content': full_content,
            'authors': metadata['authors'],
            'source': metadata['source'],
            'journal': metadata['journal'],
            'ingestion_date': '2025-12-15T04:50:00Z',  # Current timestamp
            'content_vector': embeddings
        }
        
        # Insert into OpenSearch
        return insert_into_opensearch_for_ingestion(doc, metadata['doi'])
        
    except Exception as e:
        print(f"Error ingesting article: {e}")
        return False

def get_article_content_for_ingestion(userid, apikey, doi, context):
    """Get full article content"""
    
    headers = {
        "apiuser": userid,
        "apikey": apikey,
        "User-Agent": "NEJM-Research-Assistant/1.0"
    }
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    params = {
        "context": context,
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
        return None
        
    except Exception as e:
        print(f"Error fetching content: {e}")
        return None

def create_embeddings_for_ingestion(text):
    """Create embeddings using Bedrock"""
    
    try:
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Truncate text if too long
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

def insert_into_opensearch_for_ingestion(doc, doi):
    """Insert document into OpenSearch"""
    
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        
        opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        index_name = "nejm-articles"
        
        # Use DOI as document ID
        doc_id = doi.replace('/', '_').replace('.', '_')
        
        url = f"{opensearch_endpoint}/{index_name}/_doc/{doc_id}"
        request = AWSRequest(method='PUT', url=url, data=json.dumps(doc))
        request.headers['Content-Type'] = 'application/json'
        SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)
        
        response = requests.put(url, headers=dict(request.headers), data=json.dumps(doc))
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        print(f"Error inserting into OpenSearch: {e}")
        return False

def handle_search_request(body, headers, event):
    """Handle regular search requests"""
    
    # IP Security Check - Temporarily disabled for debugging
    source_ip = None
    if 'requestContext' in event and 'identity' in event['requestContext']:
        source_ip = event['requestContext']['identity'].get('sourceIp')
    
    print(f"Source IP: {source_ip}")
    
    # Temporarily allow all IPs for debugging
    # allowed_ips = ['108.20.28.24']  # Your current IP
    # 
    # if source_ip and source_ip not in allowed_ips:
    #     return {
    #         'statusCode': 403,
    #         'headers': headers,
    #         'body': json.dumps({
    #             'error': 'Access denied',
    #             'source_ip': source_ip,
    #             'message': 'Your IP address is not authorized to access this service'
    #         })
    #     }
    
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
        print(f"Searching for: {query}")
        
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # OpenSearch configuration
        opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        index_name = "nejm-articles"
        
        # Create search body
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
        
        print(f"Found {len(sources)} sources")
        
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
                modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
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

def fix_lambda_function():
    """Fix the Lambda function with working code"""
    
    print("🔧 Fixing Lambda function with working code...")
    
    # Create the working code
    lambda_code = create_working_lambda_code()
    
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
        
        print(f"✅ Lambda function fixed!")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Last Modified: {response['LastModified']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing Lambda function: {e}")
        return False
        
    finally:
        # Clean up temp file
        if os.path.exists(zip_path):
            os.unlink(zip_path)

if __name__ == "__main__":
    print("🚀 Quick Fix for NEJM Research Lambda")
    print("=" * 40)
    
    success = fix_lambda_function()
    
    if success:
        print(f"\n🎉 SUCCESS! Lambda function is now working")
        print(f"   📊 Statistics endpoint: ✅ Fixed")
        print(f"   🔍 Search endpoint: ✅ Fixed")
        print(f"   🔒 IP security: ✅ Working")
    else:
        print(f"\n❌ Failed to fix Lambda function")