#!/usr/bin/env python3
"""
Directly populate AWS OpenSearch with NEJM articles
"""

import boto3
import json
import requests
from typing import List, Dict
import time
import uuid

class DirectOpenSearchPopulator:
    def __init__(self):
        # AWS clients
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
        # OpenSearch configuration
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        self.index_name = "articles"
        
        # NEJM API
        self.nejm_base_url = "https://onesearch-api.nejmgroup-qa.org"
        
    def get_nejm_credentials(self):
        """Get NEJM credentials from Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId='nejm-api-credentials')
            credentials = json.loads(response['SecretString'])
            return f"{credentials['userid']}|{credentials['apikey']}"
        except Exception as e:
            print(f"❌ Could not get NEJM credentials: {e}")
            return None
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding using Bedrock"""
        response = self.bedrock_client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": text})
        )
        result = json.loads(response['body'].read())
        return result['embedding']
    
    def fetch_nejm_articles(self, context: str = "nejm-ai", count: int = 5) -> List[Dict]:
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
    
    def create_opensearch_index(self):
        """Create OpenSearch index with proper mapping"""
        print("🏗️ Creating OpenSearch index...")
        
        # Use AWS SDK to create index via OpenSearch API
        # For now, we'll use the Lambda function approach
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        # Create a simple test document to initialize the index
        test_payload = {
            "action": "create_index",
            "index": self.index_name
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName='nejm-research-assistant',
                Payload=json.dumps(test_payload)
            )
            
            result = json.loads(response['Payload'].read())
            print(f"📋 Lambda response: {result}")
            
        except Exception as e:
            print(f"⚠️ Could not create index via Lambda: {e}")
            print("💡 Index will be created automatically when we add documents")
    
    def populate_with_test_articles(self):
        """Populate with a few test articles to make search work"""
        print("🧪 Populating with test articles...")
        
        # Fetch real articles from NEJM
        articles = self.fetch_nejm_articles("nejm-ai", 3)
        
        if not articles:
            print("❌ No articles fetched, using hardcoded test data")
            articles = [
                {
                    "title": "AI in Clinical Documentation: Current State and Future Directions",
                    "abstract": "Artificial intelligence is revolutionizing clinical documentation by automating routine tasks and improving accuracy.",
                    "doi": "10.1056/test001",
                    "year": 2024,
                    "context": "test"
                }
            ]
        
        # Process and store articles
        for i, article in enumerate(articles, 1):
            print(f"📝 Processing article {i}: {article.get('title', 'Unknown')[:50]}...")
            
            try:
                # Create content for embedding
                title = article.get('title', '')
                abstract = article.get('abstract', '')
                content = f"{title}. {abstract}"
                
                # Get embedding
                embedding = self.get_embedding(content)
                
                # Create document
                doc = {
                    "title": title,
                    "content": content,
                    "abstract": abstract,
                    "doi": article.get('doi', ''),
                    "year": article.get('year'),
                    "source": f"nejm-api-{article.get('context', 'unknown')}",
                    "authors": article.get('authors', []),
                    "vector": embedding,
                    "timestamp": time.time(),
                    "id": str(uuid.uuid4())
                }
                
                print(f"   ✅ Created document: {len(content)} chars, {len(embedding)} dims")
                
                # For now, just show what we would store
                # In a full implementation, we'd use the OpenSearch API
                
            except Exception as e:
                print(f"   ❌ Error processing article {i}: {e}")
        
        print("\n💡 Articles processed successfully!")
        print("🔧 Next step: Use Lambda function to actually store in OpenSearch")
    
    def test_via_lambda(self):
        """Test populating via Lambda function"""
        print("🧪 Testing population via Lambda...")
        
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        # Test with a simple query first
        test_payload = {
            "query": "What is artificial intelligence in healthcare?",
            "limit": 3
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName='nejm-research-assistant',
                Payload=json.dumps(test_payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if 'sources' in result:
                source_count = len(result.get('sources', []))
                print(f"✅ Lambda test successful! Found {source_count} sources")
                
                if source_count == 0:
                    print("⚠️ OpenSearch appears empty - need to populate it")
                    return False
                else:
                    print("🎉 OpenSearch has content!")
                    return True
            else:
                print(f"📋 Lambda response: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Lambda test failed: {e}")
            return False

def main():
    print("🚀 Direct OpenSearch Population")
    print("=" * 40)
    
    populator = DirectOpenSearchPopulator()
    
    # Test current state
    has_content = populator.test_via_lambda()
    
    if has_content:
        print("\n🎉 Great! OpenSearch already has content.")
        print("Your web interface should work for searches now.")
    else:
        print("\n📋 OpenSearch appears empty. Let's populate it...")
        
        # Try to populate
        populator.populate_with_test_articles()
        
        print("\n💡 To complete the setup:")
        print("1. The Lambda ingestion function needs to be fixed")
        print("2. Or we need to use direct OpenSearch API calls")
        print("3. For now, the API will generate answers without sources")

if __name__ == "__main__":
    main()