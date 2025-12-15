#!/usr/bin/env python3
"""
Migrate all 262 DOIs from local Qdrant to AWS OpenSearch
"""

import requests
import json
import boto3
from typing import List, Dict, Set
import time
import uuid
from datetime import datetime

class FullMigrator:
    def __init__(self):
        # AWS clients
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
        # Local Qdrant
        self.qdrant_url = "http://127.0.0.1:6333"
        self.collection = "articles_ollama"
        
        # NEJM API
        self.nejm_base_url = "https://onesearch-api.nejmgroup-qa.org"
        
        # OpenSearch
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        self.index_name = "nejm-articles"
        
        # AWS session for signing requests
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        
        # Statistics
        self.stats = {
            "total_dois": 0,
            "already_processed": 0,
            "api_success": 0,
            "api_failed": 0,
            "opensearch_success": 0,
            "opensearch_failed": 0,
            "start_time": datetime.now()
        }
        
    def get_nejm_credentials(self):
        """Get NEJM API credentials from AWS Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId='nejm-api-credentials')
            credentials = json.loads(response['SecretString'])
            return f"{credentials['userid']}|{credentials['apikey']}"
        except Exception as e:
            print(f"❌ Could not get NEJM credentials: {e}")
            return None
    
    def get_existing_dois_in_opensearch(self) -> Set[str]:
        """Get DOIs already in OpenSearch to avoid duplicates"""
        
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            # Search for all DOIs in OpenSearch
            search_body = {
                "query": {"match_all": {}},
                "size": 1000,  # Should be enough for our current data
                "_source": ["doi"]
            }
            
            url = f"{self.opensearch_endpoint}/{self.index_name}/_search"
            request = AWSRequest(method='POST', url=url, data=json.dumps(search_body))
            request.headers['Content-Type'] = 'application/json'
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            headers = dict(request.headers)
            response = requests.post(url, headers=headers, data=json.dumps(search_body))
            
            if response.status_code == 200:
                result = response.json()
                existing_dois = set()
                
                for hit in result["hits"]["hits"]:
                    doi = hit["_source"].get("doi")
                    if doi:
                        existing_dois.add(doi)
                
                print(f"📋 Found {len(existing_dois)} existing DOIs in OpenSearch")
                return existing_dois
            else:
                print(f"⚠️ Could not check existing DOIs: {response.status_code}")
                return set()
                
        except Exception as e:
            print(f"⚠️ Error checking existing DOIs: {e}")
            return set()
    
    def extract_all_dois_from_qdrant(self) -> Set[str]:
        """Extract all unique DOIs from local Qdrant database"""
        print("🔍 Extracting all DOIs from local Qdrant...")
        
        dois = set()
        offset = None
        batch_size = 100
        
        try:
            while True:
                scroll_request = {
                    "limit": batch_size,
                    "with_payload": True,
                    "with_vector": False
                }
                
                if offset:
                    scroll_request["offset"] = offset
                
                response = requests.post(
                    f"{self.qdrant_url}/collections/{self.collection}/points/scroll",
                    json=scroll_request
                )
                
                if response.status_code != 200:
                    print(f"❌ Error scrolling Qdrant: {response.text}")
                    break
                
                result = response.json()["result"]
                points = result["points"]
                
                if not points:
                    break
                
                # Extract DOIs from metadata
                for point in points:
                    metadata = point.get("payload", {}).get("metadata", {})
                    doi = metadata.get("doi")
                    if doi and doi != "N/A":
                        dois.add(doi)
                
                offset = result.get("next_page_offset")
                print(f"📥 Processed {len(points)} points, found {len(dois)} unique DOIs so far...")
                
                if not offset:
                    break
            
            print(f"✅ Found {len(dois)} unique DOIs in local database")
            return dois
            
        except Exception as e:
            print(f"❌ Error extracting DOIs: {e}")
            return set()
    
    def fetch_full_article_from_nejm(self, doi: str) -> Dict:
        """Fetch full article content from NEJM API using DOI"""
        api_key = self.get_nejm_credentials()
        if not api_key:
            return {"doi": doi, "success": False, "error": "No API credentials"}
        
        user_id, key = api_key.split('|', 1)
        headers = {
            "apiuser": user_id,
            "apikey": key
        }
        
        # Use the working content endpoint
        endpoint = f"{self.nejm_base_url}/api/v1/content"
        
        # Try different contexts
        contexts = ["nejm", "nejm-ai", "catalyst"]
        
        for context in contexts:
            params = {
                "context": context,
                "doi": doi,
                "format": "json"
            }
            
            try:
                response = requests.get(endpoint, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract the document content
                    document = data.get("document", "")
                    title = data.get("title", "")
                    abstract = data.get("displayAbstract", "")
                    
                    if title or document:  # Valid response
                        return {
                            "doi": doi,
                            "title": title,
                            "abstract": abstract,
                            "document": document,
                            "metadata": data,
                            "success": True,
                            "context": context
                        }
                
            except Exception as e:
                continue  # Try next context
        
        return {"doi": doi, "success": False, "error": "No valid response from any context"}
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding using Bedrock Titan"""
        # Limit text length for embedding
        text = text[:8000] if len(text) > 8000 else text
        
        response = self.bedrock_client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": text})
        )
        result = json.loads(response['body'].read())
        return result['embedding']
    
    def get_local_metadata_for_doi(self, doi: str) -> Dict:
        """Get metadata for a DOI from local Qdrant"""
        
        search_request = {
            "filter": {
                "must": [
                    {
                        "key": "metadata.doi",
                        "match": {"value": doi}
                    }
                ]
            },
            "limit": 1,
            "with_payload": True,
            "with_vector": False
        }
        
        try:
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection}/points/search",
                json=search_request
            )
            
            if response.status_code == 200:
                results = response.json()["result"]
                if results:
                    return results[0]["payload"]["metadata"]
            
            return {}
            
        except Exception as e:
            return {}
    
    def process_article_for_opensearch(self, article_data: Dict, local_metadata: Dict) -> Dict:
        """Process article for OpenSearch storage"""
        
        if not article_data.get("success"):
            return None
        
        doi = article_data["doi"]
        
        # Extract content from the API response
        title = article_data.get("title", local_metadata.get("title", "Unknown Title"))
        abstract = article_data.get("abstract", "")
        document = article_data.get("document", "")
        
        # Create comprehensive text content for embedding
        content_parts = []
        
        if title:
            content_parts.append(f"Title: {title}")
        
        if abstract:
            content_parts.append(f"Abstract: {abstract}")
        
        if document:
            content_parts.append(f"Full Article: {document}")
        
        text_content = "\n\n".join(content_parts)
        
        # Limit content length for embedding
        if len(text_content) > 8000:
            text_content = text_content[:8000]
        
        # Create embedding
        try:
            embedding = self.get_embedding(text_content)
        except Exception as e:
            print(f"   ❌ Embedding failed for {doi}: {e}")
            return None
        
        # Combine API data with local metadata
        doc = {
            "id": str(uuid.uuid4()),
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "content": text_content,
            "full_document": document,
            "year": local_metadata.get("year") or article_data.get("metadata", {}).get("publicationDate", "")[:4],
            "source": f"nejm-api-{article_data.get('context', 'full')}",
            "vector": embedding,
            "local_metadata": local_metadata,
            "api_metadata": article_data.get("metadata", {}),
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "content_format": "jats_xml_full"
        }
        
        return doc
    
    def insert_article_to_opensearch(self, article: Dict) -> bool:
        """Insert a single article into OpenSearch"""
        
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            doc_id = article["id"]
            url = f"{self.opensearch_endpoint}/{self.index_name}/_doc/{doc_id}"
            
            request = AWSRequest(method='PUT', url=url, data=json.dumps(article))
            request.headers['Content-Type'] = 'application/json'
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            headers = dict(request.headers)
            response = requests.put(url, headers=headers, data=json.dumps(article))
            
            return response.status_code in [200, 201]
                
        except Exception as e:
            return False
    
    def migrate_all_articles(self):
        """Migrate all articles from Qdrant to OpenSearch"""
        
        print("🚀 Full Article Migration: All 262 DOIs")
        print("=" * 60)
        
        # Step 1: Get all DOIs from local database
        all_dois = self.extract_all_dois_from_qdrant()
        self.stats["total_dois"] = len(all_dois)
        
        if not all_dois:
            print("❌ No DOIs found in local database")
            return False
        
        # Step 2: Check what's already in OpenSearch
        existing_dois = self.get_existing_dois_in_opensearch()
        new_dois = all_dois - existing_dois
        self.stats["already_processed"] = len(existing_dois)
        
        print(f"📊 Migration Plan:")
        print(f"   Total DOIs in Qdrant: {len(all_dois)}")
        print(f"   Already in OpenSearch: {len(existing_dois)}")
        print(f"   New DOIs to migrate: {len(new_dois)}")
        
        if not new_dois:
            print("✅ All articles already migrated!")
            return True
        
        # Step 3: Process new DOIs in batches
        new_dois_list = list(new_dois)
        batch_size = 10  # Process in smaller batches
        
        print(f"\n📥 Starting migration of {len(new_dois_list)} articles...")
        
        for i in range(0, len(new_dois_list), batch_size):
            batch = new_dois_list[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(new_dois_list) + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} DOIs)")
            
            for j, doi in enumerate(batch, 1):
                print(f"🔍 Processing {i+j}/{len(new_dois_list)}: {doi}")
                
                # Get local metadata
                local_metadata = self.get_local_metadata_for_doi(doi)
                
                # Fetch full article from NEJM
                article_data = self.fetch_full_article_from_nejm(doi)
                
                if article_data.get("success"):
                    self.stats["api_success"] += 1
                    
                    # Process for OpenSearch
                    doc = self.process_article_for_opensearch(article_data, local_metadata)
                    
                    if doc:
                        # Insert into OpenSearch
                        if self.insert_article_to_opensearch(doc):
                            self.stats["opensearch_success"] += 1
                            print(f"   ✅ Inserted: {doc['title'][:50]}...")
                        else:
                            self.stats["opensearch_failed"] += 1
                            print(f"   ❌ OpenSearch insert failed")
                    else:
                        self.stats["opensearch_failed"] += 1
                        print(f"   ❌ Processing failed")
                else:
                    self.stats["api_failed"] += 1
                    error = article_data.get("error", "Unknown error")
                    print(f"   ❌ API failed: {error}")
                
                # Rate limiting
                time.sleep(0.5)
            
            # Show progress after each batch
            self.show_progress()
            
            # Longer pause between batches
            if i + batch_size < len(new_dois_list):
                print("⏳ Pausing 5 seconds between batches...")
                time.sleep(5)
        
        # Final summary
        self.show_final_summary()
        return True
    
    def show_progress(self):
        """Show current progress"""
        elapsed = datetime.now() - self.stats["start_time"]
        
        print(f"\n📊 Progress Update:")
        print(f"   ✅ API Success: {self.stats['api_success']}")
        print(f"   ❌ API Failed: {self.stats['api_failed']}")
        print(f"   ✅ OpenSearch Success: {self.stats['opensearch_success']}")
        print(f"   ❌ OpenSearch Failed: {self.stats['opensearch_failed']}")
        print(f"   ⏱️ Elapsed: {elapsed}")
    
    def show_final_summary(self):
        """Show final migration summary"""
        elapsed = datetime.now() - self.stats["start_time"]
        
        print(f"\n🎯 Final Migration Summary")
        print("=" * 50)
        print(f"📊 Statistics:")
        print(f"   Total DOIs found: {self.stats['total_dois']}")
        print(f"   Already processed: {self.stats['already_processed']}")
        print(f"   API calls successful: {self.stats['api_success']}")
        print(f"   API calls failed: {self.stats['api_failed']}")
        print(f"   OpenSearch inserts successful: {self.stats['opensearch_success']}")
        print(f"   OpenSearch inserts failed: {self.stats['opensearch_failed']}")
        print(f"   Total time: {elapsed}")
        
        success_rate = (self.stats['opensearch_success'] / max(1, self.stats['api_success'])) * 100
        print(f"   Success rate: {success_rate:.1f}%")
        
        total_in_db = self.stats['already_processed'] + self.stats['opensearch_success']
        print(f"\n🎉 OpenSearch now contains {total_in_db} articles!")

def main():
    migrator = FullMigrator()
    
    print("🔄 Full Article Migration: All DOIs → AWS OpenSearch")
    print("=" * 70)
    
    success = migrator.migrate_all_articles()
    
    if success:
        print("\n🎉 Migration completed!")
        print("🌐 Your AWS OpenSearch database is now fully populated")
    else:
        print("\n❌ Migration failed - check logs above")

if __name__ == "__main__":
    main()