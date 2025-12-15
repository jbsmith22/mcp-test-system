#!/usr/bin/env python3
"""
Test script for NEJM API integration
"""

from nejm_api_client import NEJMAPIClient

def test_api_connection():
    """Test basic API connectivity"""
    client = NEJMAPIClient()  # Now defaults to QA environment
    
    print("Testing NEJM API endpoints...")
    
    # Test without API key to see error message
    articles = client.get_recent_articles(limit=1)
    
    if not articles:
        print("\n🔑 API Key Required!")
        print("To use this API, you need to:")
        print("1. Get an API key from NEJM")
        print("2. Run: python nejm_api_client.py --api-key YOUR_KEY --dry-run --limit 3")
        print("3. Once working, remove --dry-run to start ingesting")
        
    return len(articles) > 0

def show_usage_examples():
    """Show usage examples"""
    print("\n📖 Usage Examples:")
    print("=" * 50)
    
    print("\n1. Test with API key (dry run - QA environment):")
    print("   python nejm_api_client.py --api-key YOUR_KEY --dry-run --limit 5")
    
    print("\n2. Ingest 10 recent NEJM articles (QA):")
    print("   python nejm_api_client.py --api-key YOUR_KEY --limit 10")
    
    print("\n3. Use production environment:")
    print("   python nejm_api_client.py --api-key YOUR_KEY --environment production --limit 5")
    
    print("\n4. Ingest from different journals:")
    print("   python nejm_api_client.py --api-key YOUR_KEY --context catalyst --limit 5")
    print("   python nejm_api_client.py --api-key YOUR_KEY --context evidence --limit 5")
    
    print("\n5. Available contexts:")
    print("   - nejm: New England Journal of Medicine")
    print("   - catalyst: NEJM Catalyst")
    print("   - evidence: NEJM Evidence")
    print("   - clinician: NEJM Journal Watch")
    print("   - nejm-ai: NEJM AI")
    
    print("\n6. Available environments:")
    print("   - qa: QA environment (default)")
    print("   - production: Production environment")

if __name__ == "__main__":
    test_api_connection()
    show_usage_examples()