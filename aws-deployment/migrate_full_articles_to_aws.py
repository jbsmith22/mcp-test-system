#!/usr/bin/env python3
"""
Migrate articles from local Qdrant to AWS OpenSearch by fetching full text from NEJM API
"""

import requests
import json
import boto3
from typing import List, Dict, Set
import time
import uuid
from datetime import datetime

class FullArticleMigrator:
    def __init__(self):
        # AWS clients
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        # Local Qdrant
        self.qdrant_url = "http://127.0.0.1:6333"
        self.collection = "articles_ollama"
        
        # NEJM API
        self.nejm_base_url = "https://onesearch-api.nejmgroup-qa.org"
        
        # OpenSearch (via Lambda for now)
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        
    def get_nejm_credentials(self):
        """Get NEJM API credentials from AWS Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId='nejm-api-credentials')
            credentials = json.loads(response['SecretString'])
            return f"{credentials['userid']}|{credentials['apikey']}"
        except Exception as e:
            print(f"❌ Could not get NEJM credentials: {e}")
            return None
    
    def extract_dois_from_qdrant(self) -> Set[str]:
        """Extract unique DOIs from local Qdrant database"""
        print("🔍 Extracting DOIs from local Qdrant...")
        
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
            return None
        
        user_id, key = api_key.split('|', 1)
        headers = {
            "apiuser": user_id,
            "apikey": key
        }
        
        # Use the working content endpoint with proper parameters
        endpoint = f"{self.nejm_base_url}/api/v1/content"
        params = {
            "context": "nejm",  # Try nejm context first
            "doi": doi,
            "format": "json"  # Get JSON format with structured content
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract the document content (JATS XML)
                document = data.get("document", "")
                title = data.get("title", "")
                abstract = data.get("displayAbstract", "")
                
                return {
                    "doi": doi,
                    "title": title,
                    "abstract": abstract,
                    "document": document,  # Full JATS XML content
                    "metadata": data,  # Full API response for additional fields
                    "success": True
                }
            else:
                # Try with different context if nejm fails
                if params["context"] == "nejm":
                    params["context"] = "nejm-ai"
                    response = requests.get(endpoint, params=params, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "doi": doi,
                            "title": data.get("title", ""),
                            "abstract": data.get("displayAbstract", ""),
                            "document": data.get("document", ""),
                            "metadata": data,
                            "success": True
                        }
                
                print(f"   ⚠️ API error for {doi}: {response.status_code}")
                return {"doi": doi, "success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"   ❌ Error fetching {doi}: {e}")
            return {"doi": doi, "success": False, "error": str(e)}
    
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
            # The document contains JATS XML with full article text
            # For embedding, we'll use the raw XML (contains all text content)
            content_parts.append(f"Full Article: {document}")
        
        text_content = "\n\n".join(content_parts)
        
        # Limit content length for embedding (Bedrock has limits)
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
            "full_document": document,  # Store full JATS XML separately
            "year": local_metadata.get("year") or article_data.get("metadata", {}).get("publicationDate", "")[:4],
            "source": local_metadata.get("source", "nejm-api-full"),
            "vector": embedding,
            "local_metadata": local_metadata,
            "api_metadata": article_data.get("metadata", {}),
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "content_format": "jats_xml_full"
        }
        
        return doc
    
    def get_local_metadata_for_doi(self, doi: str) -> Dict:
        """Get metadata for a DOI from local Qdrant"""
        
        # Search for points with this DOI
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
            print(f"   ⚠️ Could not get metadata for {doi}: {e}")
            return {}
    
    def store_in_opensearch_via_lambda(self, documents: List[Dict]):
        """Store documents in OpenSearch via Lambda function"""
        print("📤 Storing documents in AWS OpenSearch...")
        
        # For now, we'll prepare the documents and show what would be stored
        # In a full implementation, we'd need to fix the Lambda function or use direct API
        
        print(f"📊 Prepared {len(documents)} documents for OpenSearch:")
        
        for i, doc in enumerate(documents, 1):
            print(f"   {i}. {doc['title'][:60]}...")
            print(f"      DOI: {doc['doi']}")
            print(f"      Content: {len(doc['content'])} chars")
            print(f"      Vector: {len(doc['vector'])} dims")
            print(f"      Source: {doc['source']}")
        
        # Save to file for manual import if needed
        output_file = "aws_migration_documents.json"
        with open(output_file, 'w') as f:
            json.dump(documents, f, indent=2)
        
        print(f"\n💾 Documents saved to {output_file}")
        print("🔧 Next: Use Lambda function or direct API to insert into OpenSearch")
    
    def migrate_sample_articles(self, limit: int = 5):
        """Migrate a sample of articles for testing"""
        print(f"🚀 Migrating Sample Articles to AWS ({limit} articles)")
        print("=" * 60)
        
        # Step 1: Get DOIs from local database
        all_dois = self.extract_dois_from_qdrant()
        
        if not all_dois:
            print("❌ No DOIs found in local database")
            return False
        
        # Take a sample for testing
        sample_dois = list(all_dois)[:limit]
        print(f"📋 Selected {len(sample_dois)} DOIs for migration")
        
        # Step 2: Fetch full articles from NEJM
        print("\n📥 Fetching full articles from NEJM API...")
        
        successful_articles = []
        
        for i, doi in enumerate(sample_dois, 1):
            print(f"🔍 Fetching {i}/{len(sample_dois)}: {doi}")
            
            # Get local metadata
            local_metadata = self.get_local_metadata_for_doi(doi)
            
            # Fetch full article
            article_data = self.fetch_full_article_from_nejm(doi)
            
            if article_data and article_data.get("success"):
                # Process for OpenSearch
                doc = self.process_article_for_opensearch(article_data, local_metadata)
                
                if doc:
                    successful_articles.append(doc)
                    print(f"   ✅ Processed: {len(doc['content'])} chars, {len(doc['vector'])} dims")
                else:
                    print(f"   ❌ Processing failed")
            else:
                print(f"   ❌ Fetch failed: {article_data.get('error', 'Unknown error') if article_data else 'No response'}")
            
            # Rate limiting
            time.sleep(1)
        
        print(f"\n✅ Successfully processed {len(successful_articles)} articles")
        
        # Step 3: Store in OpenSearch
        if successful_articles:
            self.store_in_opensearch_via_lambda(successful_articles)
            
            print(f"\n🎯 Migration Summary:")
            print(f"   📊 Total DOIs found: {len(all_dois)}")
            print(f"   🔍 DOIs attempted: {len(sample_dois)}")
            print(f"   ✅ Successfully processed: {len(successful_articles)}")
            print(f"   📈 Success rate: {len(successful_articles)/len(sample_dois)*100:.1f}%")
            
            return True
        else:
            print("❌ No articles successfully processed")
            return False

def main():
    migrator = FullArticleMigrator()
    
    print("🔄 Full Article Migration: Qdrant → NEJM API → AWS OpenSearch")
    print("=" * 70)
    
    # Test with a small sample first
    success = migrator.migrate_sample_articles(limit=3)
    
    if success:
        print("\n🎉 Sample migration successful!")
        print("💡 Ready to migrate more articles or integrate with OpenSearch")
    else:
        print("\n❌ Migration failed - check NEJM API access and credentials")

if __name__ == "__main__":
    main()