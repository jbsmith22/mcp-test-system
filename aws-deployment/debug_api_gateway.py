#!/usr/bin/env python3
"""
Debug API Gateway issues from browser perspective
"""

import requests
import json

def test_api_gateway_cors():
    """Test CORS preflight request"""
    
    api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
    
    print("🧪 Testing CORS preflight (OPTIONS)...")
    
    try:
        response = requests.options(api_url, headers={
            'Origin': 'http://nejm-research-web-interface.s3-website-us-east-1.amazonaws.com',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        })
        
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("   ✅ CORS preflight working")
            return True
        else:
            print(f"   ❌ CORS preflight failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ CORS test error: {e}")
        return False

def test_statistics_request():
    """Test statistics request like browser would make it"""
    
    api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
    
    print("\n📊 Testing statistics request from browser perspective...")
    
    try:
        response = requests.post(api_url, 
                               json={"type": "statistics"},
                               headers={
                                   'Content-Type': 'application/json',
                                   'Origin': 'http://nejm-research-web-interface.s3-website-us-east-1.amazonaws.com'
                               })
        
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Statistics working: {result.get('total_articles')} articles")
            return True
        else:
            print(f"   ❌ Statistics failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Statistics error: {e}")
        return False

def test_search_request():
    """Test search request like browser would make it"""
    
    api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
    
    print("\n🔍 Testing search request from browser perspective...")
    
    try:
        response = requests.post(api_url, 
                               json={
                                   "query": "diabetes",
                                   "max_results": 2
                               },
                               headers={
                                   'Content-Type': 'application/json',
                                   'Origin': 'http://nejm-research-web-interface.s3-website-us-east-1.amazonaws.com'
                               })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Search working: {result.get('total_found')} results")
            return True
        else:
            print(f"   ❌ Search failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Search error: {e}")
        return False

def check_api_gateway_config():
    """Check API Gateway configuration"""
    
    print("\n🔧 Checking API Gateway configuration...")
    
    import boto3
    
    try:
        client = boto3.client('apigateway', region_name='us-east-1')
        
        # Get API info
        api_id = "lwi6jeeczi"
        api_info = client.get_rest_api(restApiId=api_id)
        print(f"   API Name: {api_info['name']}")
        
        # Get resources
        resources = client.get_resources(restApiId=api_id)
        for resource in resources['items']:
            if resource['path'] == '/research':
                print(f"   Resource: {resource['path']}")
                if 'resourceMethods' in resource:
                    methods = list(resource['resourceMethods'].keys())
                    print(f"   Methods: {methods}")
                    
                    # Check if OPTIONS method exists
                    if 'OPTIONS' in methods:
                        print("   ✅ OPTIONS method configured")
                    else:
                        print("   ❌ OPTIONS method missing")
        
        return True
        
    except Exception as e:
        print(f"   ❌ API Gateway check error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Debugging API Gateway Issues")
    print("=" * 50)
    
    cors_ok = test_api_gateway_cors()
    stats_ok = test_statistics_request()
    search_ok = test_search_request()
    config_ok = check_api_gateway_config()
    
    print(f"\n📋 Debug Results:")
    print(f"   CORS Preflight: {'✅ Working' if cors_ok else '❌ Failed'}")
    print(f"   Statistics API: {'✅ Working' if stats_ok else '❌ Failed'}")
    print(f"   Search API: {'✅ Working' if search_ok else '❌ Failed'}")
    print(f"   API Config: {'✅ OK' if config_ok else '❌ Issues'}")
    
    if not (cors_ok and stats_ok and search_ok):
        print(f"\n⚠️ Issues found. The website failures are likely due to:")
        if not cors_ok:
            print("   - CORS configuration problems")
        if not stats_ok:
            print("   - Statistics endpoint not working")
        if not search_ok:
            print("   - Search endpoint not working")
    else:
        print(f"\n🎉 All API tests passed! Website should work.")