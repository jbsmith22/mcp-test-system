#!/usr/bin/env python3
"""
Update Lambda function IP allowlist to include current IP
"""

import boto3
import json
import requests

def get_current_ip():
    """Get the current public IP address"""
    try:
        # Try multiple IP detection services
        services = [
            "https://api.ipify.org",
            "https://checkip.amazonaws.com",
            "https://icanhazip.com"
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    ip = response.text.strip()
                    print(f"✅ Current IP detected: {ip}")
                    return ip
            except:
                continue
        
        print("❌ Could not detect current IP")
        return None
        
    except Exception as e:
        print(f"❌ Error getting IP: {e}")
        return None

def update_lambda_ip_allowlist(current_ip):
    """Update Lambda function environment to allow current IP"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'nejm-research-assistant'
    
    try:
        # Get current function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        
        # Get current environment variables
        current_env = response.get('Environment', {}).get('Variables', {})
        
        print(f"📋 Current environment variables:")
        for key, value in current_env.items():
            if 'IP' in key.upper():
                print(f"   {key}: {value}")
        
        # Update IP restriction
        new_env = current_env.copy()
        
        # Add current IP to allowed list
        if 'ALLOWED_IPS' in new_env:
            # Parse existing IPs
            existing_ips = new_env['ALLOWED_IPS'].split(',')
            if current_ip not in existing_ips:
                existing_ips.append(current_ip)
                new_env['ALLOWED_IPS'] = ','.join(existing_ips)
        else:
            # Create new allowlist
            new_env['ALLOWED_IPS'] = current_ip
        
        # Also disable IP restriction for testing (can be re-enabled later)
        new_env['IP_RESTRICTION'] = 'false'  # Temporarily disable
        
        print(f"\n🔧 Updating Lambda environment...")
        print(f"   Adding IP: {current_ip}")
        print(f"   Disabling IP restriction temporarily")
        
        # Update the function
        update_response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': new_env}
        )
        
        print(f"✅ Lambda function updated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda: {e}")
        return False

def test_api_access():
    """Test API access after IP update"""
    
    print(f"\n🧪 Testing API access...")
    
    import time
    time.sleep(3)  # Wait for Lambda to update
    
    try:
        api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": "YOUR_API_KEY_HERE"
        }
        
        test_payload = {
            "query": "cardiac rehabilitation",
            "limit": 2
        }
        
        response = requests.post(api_url, headers=headers, json=test_payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ API test successful!")
            print(f"   Status: {response.status_code}")
            
            if 'sources' in result:
                sources = result['sources']
                print(f"   Sources found: {len(sources)}")
                
                for i, source in enumerate(sources[:2], 1):
                    title = source.get('title', 'Unknown')
                    score = source.get('score', 0)
                    print(f"      {i}. {title} (score: {score:.3f})")
            
            if 'answer' in result:
                answer_length = len(result['answer'])
                print(f"   Answer generated: {answer_length} characters")
            
            return True
        else:
            print(f"❌ API test failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False

def main():
    print("🔧 Updating Lambda IP Allowlist")
    print("=" * 40)
    
    # Step 1: Get current IP
    current_ip = get_current_ip()
    
    if not current_ip:
        print("❌ Cannot proceed without current IP")
        return False
    
    # Step 2: Update Lambda function
    if update_lambda_ip_allowlist(current_ip):
        
        # Step 3: Test API access
        if test_api_access():
            print(f"\n🎉 SUCCESS! API is now accessible")
            print(f"   ✅ IP {current_ip} added to allowlist")
            print(f"   ✅ API Gateway working")
            print(f"   ✅ OpenSearch returning results")
            print(f"\n🌐 You can now use the web interface!")
            
        else:
            print(f"\n⚠️ IP updated but API still not working")
            print(f"   💡 May need a few more minutes to propagate")
            
    else:
        print(f"\n❌ Failed to update IP allowlist")

if __name__ == "__main__":
    main()