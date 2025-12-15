#!/usr/bin/env python3
"""
Populate AWS OpenSearch with test articles for immediate functionality
"""

import boto3
import json
import requests
from typing import List, Dict

def create_test_articles():
    """Create some test medical articles for immediate testing"""
    
    test_articles = [
        {
            "id": "test-001",
            "title": "AI in Clinical Documentation: Current State and Future Directions",
            "content": "Artificial intelligence (AI) is revolutionizing clinical documentation by automating routine tasks, improving accuracy, and reducing physician burnout. Recent studies show that AI-powered documentation systems can reduce documentation time by up to 40% while maintaining clinical quality. Key technologies include natural language processing (NLP), automated speech recognition (ASR), and machine learning algorithms that can extract relevant clinical information from unstructured text.",
            "doi": "10.1056/test001",
            "year": 2024,
            "source": "test-data",
            "authors": ["Smith, J.", "Johnson, A."],
            "abstract": "This review examines the current state of AI in clinical documentation and explores future directions for implementation in healthcare systems."
        },
        {
            "id": "test-002", 
            "title": "Machine Learning Applications in Diagnostic Imaging",
            "content": "Machine learning algorithms are increasingly being used in diagnostic imaging to improve accuracy and efficiency. Deep learning models have shown remarkable performance in detecting various conditions including diabetic retinopathy, skin cancer, and pneumonia. These AI systems can analyze medical images faster than human radiologists while maintaining high accuracy rates. Implementation challenges include data privacy, algorithm transparency, and integration with existing healthcare workflows.",
            "doi": "10.1056/test002",
            "year": 2024,
            "source": "test-data", 
            "authors": ["Brown, M.", "Davis, K."],
            "abstract": "This study reviews machine learning applications in diagnostic imaging and discusses implementation strategies for healthcare systems."
        },
        {
            "id": "test-003",
            "title": "Natural Language Processing for Electronic Health Records",
            "content": "Natural language processing (NLP) technologies are transforming how healthcare organizations extract insights from electronic health records (EHRs). NLP can automatically identify clinical concepts, extract medication information, and detect adverse events from unstructured clinical notes. Recent advances in transformer-based models have significantly improved the accuracy of clinical NLP tasks. Applications include clinical decision support, quality measurement, and population health management.",
            "doi": "10.1056/test003", 
            "year": 2024,
            "source": "test-data",
            "authors": ["Wilson, R.", "Taylor, S."],
            "abstract": "This paper explores NLP applications for EHRs and discusses the potential for improving healthcare delivery through automated text analysis."
        }
    ]
    
    return test_articles

def get_bedrock_embedding(text: str) -> List[float]:
    """Get embedding using AWS Bedrock"""
    client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    response = client.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        body=json.dumps({
            "inputText": text
        })
    )
    
    result = json.loads(response['body'].read())
    return result['embedding']

def test_aws_research_api():
    """Test the AWS research API with a simple query"""
    print("🧪 Testing AWS Research API...")
    
    url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "YOUR_API_KEY_HERE"
    }
    
    payload = {
        "query": "What is artificial intelligence in healthcare?",
        "limit": 3
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API Test Successful!")
            print(f"📝 Answer length: {len(result.get('answer', ''))}")
            print(f"📊 Sources found: {len(result.get('sources', []))}")
            
            if result.get('sources'):
                print("✅ OpenSearch has content!")
                return True
            else:
                print("⚠️ OpenSearch appears empty (no sources returned)")
                return False
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API Test Failed: {e}")
        return False

def main():
    print("🚀 AWS OpenSearch Population Test")
    print("=" * 40)
    
    # First, test if there's already content
    has_content = test_aws_research_api()
    
    if has_content:
        print("\n🎉 Great! Your AWS OpenSearch already has searchable content!")
        print("The web interface should work now.")
    else:
        print("\n📋 OpenSearch appears empty. Here are your options:")
        print("\n1. 🔧 Fix Lambda ingestion function and populate from NEJM API")
        print("2. 📤 Import the exported articles_export.json (7,267 articles)")
        print("3. 🧪 Add test articles for immediate functionality")
        
        print(f"\n💾 Your local data has been exported to: articles_export.json")
        print(f"📊 File size: {len(open('articles_export.json').read()) / 1024 / 1024:.1f} MB")
        
        # Create test embeddings to verify Bedrock works
        print("\n🧪 Testing Bedrock embedding generation...")
        try:
            test_text = "This is a test for medical AI research"
            embedding = get_bedrock_embedding(test_text)
            print(f"✅ Bedrock embeddings working! Vector size: {len(embedding)}")
        except Exception as e:
            print(f"❌ Bedrock embedding failed: {e}")

if __name__ == "__main__":
    main()