#!/usr/bin/env python3
"""
Test Bedrock access for embeddings and chat
"""

import boto3
import json

def test_bedrock():
    client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Test embedding
    print("🧪 Testing Titan Embeddings...")
    try:
        response = client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({
                "inputText": "This is a test for medical AI research"
            })
        )
        
        result = json.loads(response['body'].read())
        embedding = result['embedding']
        print(f"✅ Embedding successful! Vector size: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
        
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        return False
    
    # Test chat model
    print("\n🧪 Testing Claude 3.5 Sonnet...")
    try:
        response = client.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user", 
                        "content": "What is artificial intelligence in healthcare? Answer in one sentence."
                    }
                ]
            })
        )
        
        result = json.loads(response['body'].read())
        answer = result['content'][0]['text']
        print(f"✅ Chat successful!")
        print(f"   Answer: {answer}")
        
    except Exception as e:
        print(f"❌ Chat failed: {e}")
        return False
    
    print("\n🎉 Bedrock is fully functional!")
    return True

if __name__ == "__main__":
    test_bedrock()