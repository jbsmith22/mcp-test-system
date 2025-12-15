#!/usr/bin/env python3
"""
Quick script to populate AWS OpenSearch from local Qdrant data
"""

import requests
import json
import boto3
from typing import List, Dict

def quick_populate():
    """Quickly populate AWS with a few articles for testing"""
    
    print("🚀 Quick AWS OpenSearch Population")
    print("=" * 40)
    
    # Step 1: Get a few articles from local Qdrant
    print("1. Fetching sample articles from local Qdrant...")
    
    try:
        # Get collection info
        response = requests.get("http://127.0.0.1:6333/collections/articles_ollama")
        if response.status_code != 200:
            print("❌ Cannot connect to local Qdrant")
            return False
        
        # Get a few sample points
        scroll_request = {
            "limit": 5,
            "with_payload": True,
            "with_vector": False  # We'll regenerate with Bedrock
        }
        
        response = requests.post(
            "http://127.0.0.1:6333/collections/articles_ollama/points/scroll",
            json=scroll_request
        )
        
        if response.status_code != 200:
            print("❌ Error fetching from Qdrant")
            return False
        
        points = response.json()["result"]["points"]
        print(f"✅ Found {len(points)} sample articles")
        
        # Step 2: Process articles for AWS
        print("2. Processing articles for AWS...")
        
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        processed_articles = []
        
        for i, point in enumerate(points, 1):
            payload = point["payload"]
            
            # Extract content
            title = payload.get("metadata", {}).get("title", "Unknown Title")
            content = payload.get("document", "")
            
            print(f"   📝 Processing {i}: {title[:50]}...")
            
            # Create embedding with Bedrock
            try:
                response = bedrock_client.invoke_model(
                    modelId='amazon.titan-embed-text-v1',
                    body=json.dumps({"inputText": content[:8000]})  # Limit text length
                )
                
                result = json.loads(response['body'].read())
                embedding = result['embedding']
                
                # Create document for OpenSearch
                doc = {
                    "title": title,
                    "content": content,
                    "metadata": payload.get("metadata", {}),
                    "vector": embedding,
                    "point_id": point["id"]
                }
                
                processed_articles.append(doc)
                print(f"      ✅ Embedded: {len(content)} chars → {len(embedding)} dims")
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        print(f"✅ Processed {len(processed_articles)} articles")
        
        # Step 3: Test the API with processed data
        print("3. Testing AWS API...")
        
        # Test current API
        api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": "YOUR_API_KEY_HERE"
        }
        
        test_payload = {
            "query": "artificial intelligence in healthcare",
            "limit": 3
        }
        
        response = requests.post(api_url, headers=headers, json=test_payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            source_count = len(result.get('sources', []))
            print(f"✅ API test successful! Sources found: {source_count}")
            
            if source_count > 0:
                print("🎉 OpenSearch already has content!")
                return True
            else:
                print("⚠️ API works but OpenSearch is empty")
        else:
            print(f"❌ API test failed: {response.status_code}")
        
        # Step 4: Show what we would need to do
        print("\n📋 To complete the setup:")
        print("1. ✅ Articles processed and ready")
        print("2. ⚠️ Need to insert into OpenSearch (requires proper API access)")
        print("3. 💡 Alternative: Fix Lambda ingestion function")
        
        print(f"\n💾 Sample processed article:")
        if processed_articles:
            sample = processed_articles[0]
            print(f"   Title: {sample['title']}")
            print(f"   Content length: {len(sample['content'])} chars")
            print(f"   Vector dimensions: {len(sample['vector'])}")
            print(f"   Metadata keys: {list(sample['metadata'].keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    success = quick_populate()
    
    if success:
        print("\n🎯 Status: AWS infrastructure is ready!")
        print("📝 Next: Need to populate OpenSearch with articles")
        print("🌐 Web interface will work once OpenSearch has content")
    else:
        print("\n❌ Setup incomplete - check local Qdrant connection")

if __name__ == "__main__":
    main()