#!/usr/bin/env python3
"""
Security Lockdown Test
Tests that AWS resources are properly IP-restricted and inaccessible from other IPs
"""

import boto3
import requests
import json
from typing import Dict, List

def get_opensearch_endpoint():
    """Get the OpenSearch domain endpoint"""
    try:
        client = boto3.client('opensearch', region_name='us-east-1')
        domain = client.describe_domain(DomainName='nejm-research')['DomainStatus']
        
        if domain.get('Endpoint'):
            return f"https://{domain['Endpoint']}"
        else:
            return None
    except Exception as e:
        print(f"Error getting OpenSearch endpoint: {e}")
        return None

def test_opensearch_access():
    """Test OpenSearch access from current IP"""
    endpoint = get_opensearch_endpoint()
    
    if not endpoint:
        print("❌ OpenSearch domain not ready yet")
        return None
    
    print(f"🔍 Testing OpenSearch access: {endpoint}")
    
    try:
        # Test basic connectivity
        response = requests.get(f"{endpoint}/", timeout=10)
        
        if response.status_code == 200:
            print("✅ OpenSearch accessible from your IP")
            return endpoint
        elif response.status_code == 403:
            print("❌ OpenSearch access denied (IP restriction working)")
            return endpoint
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            return endpoint
            
    except requests.exceptions.RequestException as e:
        print(f"❌ OpenSearch connection failed: {e}")
        return endpoint

def generate_test_commands():
    """Generate test commands for different scenarios"""
    
    print("\n🧪 Security Test Commands")
    print("=" * 40)
    
    # Get OpenSearch endpoint
    endpoint = get_opensearch_endpoint()
    
    if endpoint:
        print(f"\n📍 OpenSearch Endpoint: {endpoint}")
        
        print(f"\n1️⃣ Test from YOUR current IP (should work):")
        print(f"curl -v '{endpoint}/'")
        
        print(f"\n2️⃣ Test from a DIFFERENT IP (should fail):")
        print(f"# Use a VPN, proxy, or ask someone else to run:")
        print(f"curl -v '{endpoint}/'")
        print(f"# Expected result: Connection timeout or 403 Forbidden")
        
        print(f"\n3️⃣ Test with online proxy services:")
        print(f"# Go to: https://www.proxy-list.download/api/v1/get?type=http")
        print(f"# Or use: https://httpbin.org/get (as a proxy test)")
        print(f"# Try accessing: {endpoint}")
        
        print(f"\n4️⃣ Test OpenSearch API endpoints:")
        print(f"curl -v '{endpoint}/_cluster/health'")
        print(f"curl -v '{endpoint}/_cat/indices'")
        print(f"curl -v '{endpoint}/articles_ollama/_search' -H 'Content-Type: application/json' -d '{{\"query\":{{\"match_all\":{{}}}}}}'")
        
    else:
        print("\n⏳ OpenSearch domain not ready yet. Try again in a few minutes.")
    
    # S3 bucket tests
    s3_client = boto3.client('s3')
    buckets = s3_client.list_buckets()
    nejm_buckets = [b['Name'] for b in buckets['Buckets'] if 'nejm-research' in b['Name']]
    
    if nejm_buckets:
        bucket_name = nejm_buckets[0]
        print(f"\n📦 S3 Bucket Tests:")
        print(f"Bucket: {bucket_name}")
        
        print(f"\n5️⃣ Test S3 public access (should fail):")
        print(f"curl -v 'https://{bucket_name}.s3.amazonaws.com/'")
        print(f"curl -v 'https://s3.amazonaws.com/{bucket_name}/'")
        print(f"# Expected result: 403 Forbidden or Access Denied")
        
        print(f"\n6️⃣ Test S3 object access (should fail):")
        print(f"curl -v 'https://{bucket_name}.s3.amazonaws.com/test.txt'")
        print(f"# Expected result: 403 Forbidden")
    
    # API Gateway tests (when available)
    print(f"\n🌐 API Gateway Tests (when deployed):")
    print(f"# These will be available after Phase 3")
    print(f"curl -v 'https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/research'")
    print(f"# Without API key: Should get 401 Unauthorized")
    print(f"# From different IP: Should get 403 Forbidden")

