#!/usr/bin/env python3
"""
Vectorize All Articles - Add embeddings to articles that don't have them
This ensures full vector coverage for semantic search
"""

import boto3
import json
import time
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from typing import Dict, List

# Configuration
OPENSEARCH_ENDPOINT = 'https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com'
INDEX_NAME = 'nejm-articles'
BEDROCK_REGION = 'us-east-1'
BATCH_SIZE = 10  # Process articles in batches to avoid timeouts

# Initialize clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)
session = boto3.Session()
credentials = session.get_credentials()

def opensearch_request(method: str, path: str, data: Dict = None) -> Dict:
    """Make authenticated request to OpenSearch"""
    url = f"{OPENSEARCH_ENDPOINT}{path}"
    request = AWSRequest(method=method, url=url, data=json.dumps(data) if data else None)
    if data:
        request.headers['Content-Type'] = 'application/json'
    SigV4Auth(credentials, 'es', BEDROCK_REGION).add_auth(request)
    
    if method == 'GET':
        response = requests.get(url, headers=dict(request.headers))
    else:
        response = requests.post(url, headers=dict(request.headers), data=json.dumps(data) if data else None)
    
    response.raise_for_status()
    return response.json()

def get_embedding(text: str) -> List[float]:
    """Get embedding from Bedrock Titan"""
    try:
        response = bedrock_runtime.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": text})
        )
        result = json.loads(response['body'].read())
        return result['embedding']
    except Exception as e:
        print(f"❌ Failed to get embedding: {str(e)}")
        return None

def get_articles_without_vectors():
    """Find all articles that need re-vectorization with full content"""
    print("🔍 Finding all articles for full-content re-vectorization...")
    
    # Query for ALL articles to re-vectorize with enhanced content
    query = {
        "size": 10000,  # Get all articles
        "_source": ["id", "title", "abstract", "content", "doi"],
        "query": {"match_all": {}}  # Get ALL articles for re-vectorization
    }
    
    result = opensearch_request('POST', f'/{INDEX_NAME}/_search', query)
    hits = result.get('hits', {}).get('hits', [])
    
    articles = []
    for hit in hits:
        source = hit['_source']
        articles.append({
            'id': hit['_id'],
            'title': source.get('title', ''),
            'abstract': source.get('abstract', ''),
            'content': source.get('content', ''),
            'doi': source.get('doi', '')
        })
    
    print(f"📊 Found {len(articles)} articles for full-content re-vectorization")
    return articles

def create_embedding_text(article: Dict) -> str:
    """Create text for embedding from article content"""
    # Combine title, abstract, and content for comprehensive embedding
    parts = []
    
    if article.get('title'):
        parts.append(f"Title: {article['title']}")
    
    if article.get('abstract'):
        parts.append(f"Abstract: {article['abstract']}")
    
    if article.get('content'):
        # Use full content up to Titan's 8000 character limit
        content = article['content'][:8000]  # Amazon Titan limit
        parts.append(f"Content: {content}")
    
    return " ".join(parts)

def update_article_with_vector(article_id: str, vector: List[float]):
    """Update an article with its enhanced vector embedding"""
    update_body = {
        "doc": {
            "vector": vector,
            "vector_timestamp": time.time(),
            "vector_model": "amazon.titan-embed-text-v1",
            "vector_content_limit": "8000_chars_full_content"
        }
    }
    
    try:
        opensearch_request('POST', f'/{INDEX_NAME}/_update/{article_id}', update_body)
        return True
    except Exception as e:
        print(f"❌ Failed to update article {article_id}: {str(e)}")
        return False

