#!/usr/bin/env python3
"""
Debug why Lambda function isn't finding sources in OpenSearch
"""

import boto3
import json

def check_lambda_environment():
    """Check Lambda function environment variables"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        response = lambda_client.get_function_configuration(FunctionName='nejm-research-assistant')
        
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        print("🔍 Lambda Environment Variables:")
        for key, value in env_vars.items():
            print(f"   {key}: {value}")
        
        # Check if OPENSEARCH_INDEX is set correctly
        index_name = env_vars.get('OPENSEARCH_INDEX', 'NOT SET')
        print(f"\n📋 Index Configuration:")
        print(f"   Expected: nejm-articles")
        print(f"   Actual: {index_name}")
        
        return index_name == 'nejm-articles'
        
    except Exception as e:
        print(f"❌ Error checking Lambda config: {e}")
        return False

def test_lambda_with_debug():
    """Test Lambda function with debug information"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create a test event that matches API Gateway format
    test_event = {
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/json",
            "x-api-key": "YOUR_API_KEY_HERE"
        },
        "requestContext": {
            "identity": {
                "sourceIp": "108.20.28.24"  # Current IP
            }
        },
        "body": json.dumps({
            "query": "cardiac",
            "limit": 1,
            "debug": True  # Add debug flag
        })
    }
    
    try:
        print("\n🧪 Testing Lambda function with debug...")
        
        response = lambda_client.invoke(
            FunctionName='nejm-research-assistant',
            Payload=json.dumps(test_event)
        )
        
        result = json.loads(response['Payload'].read())
        
        print(f"📊 Lambda Response:")
        print(f"   Status Code: {result.get('statusCode', 'N/A')}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result.get('body', '{}'))
            
            print(f"   Query: {body.get('query', 'N/A')}")
            print(f"   Sources: {len(body.get('sources', []))}")
            print(f"   Answer length: {len(body.get('answer', ''))}")
            
            # Look for debug information
            if 'debug' in body:
                print(f"   Debug info: {body['debug']}")
        else:
            print(f"   Error: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda test failed: {e}")
        return False

def fix_lambda_search_config():
    """Update Lambda function to ensure it searches the correct index"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Get current configuration
        response = lambda_client.get_function_configuration(FunctionName='nejm-research-assistant')
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Ensure correct configuration
        new_env = current_env.copy()
        new_env['OPENSEARCH_INDEX'] = 'nejm-articles'
        new_env['OPENSEARCH_ENDPOINT'] = 'https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com'
        
        # Make sure IP restriction is disabled for testing
        new_env['IP_RESTRICTION'] = 'false'
        
        print(f"🔧 Updating Lambda configuration...")
        
        lambda_client.update_function_configuration(
            FunctionName='nejm-research-assistant',
            Environment={'Variables': new_env}
        )
        
        print(f"✅ Lambda configuration updated")
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda: {e}")
        return False

def main():
    print("🔍 Debugging Lambda Search Issues")
    print("=" * 40)
    
    # Step 1: Check current configuration
    config_ok = check_lambda_environment()
    
    if not config_ok:
        print("\n🔧 Fixing Lambda configuration...")
        fix_lambda_search_config()
        
        import time
        time.sleep(3)  # Wait for update
    
    # Step 2: Test Lambda function
    test_lambda_with_debug()
    
    print(f"\n💡 If sources are still empty:")
    print(f"   1. Lambda function code may need updating")
    print(f"   2. OpenSearch permissions may need adjustment")
    print(f"   3. Index mapping may be different than expected")

if __name__ == "__main__":
    main()