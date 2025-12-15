#!/usr/bin/env python3
"""
Ingest NEJM articles directly to AWS OpenSearch
"""

import boto3
import json
import requests
from typing import List, Dict
import time

class AWSNEJMIngester:
    def __init__(self):
        # AWS configuration
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        
        # NEJM API configuration
        self.nejm_base_url = "https://onesearch-api.nejmgroup-qa.org"
        
        # Get NEJM credentials from AWS Secrets Manager
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
    def get_nejm_credentials(self):
        """Get NEJM API credentials from Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId='nejm-api-credentials')
            credentials = json.loads(response['SecretString'])
            return f"{credentials['userid']}|{credentials['apikey']}"
        except Exception as e:
            print(f"❌ Could not get NEJM credentials: {e}")
            return None
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding using Bedrock Titan"""
        response = self.bedrock_client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": text})
        )
        result = json.loads(response['body'].read())
        return result['embedding']
    
    def fetch_nejm_articles(self, context: str = "nejm-ai", count: int = 10) -> List[Dict]:
        """Fetch articles from NEJM API"""
        print(f"🔍 Fetching {count} articles from {context}...")
        
        api_key = self.get_nejm_credentials()
        if not api_key:
            return []
        
        user_id, key = api_key.split('|', 1)
        headers = {
            "apiuser": user_id,
            "apikey": key
        }
        
        endpoint = f"{self.nejm_base_url}/api/v1/simple"
        params = {
            "context": context,
            "objectType": f"{context}-article",
            "sortBy": "pubdate-descending",
            "pageLength": count,
            "startPage": 1,
            "showFacets": "N"
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('results', [])
                print(f"✅ Found {len(articles)} articles")
                return articles
            else:
                print(f"❌ NEJM API error: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching articles: {e}")
            return []
    
    def process_article_for_opensearch(self, article: Dict) -> Dict:
        """Process article for OpenSearch format"""
        # Extract key information
        title = article.get('title', '')
        abstract = article.get('abstract', '')
        content = f"{title}. {abstract}"
        
        # Create embedding
        embedding = self.get_embedding(content)
        
        # Format for OpenSearch
        doc = {
            "title": title,
            "content": content,
            "abstract": abstract,
            "doi": article.get('doi', ''),
            "year": article.get('year'),
            "source": f"nejm-api-{article.get('context', 'unknown')}",
            "authors": article.get('authors', []),
            "vector": embedding,
            "timestamp": time.time()
        }
        
        return doc
    
    def ingest_to_opensearch_via_lambda(self, articles: List[Dict]):
        """Use Lambda function to ingest articles"""
        print("📤 Ingesting articles via Lambda function...")
        
        # For now, we'll use the research assistant Lambda to test
        # In a production setup, we'd have a dedicated ingestion Lambda
        
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        for i, article in enumerate(articles[:3], 1):  # Test with first 3 articles
            print(f"📝 Processing article {i}: {article.get('title', 'Unknown')[:50]}...")
            
            try:
                # Process article
                doc = self.process_article_for_opensearch(article)
                
                # For now, just show what we would ingest
                print(f"   ✅ Processed: {len(doc['content'])} chars, {len(doc['vector'])} dims")
                
            except Exception as e:
                print(f"   ❌ Error processing article {i}: {e}")
    
    def test_ingestion(self):
        """Test the ingestion process"""
        print("🧪 Testing AWS NEJM Ingestion")
        print("=" * 40)
        
        # Test 1: Fetch articles
        articles = self.fetch_nejm_articles("nejm-ai", 5)
        
        if not articles:
            print("❌ No articles fetched")
            return False
        
        # Test 2: Process articles
        print(f"\n📊 Processing {len(articles)} articles...")
        self.ingest_to_opensearch_via_lambda(articles)
        
        print("\n💡 Next steps:")
        print("1. Fix Lambda ingestion function to properly store in OpenSearch")
        print("2. Set up proper OpenSearch index mapping")
        print("3. Test end-to-end search functionality")
        
        return True

def main():
    ingester = AWSNEJMIngester()
    ingester.test_ingestion()

if __name__ == "__main__":
    main()