#!/usr/bin/env python3
"""
Fix Lambda function to use the correct OpenSearch index
"""

import boto3
import json

def update_lambda_environment():
    """Update Lambda environment variables to use correct index"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    function_name = 'nejm-research-assistant'
    
    try:
        # Get current function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        
        print(f"📋 Current Lambda configuration:")
        print(f"   Function: {response['FunctionName']}")
        print(f"   Runtime: {response['Runtime']}")
        print(f"   Timeout: {response['Timeout']}s")
        
        # Get current environment variables
        current_env = response.get('Environment', {}).get('Variables', {})
        print(f"   Current env vars: {list(current_env.keys())}")
        
        # Update environment variables
        new_env = current_env.copy()
        new_env['OPENSEARCH_INDEX'] = 'nejm-articles'  # Our index name
        new_env['OPENSEARCH_ENDPOINT'] = 'https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com'
        
        print(f"\n🔧 Updating environment variables...")
        
        # Update the function
        update_response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': new_env}
        )
        
        print(f"✅ Lambda function updated successfully")
        print(f"   New index: {new_env['OPENSEARCH_INDEX']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda: {e}")
        return False

def test_lambda_directly():
    """Test Lambda function directly"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    test_payload = {
        "query": "cardiac rehabilitation",
        "limit": 2
    }
    
    try:
        print(f"\n🧪 Testing Lambda function directly...")
        
        response = lambda_client.invoke(
            FunctionName='nejm-research-assistant',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        print(f"✅ Lambda test successful!")
        print(f"   Status: {response['StatusCode']}")
        
        if 'sources' in result:
            print(f"   Sources found: {len(result['sources'])}")
        
        if 'answer' in result:
            print(f"   Answer length: {len(result['answer'])} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda test failed: {e}")
        return False

def main():
    print("🔧 Fixing Lambda Function Index Configuration")
    print("=" * 50)
    
    # Step 1: Update environment variables
    if update_lambda_environment():
        print("\n⏳ Waiting for Lambda to update...")
        import time
        time.sleep(5)
        
        # Step 2: Test the function
        test_lambda_directly()
        
        print(f"\n🎯 Status:")
        print(f"   ✅ Lambda configured for index: nejm-articles")
        print(f"   🧪 Ready to test API Gateway")
        
    else:
        print("❌ Failed to update Lambda configuration")

if __name__ == "__main__":
    main()