#!/usr/bin/env python3
"""
Test the fixed Lambda function
"""

import boto3
import json

def test_lambda_directly():
    """Test the Lambda function directly"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test statistics request
    print("🧪 Testing statistics request...")
    
    stats_payload = {
        "type": "statistics"
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='nejm-research-assistant',
            Payload=json.dumps(stats_payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ Statistics test result: {result}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            if body.get('type') == 'statistics':
                print(f"   📊 Total articles: {body.get('total_articles')}")
                print(f"   📋 Source breakdown: {body.get('source_breakdown')}")
                return True
        
        print(f"❌ Statistics test failed: {result}")
        return False
        
    except Exception as e:
        print(f"❌ Error testing statistics: {e}")
        return False

def test_search_request():
    """Test a search request"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("\n🔍 Testing search request...")
    
    search_payload = {
        "httpMethod": "POST",
        "requestContext": {
            "identity": {
                "sourceIp": "108.20.28.24"  # Your authorized IP
            }
        },
        "body": json.dumps({
            "query": "diabetes",
            "max_results": 2
        })
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='nejm-research-assistant',
            Payload=json.dumps(search_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            print(f"✅ Search test successful!")
            print(f"   🔍 Query: {body.get('query')}")
            print(f"   📚 Sources found: {body.get('total_found')}")
            return True
        else:
            print(f"❌ Search test failed: {result}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing search: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Fixed Lambda Function")
    print("=" * 40)
    
    stats_ok = test_lambda_directly()
    search_ok = test_search_request()
    
    print(f"\n📋 Test Results:")
    print(f"   Statistics: {'✅ Working' if stats_ok else '❌ Failed'}")
    print(f"   Search: {'✅ Working' if search_ok else '❌ Failed'}")
    
    if stats_ok and search_ok:
        print(f"\n🎉 All tests passed! Website should work now.")
    else:
        print(f"\n⚠️ Some tests failed. Check the logs.")