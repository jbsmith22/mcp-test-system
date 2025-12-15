#!/usr/bin/env python3
"""
Compare QA vs Production environments for NEJM API
"""

import requests
import sys

def test_environment(env_name, base_url):
    """Test basic connectivity to an environment"""
    print(f"\n🔍 Testing {env_name.upper()} Environment")
    print(f"URL: {base_url}")
    print("-" * 50)
    
    # Test health endpoint
    try:
        health_url = f"{base_url}/api/v1/health"
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Health check: OK")
        else:
            print(f"⚠️  Health check: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test simple search endpoint (without API key to see auth requirement)
    try:
        search_url = f"{base_url}/api/v1/simple"
        params = {
            "context": "nejm",
            "objectType": "nejm-article",
            "pageLength": 1
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 403:
            data = response.json()
            if "API Key" in data.get('data', {}).get('message', ''):
                print(f"✅ Search endpoint: Requires API key (expected)")
            else:
                print(f"⚠️  Search endpoint: {response.status_code} - {data}")
        else:
            print(f"⚠️  Search endpoint: Unexpected response {response.status_code}")
            
    except Exception as e:
        print(f"❌ Search endpoint failed: {e}")
        return False
    
    return True

def main():
    print("🔄 NEJM API Environment Comparison")
    print("=" * 60)
    
    environments = {
        "qa": "https://onesearch-api.nejmgroup-qa.org",
        "production": "https://onesearch-api.nejmgroup-production.org"
    }
    
    results = {}
    
    for env_name, base_url in environments.items():
        results[env_name] = test_environment(env_name, base_url)
    
    print(f"\n📊 Summary")
    print("=" * 20)
    
    for env_name, success in results.items():
        status = "✅ Available" if success else "❌ Issues"
        print(f"{env_name.upper()}: {status}")
    
    print(f"\n💡 Recommendation:")
    if results.get("qa"):
        print("Use QA environment for development and testing")
        print("Command: python nejm_api_client.py --api-key YOUR_KEY --dry-run")
    
    if results.get("production"):
        print("Use Production environment for live data ingestion")
        print("Command: python nejm_api_client.py --api-key YOUR_KEY --environment production")

if __name__ == "__main__":
    main()