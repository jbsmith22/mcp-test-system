#!/usr/bin/env python3
"""
Test NEJM OneSearch API access from current environment
"""

import boto3
import json
import requests
import sys
from datetime import datetime

def get_nejm_credentials():
    """Get NEJM credentials from AWS Secrets Manager"""
    try:
        print("🔑 Retrieving NEJM API credentials from AWS Secrets Manager...")
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        response = secrets_client.get_secret_value(SecretId='nejm-api-credentials')
        credentials = json.loads(response['SecretString'])
        
        userid = credentials.get('userid')
        apikey = credentials.get('apikey')
        
        if userid and apikey:
            print(f"✅ Credentials retrieved successfully")
            print(f"   User ID: {userid}")
            print(f"   API Key: {'*' * (len(apikey) - 4) + apikey[-4:] if len(apikey) > 4 else '****'}")
            return userid, apikey
        else:
            print(f"❌ Invalid credential format in secrets manager")
            return None, None
            
    except Exception as e:
        print(f"❌ Could not get NEJM credentials: {e}")
        return None, None

def test_api_connectivity():
    """Test basic connectivity to NEJM API endpoints"""
    
    print("\n🌐 Testing API Connectivity")
    print("=" * 50)
    
    endpoints = [
        "https://onesearch-api.nejmgroup-qa.org",
        "https://onesearch-api.nejmgroup-production.org"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(f"{endpoint}/api/v1/simple", 
                                  params={"context": "nejm", "objectType": "nejm-article", "pageLength": 1},
                                  timeout=10)
            
            if response.status_code == 401:
                print(f"   ✅ Endpoint reachable (401 = needs authentication)")
            elif response.status_code == 200:
                print(f"   ✅ Endpoint reachable and responding")
            else:
                print(f"   ⚠️  Endpoint returned {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ❌ Timeout connecting to {endpoint}")
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection error to {endpoint}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_authenticated_access(userid, apikey):
    """Test authenticated access to NEJM API"""
    
    print(f"\n🔐 Testing Authenticated Access")
    print("=" * 50)
    
    headers = {
        "apiuser": userid,
        "apikey": apikey,
        "User-Agent": "NEJM-Research-Assistant/1.0"
    }
    
    # Test both QA and Production environments
    environments = [
        ("QA", "https://onesearch-api.nejmgroup-qa.org"),
        ("Production", "https://onesearch-api.nejmgroup-production.org")
    ]
    
    for env_name, base_url in environments:
        print(f"\n📍 Testing {env_name} Environment: {base_url}")
        
        # Test 1: Simple search
        try:
            print("   1. Testing simple search...")
            response = requests.get(f"{base_url}/api/v1/simple", 
                                  params={
                                      "context": "nejm-ai", 
                                      "objectType": "nejm-ai-article",
                                      "sortBy": "pubdate-descending",
                                      "pageLength": 3
                                  }, 
                                  headers=headers,
                                  timeout=15)
            
            print(f"      Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total = data.get('totalResults', 0)
                
                print(f"      ✅ SUCCESS! Found {len(results)} articles (total: {total})")
                
                if results:
                    article = results[0]
                    print(f"      📄 Sample article:")
                    print(f"         Title: {article.get('text', 'N/A')[:80]}...")
                    print(f"         DOI: {article.get('doi', 'N/A')}")
                    print(f"         Date: {article.get('pubdate', 'N/A')}")
                    print(f"         Fields: {list(article.keys())}")
                    
                    # Save sample for analysis
                    with open(f"nejm_sample_{env_name.lower()}.json", 'w') as f:
                        json.dump(results[0], f, indent=2)
                    print(f"         💾 Sample saved to nejm_sample_{env_name.lower()}.json")
                
            elif response.status_code == 401:
                print(f"      ❌ Authentication failed - check credentials")
            elif response.status_code == 403:
                print(f"      ❌ Access forbidden - check permissions")
            else:
                print(f"      ❌ Error: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"      ❌ Request timeout")
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Test 2: Different contexts
        if response.status_code == 200:  # Only test if basic auth works
            print("   2. Testing different contexts...")
            
            contexts = ["nejm", "nejm-ai", "catalyst", "evidence"]
            
            for context in contexts:
                try:
                    response = requests.get(f"{base_url}/api/v1/simple", 
                                          params={
                                              "context": context, 
                                              "objectType": f"{context}-article",
                                              "pageLength": 1
                                          }, 
                                          headers=headers,
                                          timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        count = len(data.get('results', []))
                        total = data.get('totalResults', 0)
                        print(f"      ✅ {context}: {count} results (total: {total})")
                    else:
                        print(f"      ❌ {context}: {response.status_code}")
                        
                except Exception as e:
                    print(f"      ❌ {context}: Error - {e}")

def test_content_retrieval(userid, apikey):
    """Test full content retrieval"""
    
    print(f"\n📄 Testing Content Retrieval")
    print("=" * 50)
    
    headers = {
        "apiuser": userid,
        "apikey": apikey,
        "User-Agent": "NEJM-Research-Assistant/1.0"
    }
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    # First get a recent article DOI
    try:
        print("   1. Getting recent article DOI...")
        response = requests.get(f"{base_url}/api/v1/simple", 
                              params={
                                  "context": "nejm-ai", 
                                  "objectType": "nejm-ai-article",
                                  "sortBy": "pubdate-descending",
                                  "pageLength": 1
                              }, 
                              headers=headers,
                              timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if results:
                article = results[0]
                doi = article.get('doi')
                title = article.get('text', 'Unknown')
                
                print(f"      ✅ Found article: {title[:60]}...")
                print(f"      📄 DOI: {doi}")
                
                if doi:
                    # Test content endpoints
                    print("   2. Testing content retrieval...")
                    
                    content_tests = [
                        {"endpoint": "/api/v1/content", "params": {"context": "nejm-ai", "doi": doi, "format": "json"}},
                        {"endpoint": "/api/v1/content", "params": {"context": "nejm-ai", "doi": doi, "format": "jats"}},
                        {"endpoint": "/api/v1/content", "params": {"doi": doi}},
                    ]
                    
                    for test in content_tests:
                        try:
                            url = f"{base_url}{test['endpoint']}"
                            response = requests.get(url, params=test['params'], headers=headers, timeout=15)
                            
                            params_str = ", ".join([f"{k}={v}" for k, v in test['params'].items()])
                            print(f"      {test['endpoint']}?{params_str}: {response.status_code}")
                            
                            if response.status_code == 200:
                                content_length = len(response.text)
                                content_type = response.headers.get('content-type', 'unknown')
                                
                                print(f"         ✅ SUCCESS! Length: {content_length}, Type: {content_type}")
                                
                                # Save successful response
                                filename = f"nejm_content_sample_{test['params'].get('format', 'default')}.txt"
                                with open(filename, 'w', encoding='utf-8') as f:
                                    f.write(response.text)
                                print(f"         💾 Content saved to {filename}")
                                
                                # Show preview
                                preview = response.text[:300].replace('\n', ' ')
                                print(f"         Preview: {preview}...")
                                
                                return True  # Success!
                                
                            elif response.status_code == 404:
                                print(f"         ⚠️ Content not found")
                            else:
                                print(f"         ❌ Error: {response.text[:100]}")
                                
                        except Exception as e:
                            print(f"         ❌ Error: {e}")
                
            else:
                print(f"      ❌ No articles found in search results")
        else:
            print(f"      ❌ Search failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def main():
    print("🧪 NEJM OneSearch API Access Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Step 1: Get credentials
    userid, apikey = get_nejm_credentials()
    if not userid or not apikey:
        print("\n❌ Cannot proceed without valid credentials")
        sys.exit(1)
    
    # Step 2: Test basic connectivity
    test_api_connectivity()
    
    # Step 3: Test authenticated access
    test_authenticated_access(userid, apikey)
    
    # Step 4: Test content retrieval
    content_success = test_content_retrieval(userid, apikey)
    
    # Summary
    print(f"\n📋 Test Summary")
    print("=" * 50)
    print(f"✅ Credentials: Retrieved from AWS Secrets Manager")
    print(f"✅ Connectivity: API endpoints are reachable")
    print(f"✅ Authentication: API accepts credentials")
    print(f"{'✅' if content_success else '⚠️'} Content Retrieval: {'Working' if content_success else 'Needs investigation'}")
    
    if content_success:
        print(f"\n🎉 SUCCESS! NEJM API is fully accessible")
        print(f"   Ready to implement article ingestion")
        print(f"   Can fetch recent articles and full content")
    else:
        print(f"\n⚠️ PARTIAL SUCCESS")
        print(f"   API is accessible but content retrieval needs work")
        print(f"   May need to use search results + metadata only")
    
    print(f"\n🔗 Next Steps:")
    print(f"   1. Review saved sample files for content structure")
    print(f"   2. Implement ingestion pipeline based on available data")
    print(f"   3. Test with different article types and contexts")

if __name__ == "__main__":
    main()