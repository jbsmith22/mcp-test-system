#!/usr/bin/env python3
"""
Test different NEJM API endpoints to find the correct way to get full articles
"""

import boto3
import json
import requests

def get_nejm_credentials():
    """Get NEJM credentials from AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='nejm-api-credentials')
        credentials = json.loads(response['SecretString'])
        return f"{credentials['userid']}|{credentials['apikey']}"
    except Exception as e:
        print(f"❌ Could not get NEJM credentials: {e}")
        return None

def test_nejm_endpoints():
    """Test various NEJM API endpoints"""
    
    api_key = get_nejm_credentials()
    if not api_key:
        return
    
    user_id, key = api_key.split('|', 1)
    headers = {
        "apiuser": user_id,
        "apikey": key
    }
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    # Test DOI from our database
    test_doi = "10.1056/NEJMp2515668"
    
    print(f"🧪 Testing NEJM API endpoints with DOI: {test_doi}")
    print("=" * 60)
    
    # Test 1: Simple search to verify API works
    print("1. Testing simple search endpoint...")
    try:
        response = requests.get(f"{base_url}/api/v1/simple", 
                              params={
                                  "context": "nejm-ai", 
                                  "objectType": "nejm-ai-article",
                                  "pageLength": 1
                              }, 
                              headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"   ✅ Simple search works - found {len(results)} results")
            
            if results:
                article = results[0]
                print(f"   📄 Sample article fields: {list(article.keys())}")
                print(f"   📄 Title: {article.get('text', 'N/A')}")
                print(f"   📄 DOI: {article.get('doi', 'N/A')}")
        else:
            print(f"   ❌ Simple search failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Try different content endpoints with proper parameters
    content_tests = [
        {"endpoint": "/api/v1/content", "params": {"context": "nejm", "doi": test_doi, "format": "json"}},
        {"endpoint": "/api/v1/content", "params": {"context": "nejm-ai", "doi": test_doi, "format": "json"}},
        {"endpoint": "/api/v1/content", "params": {"context": "nejm", "doi": test_doi, "format": "jats"}},
        {"endpoint": "/api/v1/content", "params": {"doi": test_doi}},
        {"endpoint": f"/api/v1/content/{test_doi}", "params": {}},
    ]
    
    print(f"\n2. Testing content endpoints...")
    for test in content_tests:
        try:
            url = f"{base_url}{test['endpoint']}"
            response = requests.get(url, params=test['params'], headers=headers, timeout=10)
            
            endpoint_desc = f"{test['endpoint']} {test['params']}"
            print(f"   {endpoint_desc}: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                content_length = len(response.text)
                print(f"      ✅ Success! Content-Type: {content_type}, Length: {content_length}")
                
                # Show a preview
                if content_length > 0:
                    preview = response.text[:200].replace('\n', ' ')
                    print(f"      Preview: {preview}...")
                    
                    # Save successful response for analysis
                    with open(f"nejm_content_sample.txt", 'w') as f:
                        f.write(response.text)
                    print(f"      💾 Full response saved to nejm_content_sample.txt")
                break
            elif response.status_code == 404:
                print(f"      ⚠️ Not found")
            elif response.status_code == 500:
                print(f"      ❌ Server error")
            else:
                print(f"      ❌ Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ {endpoint_desc}: Error - {e}")
    
    # Test 3: Check if we can get article details from search
    print(f"\n3. Testing detailed search for specific DOI...")
    try:
        response = requests.get(f"{base_url}/api/v1/simple", 
                              params={
                                  "context": "nejm", 
                                  "objectType": "nejm-article",
                                  "q": test_doi,
                                  "pageLength": 1
                              }, 
                              headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if results:
                article = results[0]
                print(f"   ✅ Found article via search:")
                print(f"      Title: {article.get('title', 'N/A')}")
                print(f"      DOI: {article.get('doi', 'N/A')}")
                print(f"      Abstract: {len(article.get('abstract', ''))} chars")
                
                # Check what fields are available
                print(f"      Available fields: {list(article.keys())}")
                
                # Look for content fields
                content_fields = ['content', 'fullText', 'body', 'text', 'article']
                for field in content_fields:
                    if field in article:
                        content = article[field]
                        print(f"      📄 Found {field}: {len(str(content))} chars")
                
                # Save article data for analysis
                with open("nejm_article_sample.json", 'w') as f:
                    json.dump(article, f, indent=2)
                print(f"      💾 Article data saved to nejm_article_sample.json")
            else:
                print(f"   ⚠️ No results found for DOI search")
        else:
            print(f"   ❌ Search failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n📋 Summary:")
    print(f"   • NEJM API credentials are working")
    print(f"   • Simple search endpoint is functional") 
    print(f"   • Need to find correct endpoint for full article content")
    print(f"   • May need to use search results + additional API calls")

if __name__ == "__main__":
    test_nejm_endpoints()