#!/usr/bin/env python3
"""
Test the API Gateway endpoint to see if it can provide statistics
"""

import requests
import json

def test_stats_endpoint():
    """Test if the API can provide statistics"""
    
    api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
    
    # Test with a stats query
    test_payload = {
        "query": "stats",
        "type": "statistics"
    }
    
    try:
        print("🧪 Testing API Gateway for statistics...")
        print(f"URL: {api_url}")
        print(f"Payload: {json.dumps(test_payload, indent=2)}")
        
        response = requests.post(api_url, 
                               json=test_payload,
                               headers={'Content-Type': 'application/json'},
                               timeout=30)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Error Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def test_regular_search():
    """Test with a regular search to see the response format"""
    
    api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
    
    test_payload = {
        "query": "diabetes",
        "max_results": 1
    }
    
    try:
        print("\n🔍 Testing regular search...")
        
        response = requests.post(api_url, 
                               json=test_payload,
                               headers={'Content-Type': 'application/json'},
                               timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Regular search works!")
            print(f"Response keys: {list(result.keys())}")
            if 'sources' in result:
                print(f"Sources count: {len(result['sources'])}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing NEJM Research API for Statistics")
    print("=" * 50)
    
    # Test stats endpoint
    stats_works = test_stats_endpoint()
    
    # Test regular search
    search_works = test_regular_search()
    
    print(f"\n📋 Summary:")
    print(f"Stats endpoint: {'✅ Works' if stats_works else '❌ Not supported'}")
    print(f"Search endpoint: {'✅ Works' if search_works else '❌ Not working'}")