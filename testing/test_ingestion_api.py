#!/usr/bin/env python3
"""
Test the ingestion API functionality
"""

import requests
import json

def test_ingestion():
    """Test the ingestion endpoint"""
    
    api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
    
    print("🧪 Testing article ingestion...")
    
    test_payload = {
        "type": "ingestion",
        "source": "catalyst",
        "count": 2
    }
    
    try:
        print(f"   Requesting 2 articles from Catalyst...")
        
        response = requests.post(api_url, 
                               json=test_payload,
                               headers={'Content-Type': 'application/json'},
                               timeout=60)  # Longer timeout for ingestion
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Ingestion successful!")
            print(f"   📊 Requested: {result.get('requested_count')} articles")
            print(f"   📥 Ingested: {result.get('ingested_count')} articles")
            
            articles = result.get('articles', [])
            if articles:
                print(f"   📚 Article titles:")
                for i, article in enumerate(articles, 1):
                    title = article.get('title', 'Unknown Title')
                    print(f"      {i}. {title[:80]}{'...' if len(title) > 80 else ''}")
            
            return True
        else:
            print(f"   ❌ Ingestion failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing ingestion: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing NEJM Article Ingestion")
    print("=" * 40)
    
    success = test_ingestion()
    
    if success:
        print(f"\n🎉 Ingestion API is working!")
        print(f"   🌐 Website ingestion should now show article titles")
    else:
        print(f"\n❌ Ingestion API needs debugging")