#!/usr/bin/env python3
"""
Explore available content sources through NEJM API
"""

from nejm_api_client import NEJMAPIClient
from config_manager import ConfigManager
import json

def explore_context(client, context_name):
    """Explore what content is available in a specific context"""
    print(f"\n📚 {context_name.upper()} Context")
    print("=" * 50)
    
    try:
        # Test with different object types
        object_types = [
            f"{context_name}-article",
            f"{context_name}-media"
        ]
        
        for obj_type in object_types:
            print(f"\n🔍 Testing {obj_type}:")
            
            try:
                articles = client.get_recent_articles(limit=3, context=context_name)
                
                if articles:
                    print(f"✅ Found {len(articles)} items")
                    
                    # Show sample article structure
                    sample = articles[0]
                    print(f"📄 Sample content:")
                    print(f"   Title: {sample.get('text', 'N/A')[:100]}...")
                    print(f"   DOI: {sample.get('doi', 'N/A')}")
                    print(f"   Publication: {sample.get('publication', 'N/A')}")
                    print(f"   Date: {sample.get('pubdate', 'N/A')}")
                    
                    # Show available fields
                    fields = list(sample.keys())
                    print(f"   Available fields: {', '.join(fields[:10])}{'...' if len(fields) > 10 else ''}")
                    
                else:
                    print("❌ No content found")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Context error: {e}")

def main():
    print("🔍 NEJM API Content Sources Explorer")
    print("=" * 60)
    
    # Get API credentials
    config = ConfigManager()
    credentials = config.get_api_key("qa")
    
    if not credentials:
        print("❌ No API credentials found. Run setup_wizard.py first.")
        return
    
    # Initialize client
    client = NEJMAPIClient("https://onesearch-api.nejmgroup-qa.org")
    
    if '|' in credentials:
        user_id, key = credentials.split('|', 1)
        client.session.headers.update({
            "apiuser": user_id,
            "apikey": key
        })
    else:
        print("❌ Invalid credential format")
        return
    
    # Available contexts from API documentation
    contexts = [
        "nejm",        # New England Journal of Medicine
        "catalyst",    # NEJM Catalyst
        "evidence",    # NEJM Evidence  
        "clinician",   # NEJM Journal Watch
        "nejm-ai"      # NEJM AI
    ]
    
    # Explore each context
    for context in contexts:
        explore_context(client, context)
    
    # Test federated search
    print(f"\n📚 FEDERATED Context")
    print("=" * 50)
    print("🔍 Cross-journal search capability")
    
    try:
        # Federated search requires multiple object types
        endpoint = f"{client.base_url}/api/v1/simple"
        params = {
            "context": "federated",
            "objectType": "nejm-article;catalyst-article;evidence-article",
            "sortBy": "pubdate-descending",
            "pageLength": 5,
            "startPage": 1,
            "showFacets": "N"
        }
        
        response = client.session.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ Found {len(results)} federated results")
            
            # Show distribution by source
            sources = {}
            for result in results:
                pub = result.get('publication', 'Unknown')
                sources[pub] = sources.get(pub, 0) + 1
            
            print("📊 Content distribution:")
            for source, count in sources.items():
                print(f"   {source}: {count} articles")
                
        else:
            print(f"❌ Federated search failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Federated search error: {e}")
    
    print(f"\n📋 Summary")
    print("=" * 20)
    print("Available content sources:")
    print("• NEJM - New England Journal of Medicine (primary research)")
    print("• Catalyst - Healthcare delivery and innovation")  
    print("• Evidence - Evidence-based medicine reviews")
    print("• Clinician - Clinical practice and journal watch")
    print("• NEJM AI - Artificial intelligence in medicine")
    print("• Federated - Cross-journal search")
    
    print(f"\n💡 Usage Tips:")
    print("• Use specific contexts for targeted searches")
    print("• Use 'federated' to search across all journals")
    print("• Each context has both articles and media content")
    print("• Content is updated regularly with latest publications")

if __name__ == "__main__":
    main()