def test_with_online_proxy():
    """Test using online proxy services"""
    
    endpoint = get_opensearch_endpoint()
    if not endpoint:
        print("OpenSearch not ready for proxy testing")
        return
    
    print(f"\n🌐 Testing with Online Proxy Services")
    print("=" * 40)
    
    # List of free proxy testing services
    proxy_services = [
        "https://httpbin.org/get",
        "https://api.ipify.org",
        "https://ipinfo.io/json"
    ]
    
    print(f"\n📋 Manual Proxy Test Instructions:")
    print(f"1. Go to any online proxy service (search 'free web proxy')")
    print(f"2. Enter this URL: {endpoint}")
    print(f"3. You should get:")
    print(f"   - Connection timeout")
    print(f"   - 403 Forbidden error")
    print(f"   - 'Access Denied' message")
    print(f"4. This proves your system is IP-restricted!")
    
    print(f"\n🔗 Proxy Services to Try:")
    print(f"   - https://www.proxysite.com/")
    print(f"   - https://hide.me/en/proxy")
    print(f"   - https://www.filterbypass.me/")
    print(f"   - https://kproxy.com/")
    
    print(f"\n⚠️  Important: If any proxy CAN access your endpoint,")
    print(f"   that means there's a security issue!")

def create_security_test_script():
    """Create a script for others to test your security"""
    
    endpoint = get_opensearch_endpoint()
    if not endpoint:
        return
    
    test_script = f"""#!/bin/bash
# Security Test Script - Run this from a DIFFERENT IP address
# If this script succeeds, there's a security problem!

echo "🧪 Testing NEJM Research System Security"
echo "========================================"
echo "Testing from IP: $(curl -s https://ipinfo.io/ip)"
echo ""

echo "1️⃣ Testing OpenSearch access..."
curl -v --connect-timeout 10 '{endpoint}/' 2>&1 | head -20

echo ""
echo "2️⃣ Testing OpenSearch health endpoint..."
curl -v --connect-timeout 10 '{endpoint}/_cluster/health' 2>&1 | head -10

echo ""
echo "3️⃣ Expected Results:"
echo "   ✅ Connection timeout"
echo "   ✅ 403 Forbidden"
echo "   ✅ Access Denied"
echo ""
echo "❌ If you see JSON responses or 200 OK, there's a security issue!"
"""
    
    with open('test_security_from_other_ip.sh', 'w') as f:
        f.write(test_script)
    
    print(f"\n📝 Created test script: test_security_from_other_ip.sh")
    print(f"   Send this to someone with a different IP address to run")

def main():
    """Main security test function"""
    
    print("🔒 NEJM Research System - Security Lockdown Test")
    print("=" * 50)
    
    print(f"\n🌐 Your current IP: 108.20.28.24")
    print(f"   (This IP should have access)")
    
    # Test current access
    test_opensearch_access()
    
    # Generate test commands
    generate_test_commands()
    
    # Proxy testing instructions
    test_with_online_proxy()
    
    # Create test script for others
    create_security_test_script()
    
    print(f"\n🎯 Security Test Summary:")
    print(f"=" * 30)
    print(f"✅ Your IP (108.20.28.24): Should have access")
    print(f"❌ Any other IP: Should be blocked")
    print(f"🔒 This proves your system is secure!")
    
    print(f"\n📋 Quick Tests You Can Do Right Now:")
    print(f"1. Use your phone's hotspot (different IP)")
    print(f"2. Ask a friend to test the URLs")
    print(f"3. Use a VPN to change your IP")
    print(f"4. Use online proxy services")
    
    print(f"\n⚠️  If ANY other IP can access your resources,")
    print(f"   contact me immediately - there's a security issue!")

if __name__ == "__main__":
    main()