def vectorize_articles_batch(articles: List[Dict]) -> Dict:
    """Vectorize a batch of articles"""
    results = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    for i, article in enumerate(articles):
        print(f"  📄 Processing {i+1}/{len(articles)}: {article['title'][:50]}...")
        
        # Create embedding text
        embedding_text = create_embedding_text(article)
        
        if not embedding_text.strip():
            print(f"    ⚠️ No content to embed, skipping")
            results['failed'] += 1
            continue
        
        # Get embedding
        vector = get_embedding(embedding_text)
        
        if vector is None:
            print(f"    ❌ Failed to get embedding")
            results['failed'] += 1
            results['errors'].append(f"Embedding failed for {article['id']}")
            continue
        
        # Update article
        if update_article_with_vector(article['id'], vector):
            print(f"    ✅ Vector added ({len(vector)} dimensions)")
            results['success'] += 1
        else:
            print(f"    ❌ Failed to update article")
            results['failed'] += 1
            results['errors'].append(f"Update failed for {article['id']}")
        
        # Small delay to avoid rate limits
        time.sleep(0.1)
    
    return results

def main():
    """Main vectorization process"""
    print("🚀 Starting vectorization of all articles...")
    print("=" * 60)
    
    # Get current stats
    total_query = {"query": {"match_all": {}}}
    total_result = opensearch_request('POST', f'/{INDEX_NAME}/_count', total_query)
    total_articles = total_result.get('count', 0)
    
    vector_query = {"query": {"exists": {"field": "vector"}}}
    vector_result = opensearch_request('POST', f'/{INDEX_NAME}/_count', vector_query)
    vectorized_articles = vector_result.get('count', 0)
    
    print(f"📊 Current Status:")
    print(f"   Total Articles: {total_articles}")
    print(f"   Vectorized: {vectorized_articles}")
    print(f"   Missing Vectors: {total_articles - vectorized_articles}")
    print()
    
    print(f"🔄 Re-vectorizing all articles with enhanced full-content processing...")
    print(f"📈 Upgrading from 2,000 char limit to 8,000 char limit (4x more content)")
    print()
    
    # Get all articles for re-vectorization
    articles_to_vectorize = get_articles_without_vectors()
    
    if not articles_to_vectorize:
        print("❌ No articles found in database!")
        return
    
    print(f"🔄 Processing {len(articles_to_vectorize)} articles in batches of {BATCH_SIZE}...")
    print()
    
    # Process in batches
    total_results = {'success': 0, 'failed': 0, 'errors': []}
    
    for i in range(0, len(articles_to_vectorize), BATCH_SIZE):
        batch = articles_to_vectorize[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(articles_to_vectorize) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"📦 Batch {batch_num}/{total_batches} ({len(batch)} articles)")
        
        batch_results = vectorize_articles_batch(batch)
        
        # Accumulate results
        total_results['success'] += batch_results['success']
        total_results['failed'] += batch_results['failed']
        total_results['errors'].extend(batch_results['errors'])
        
        print(f"   ✅ Success: {batch_results['success']}, ❌ Failed: {batch_results['failed']}")
        print()
        
        # Longer delay between batches
        if i + BATCH_SIZE < len(articles_to_vectorize):
            print("   ⏳ Waiting 2 seconds before next batch...")
            time.sleep(2)
    
    # Final verification
    print("🔍 Verifying results...")
    final_vector_result = opensearch_request('POST', f'/{INDEX_NAME}/_count', vector_query)
    final_vectorized = final_vector_result.get('count', 0)
    
    print("=" * 60)
    print("📋 VECTORIZATION COMPLETE")
    print("=" * 60)
    print(f"✅ Successfully vectorized: {total_results['success']} articles")
    print(f"❌ Failed: {total_results['failed']} articles")
    print(f"📊 Total vectorized articles: {final_vectorized}/{total_articles}")
    print(f"📈 Coverage: {(final_vectorized/total_articles)*100:.1f}%")
    
    if total_results['errors']:
        print(f"\n⚠️ Errors encountered:")
        for error in total_results['errors'][:5]:  # Show first 5 errors
            print(f"   • {error}")
        if len(total_results['errors']) > 5:
            print(f"   • ... and {len(total_results['errors']) - 5} more")
    
    if final_vectorized == total_articles:
        print("\n🎉 ALL ARTICLES NOW HAVE VECTOR EMBEDDINGS!")
        print("🔍 Semantic search is fully operational across entire database")
    else:
        print(f"\n⚠️ {total_articles - final_vectorized} articles still need vectorization")
        print("💡 You can run this script again to retry failed articles")

if __name__ == "__main__":
    main()