#!/usr/bin/env python3
"""
Direct insertion of processed articles into AWS OpenSearch
"""

import json
import boto3
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict
import time

class DirectOpenSearchInserter:
    def __init__(self):
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        self.index_name = "nejm-articles"
        
        # AWS session for signing requests
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        
    def load_processed_articles(self, filename: str = "aws_migration_documents.json") -> List[Dict]:
        """Load processed articles from JSON file"""
        try:
            with open(filename, 'r') as f:
                articles = json.load(f)
            print(f"✅ Loaded {len(articles)} processed articles")
            return articles
        except Exception as e:
            print(f"❌ Error loading articles: {e}")
            return []
    
    def create_index_if_not_exists(self):
        """Create OpenSearch index with proper mapping"""
        
        # Index mapping for our articles
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "doi": {"type": "keyword"},
                    "title": {"type": "text", "analyzer": "standard"},
                    "abstract": {"type": "text", "analyzer": "standard"},
                    "content": {"type": "text", "analyzer": "standard"},
                    "full_document": {"type": "text", "index": False},  # Store but don't index XML
                    "year": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "vector": {
                        "type": "knn_vector",
                        "dimension": 1536,  # Titan embedding dimension
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "ingestion_timestamp": {"type": "date"},
                    "content_format": {"type": "keyword"}
                }
            },
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            }
        }
        
        # Check if index exists
        check_url = f"{self.opensearch_endpoint}/{self.index_name}"
        
        try:
            # Use AWS credentials for authentication
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            # Create request
            request = AWSRequest(method='HEAD', url=check_url)
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            # Convert to requests format
            headers = dict(request.headers)
            response = requests.head(check_url, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Index '{self.index_name}' already exists")
                return True
            elif response.status_code == 404:
                print(f"📝 Creating index '{self.index_name}'...")
                
                # Create index
                create_request = AWSRequest(method='PUT', url=check_url, data=json.dumps(mapping))
                create_request.headers['Content-Type'] = 'application/json'
                SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(create_request)
                
                headers = dict(create_request.headers)
                response = requests.put(check_url, headers=headers, data=json.dumps(mapping))
                
                if response.status_code in [200, 201]:
                    print(f"✅ Index '{self.index_name}' created successfully")
                    return True
                else:
                    print(f"❌ Failed to create index: {response.status_code} - {response.text}")
                    return False
            else:
                print(f"❌ Error checking index: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error with index operations: {e}")
            return False
    
    def insert_article(self, article: Dict) -> bool:
        """Insert a single article into OpenSearch"""
        
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            # Use the article ID as document ID
            doc_id = article["id"]
            url = f"{self.opensearch_endpoint}/{self.index_name}/_doc/{doc_id}"
            
            # Create request
            request = AWSRequest(method='PUT', url=url, data=json.dumps(article))
            request.headers['Content-Type'] = 'application/json'
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            # Make request
            headers = dict(request.headers)
            response = requests.put(url, headers=headers, data=json.dumps(article))
            
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"   ❌ Insert failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error inserting article: {e}")
            return False
    
    def bulk_insert_articles(self, articles: List[Dict]) -> int:
        """Insert multiple articles using bulk API"""
        
        if not articles:
            print("❌ No articles to insert")
            return 0
        
        print(f"📤 Bulk inserting {len(articles)} articles...")
        
        # Prepare bulk request body
        bulk_body = []
        
        for article in articles:
            # Index action
            action = {
                "index": {
                    "_index": self.index_name,
                    "_id": article["id"]
                }
            }
            bulk_body.append(json.dumps(action))
            bulk_body.append(json.dumps(article))
        
        bulk_data = "\n".join(bulk_body) + "\n"
        
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            url = f"{self.opensearch_endpoint}/_bulk"
            
            # Create request
            request = AWSRequest(method='POST', url=url, data=bulk_data)
            request.headers['Content-Type'] = 'application/x-ndjson'
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            # Make request
            headers = dict(request.headers)
            response = requests.post(url, headers=headers, data=bulk_data)
            
            if response.status_code == 200:
                result = response.json()
                
                # Count successful insertions
                successful = 0
                errors = []
                
                for item in result.get("items", []):
                    if "index" in item:
                        if item["index"].get("status") in [200, 201]:
                            successful += 1
                        else:
                            errors.append(item["index"].get("error", "Unknown error"))
                
                print(f"✅ Bulk insert completed: {successful}/{len(articles)} successful")
                
                if errors:
                    print(f"⚠️ Errors encountered:")
                    for error in errors[:3]:  # Show first 3 errors
                        print(f"   - {error}")
                
                return successful
            else:
                print(f"❌ Bulk insert failed: {response.status_code} - {response.text}")
                return 0
                
        except Exception as e:
            print(f"❌ Error in bulk insert: {e}")
            return 0
    
    def verify_insertion(self) -> Dict:
        """Verify articles were inserted correctly"""
        
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            # Get index stats
            url = f"{self.opensearch_endpoint}/{self.index_name}/_stats"
            
            request = AWSRequest(method='GET', url=url)
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            headers = dict(request.headers)
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                stats = response.json()
                doc_count = stats["indices"][self.index_name]["total"]["docs"]["count"]
                
                print(f"📊 Index verification:")
                print(f"   Documents: {doc_count}")
                print(f"   Index size: {stats['indices'][self.index_name]['total']['store']['size_in_bytes']} bytes")
                
                return {"doc_count": doc_count, "success": True}
            else:
                print(f"❌ Verification failed: {response.status_code}")
                return {"success": False}
                
        except Exception as e:
            print(f"❌ Error verifying insertion: {e}")
            return {"success": False}
    
    def test_search(self, query: str = "cardiac rehabilitation") -> bool:
        """Test search functionality"""
        
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            # Simple text search
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "abstract", "content"]
                    }
                },
                "size": 3
            }
            
            url = f"{self.opensearch_endpoint}/{self.index_name}/_search"
            
            request = AWSRequest(method='POST', url=url, data=json.dumps(search_body))
            request.headers['Content-Type'] = 'application/json'
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            headers = dict(request.headers)
            response = requests.post(url, headers=headers, data=json.dumps(search_body))
            
            if response.status_code == 200:
                result = response.json()
                hits = result["hits"]["hits"]
                
                print(f"🔍 Search test for '{query}':")
                print(f"   Found {len(hits)} results")
                
                for i, hit in enumerate(hits, 1):
                    title = hit["_source"]["title"]
                    score = hit["_score"]
                    print(f"   {i}. {title} (score: {score:.2f})")
                
                return len(hits) > 0
            else:
                print(f"❌ Search test failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error in search test: {e}")
            return False

