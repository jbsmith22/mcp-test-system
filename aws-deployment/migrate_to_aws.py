#!/usr/bin/env python3
"""
Migrate articles from local Qdrant to AWS OpenSearch
"""

import requests
import json
import boto3
from typing import List, Dict
import time

class QdrantToOpenSearchMigrator:
    def __init__(self):
        self.qdrant_url = "http://127.0.0.1:6333"
        self.collection = "articles_ollama"
        
        # AWS OpenSearch configuration
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        self.opensearch_index = "articles"
        
        # AWS Bedrock for embeddings (to ensure consistency)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
    def export_from_qdrant(self) -> List[Dict]:
        """Export all articles from local Qdrant"""
        print("🔍 Exporting articles from local Qdrant...")
        
        try:
            # Get collection info
            response = requests.get(f"{self.qdrant_url}/collections/{self.collection}")
            if response.status_code != 200:
                print("❌ Cannot connect to local Qdrant. Make sure it's running.")
                return []
            
            collection_info = response.json()["result"]
            total_points = collection_info["points_count"]
            print(f"📊 Found {total_points} points in local Qdrant")
            
            # Export all points
            all_points = []
            offset = None
            batch_size = 100
            
            while True:
                scroll_request = {
                    "limit": batch_size,
                    "with_payload": True,
                    "with_vector": True
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
                
                all_points.extend(points)
                offset = result.get("next_page_offset")
                
                print(f"📥 Exported {len(all_points)} / {total_points} points...")
                
                if not offset:
                    break
            
            print(f"✅ Exported {len(all_points)} points from Qdrant")
            return all_points
            
        except Exception as e:
            print(f"❌ Error exporting from Qdrant: {e}")
            return []
    
    def create_opensearch_index(self):
        """Create the articles index in OpenSearch"""
        print("🏗️ Creating OpenSearch index...")
        
        # Note: This requires proper AWS authentication
        # For now, we'll use the Lambda function approach
        print("ℹ️ Index creation will be handled by Lambda function")
    
    def import_to_opensearch_via_lambda(self, articles: List[Dict]):
        """Import articles to OpenSearch via Lambda function"""
        print("📤 Importing articles to AWS OpenSearch via Lambda...")
        
        # We'll need to fix the Lambda function first
        print("⚠️ Lambda function needs dependency fixes")
        print("💡 Alternative: Use direct OpenSearch API with proper authentication")
    
    def migrate_articles(self):
        """Main migration process"""
        print("🚀 Starting migration from Qdrant to AWS OpenSearch...")
        
        # Step 1: Export from Qdrant
        articles = self.export_from_qdrant()
        
        if not articles:
            print("❌ No articles to migrate")
            return False
        
        # Step 2: Process articles for OpenSearch format
        print("🔄 Processing articles for OpenSearch format...")
        processed_articles = []
        
        for point in articles:
            article = {
                "id": point["id"],
                "vector": point["vector"],
                "payload": point["payload"]
            }
            processed_articles.append(article)
        
        print(f"✅ Processed {len(processed_articles)} articles")
        
        # Step 3: Save to file for manual import
        output_file = "articles_export.json"
        with open(output_file, 'w') as f:
            json.dump(processed_articles, f, indent=2)
        
        print(f"💾 Articles exported to {output_file}")
        print("📋 Next steps:")
        print("1. Fix Lambda function dependencies")
        print("2. Use Lambda or direct API to import articles")
        print("3. Verify articles are searchable in AWS")
        
        return True

def main():
    """Quick migration for immediate testing"""
    print("🧪 Quick NEJM Article Ingestion for Testing")
    print("=" * 50)
    
    # For immediate testing, let's use the NEJM API to get fresh articles
    # This bypasses the local Qdrant migration issue
    
    print("💡 Alternative approach: Ingest fresh articles directly from NEJM API")
    print("This will populate your AWS OpenSearch with new content for testing")
    
    # We can use the existing ingestion scripts but target AWS instead of local
    print("\n📋 To populate AWS OpenSearch:")
    print("1. Fix the Lambda function dependencies")
    print("2. Run: aws lambda invoke --function-name nejm-content-ingestion")
    print("3. Or use the web interface import functionality")
    
    # For now, let's try the migration
    migrator = QdrantToOpenSearchMigrator()
    migrator.migrate_articles()

if __name__ == "__main__":
    main()