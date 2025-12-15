#!/usr/bin/env python3
"""
Ingest new NEJM articles while avoiding duplicates
"""

import boto3
import json
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

def get_nejm_credentials():
    """Get NEJM credentials from AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='nejm-api-credentials')
        credentials = json.loads(response['SecretString'])
        return credentials.get('userid'), credentials.get('apikey')
    except Exception as e:
        print(f"❌ Error getting NEJM credentials: {e}")
        return None, None

def get_existing_dois():
    """Get list of DOIs already in OpenSearch"""
    
    try:
        print("🔍 Checking existing DOIs in OpenSearch...")
        
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # OpenSearch configuration
        opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        index_name = "nejm-articles"
        
        # Search for all DOIs
        search_body = {
            "query": {"match_all": {}},
            "size": 1000,  # Get up to 1000 existing articles
            "_source": ["doi"],
            "sort": [{"_id": {"order": "asc"}}]
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
            
            existing_dois = set()
            for hit in hits:
                doi = hit["_source"].get("doi")
                if doi:
                    existing_dois.add(doi)
            
            print(f"   ✅ Found {len(existing_dois)} existing DOIs in database")
            return existing_dois
        else:
            print(f"   ❌ OpenSearch error: {response.status_code}")
            return set()
            
    except Exception as e:
        print(f"   ❌ Error checking existing DOIs: {e}")
        return set()

def fetch_recent_nejm_articles(userid, apikey, context="nejm-ai", limit=20):
    """Fetch recent articles from NEJM API"""
    
    headers = {
        "apiuser": userid,
        "apikey": apikey,
        "User-Agent": "NEJM-Research-Assistant/1.0"
    }
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    params = {
        "context": context,
        "objectType": f"{context}-article",
        "sortBy": "pubdate-descending",
        "pageLength": min(limit, 100),
        "startPage": 1,
        "showFacets": "N"
    }
    
    try:
        print(f"📡 Fetching recent articles from {context.upper()}...")
        
        response = requests.get(f"{base_url}/api/v1/simple", 
                              params=params, 
                              headers=headers,
                              timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('results', [])
            print(f"   ✅ Retrieved {len(articles)} articles from API")
            return articles
        else:
            print(f"   ❌ NEJM API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"   ❌ Error fetching articles: {e}")
        return []

def get_article_content(userid, apikey, doi, context):
    """Get full article content from NEJM API"""
    
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
        else:
            print(f"      ⚠️ Content API error for {doi}: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"      ⚠️ Error fetching content for {doi}: {e}")
        return None

def extract_text_from_jats_xml(xml_content):
    """Extract readable text from JATS XML"""
    
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        
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
        
        return '\n\n'.join(text_parts)
        
    except Exception as e:
        print(f"      ⚠️ Error parsing JATS XML: {e}")
        return ""

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
        print(f"      ❌ Error creating embeddings: {e}")
        return None

def insert_into_opensearch(doc, doi):
    """Insert document into OpenSearch"""
    
    try:
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # OpenSearch configuration
        opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        index_name = "nejm-articles"
        
        # Use DOI as document ID (replace special characters)
        doc_id = doi.replace('/', '_').replace('.', '_')
        
        # Make signed request to OpenSearch
        url = f"{opensearch_endpoint}/{index_name}/_doc/{doc_id}"
        request = AWSRequest(method='PUT', url=url, data=json.dumps(doc))
        request.headers['Content-Type'] = 'application/json'
        SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)
        
        headers = dict(request.headers)
        response = requests.put(url, headers=headers, data=json.dumps(doc))
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"      ❌ OpenSearch insert error: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"      ❌ Error inserting into OpenSearch: {e}")
        return False

def extract_article_metadata(article):
    """Extract standardized metadata from NEJM API response"""
    metadata = {
        'title': article.get('text', article.get('title', 'Unknown Title')),
        'doi': article.get('doi'),
        'date': article.get('pubdate'),
        'abstract': '',  # Will be filled from content
        'authors': article.get('stringAuthors', ''),
        'journal': article.get('journal', ''),
        'article_type': article.get('articleType', []),
        'source': f"nejm-api-{article.get('journal', 'unknown')}"
    }
    
    # Extract year from date
    if metadata['date']:
        try:
            year_match = re.search(r'(\d{4})', str(metadata['date']))
            if year_match:
                metadata['year'] = int(year_match.group(1))
        except:
            pass
    
    return metadata

def ingest_article(userid, apikey, article, context):
    """Ingest a single article into OpenSearch"""
    
    try:
        # Extract metadata
        metadata = extract_article_metadata(article)
        
        if not metadata.get('doi'):
            print(f"      ❌ No DOI found for article")
            return False
        
        print(f"   📄 Processing: {metadata['title'][:60]}...")
        print(f"      DOI: {metadata['doi']}")
        
        # Get full content
        content_data = get_article_content(userid, apikey, metadata['doi'], context)
        
        # Prepare text content
        text_parts = []
        
        # Add metadata text
        if metadata.get('title'):
            text_parts.append(f"Title: {metadata['title']}")
        
        # Add full content if available
        if content_data:
            # Update abstract from content
            if content_data.get('displayAbstract'):
                metadata['abstract'] = content_data['displayAbstract']
                text_parts.append(f"Abstract: {metadata['abstract']}")
            
            # Extract full text from JATS XML
            if content_data.get('document'):
                full_text = extract_text_from_jats_xml(content_data['document'])
                if full_text:
                    text_parts.append(full_text)
        
        # Fallback to search result text
        if not text_parts or len('\n\n'.join(text_parts)) < 100:
            if article.get('text'):
                text_parts.append(f"Content: {article['text']}")
        
        full_content = '\n\n'.join(text_parts)
        
        if not full_content.strip():
            print(f"      ❌ No content available")
            return False
        
        print(f"      📝 Content length: {len(full_content)} characters")
        
        # Create embeddings
        print(f"      🤖 Creating embeddings...")
        embeddings = create_embeddings(full_content)
        if not embeddings:
            print(f"      ❌ Failed to create embeddings")
            return False
        
        print(f"      ✅ Embeddings created: {len(embeddings)} dimensions")
        
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
        print(f"      💾 Inserting into OpenSearch...")
        if insert_into_opensearch(doc, metadata['doi']):
            print(f"      ✅ Successfully ingested!")
            return True
        else:
            print(f"      ❌ Failed to insert into OpenSearch")
            return False
        
    except Exception as e:
        print(f"      ❌ Error ingesting article: {e}")
        return False

def main():
    print("🚀 NEJM Article Ingestion - Avoiding Duplicates")
    print("=" * 60)
    
    # Step 1: Get credentials
    userid, apikey = get_nejm_credentials()
    if not userid or not apikey:
        print("❌ Cannot proceed without valid credentials")
        return
    
    print(f"✅ NEJM credentials retrieved: {userid}")
    
    # Step 2: Get existing DOIs
    existing_dois = get_existing_dois()
    
    # Step 3: Try different contexts to find new articles
    contexts_to_try = ["nejm", "catalyst", "evidence", "nejm-ai"]
    all_new_articles = []
    
    for context in contexts_to_try:
        print(f"\n📡 Trying context: {context.upper()}")
        articles = fetch_recent_nejm_articles(userid, apikey, context, limit=20)
        
        if articles:
            # Filter out duplicates for this context
            context_new_articles = []
            for article in articles:
                doi = article.get('doi')
                if doi and doi not in existing_dois:
                    context_new_articles.append((article, context))
                elif doi:
                    print(f"   ⏭️ Skipping duplicate: {doi}")
            
            print(f"   ✅ Found {len(context_new_articles)} new articles in {context}")
            all_new_articles.extend(context_new_articles)
            
            # Stop if we have enough
            if len(all_new_articles) >= 10:
                break
    
    print(f"\n🔍 Total new articles found across all contexts: {len(all_new_articles)}")
    
    if len(all_new_articles) == 0:
        print("ℹ️ No new articles to ingest - all recent articles are already in database")
        return
    
    # Step 4: Ingest up to 20 new articles
    target_count = min(20, len(all_new_articles))
    print(f"\n📥 Ingesting {target_count} new articles...")
    
    success_count = 0
    failed_count = 0
    
    for i, (article, context) in enumerate(all_new_articles[:target_count], 1):
        print(f"\n{i}/{target_count}. Ingesting article from {context.upper()}...")
        
        if ingest_article(userid, apikey, article, context):
            success_count += 1
        else:
            failed_count += 1
    
    # Step 6: Summary
    print(f"\n📊 Ingestion Summary")
    print("=" * 40)
    print(f"✅ Successfully ingested: {success_count}")
    print(f"❌ Failed to ingest: {failed_count}")
    print(f"📈 Database growth: +{success_count} articles")
    
    if success_count > 0:
        print(f"\n🎉 SUCCESS! Added {success_count} new NEJM articles to your database")
        print(f"🔍 You can now search these new articles in your web interface")
        print(f"🌐 Visit: http://nejm-research-web-interface.s3-website-us-east-1.amazonaws.com")
    else:
        print(f"\n⚠️ No articles were successfully ingested")

if __name__ == "__main__":
    main()