def main():
    print("🚀 Direct OpenSearch Article Insertion")
    print("=" * 50)
    
    inserter = DirectOpenSearchInserter()
    
    # Step 1: Load processed articles
    articles = inserter.load_processed_articles()
    
    if not articles:
        print("❌ No articles to insert")
        return False
    
    # Step 2: Create index
    if not inserter.create_index_if_not_exists():
        print("❌ Failed to create/verify index")
        return False
    
    # Step 3: Insert articles
    successful = inserter.bulk_insert_articles(articles)
    
    if successful == 0:
        print("❌ No articles were inserted")
        return False
    
    # Step 4: Verify insertion
    print("\n🔍 Verifying insertion...")
    time.sleep(2)  # Wait for indexing
    
    verification = inserter.verify_insertion()
    
    if not verification.get("success"):
        print("❌ Verification failed")
        return False
    
    # Step 5: Test search
    print("\n🔍 Testing search functionality...")
    search_success = inserter.test_search()
    
    if search_success:
        print("\n🎉 SUCCESS! OpenSearch is now populated and searchable")
        print("🌐 Web interface should now work properly")
        
        print(f"\n📊 Final Status:")
        print(f"   ✅ Articles inserted: {successful}")
        print(f"   ✅ Index created: {inserter.index_name}")
        print(f"   ✅ Search working: Yes")
        print(f"   🌐 Ready for web interface")
        
        return True
    else:
        print("⚠️ Articles inserted but search test failed")
        return False

if __name__ == "__main__":
    main()