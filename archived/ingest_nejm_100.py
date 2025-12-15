#!/usr/bin/env python3
"""
Ingest 100 articles from the main NEJM journal
"""

import sys
from nejm_api_client import NEJMAPIClient
from config_manager import ConfigManager

def main():
    print("🔄 Ingesting 100 articles from NEJM journal...")
    
    # Get API credentials
    config = ConfigManager()
    api_key = config.get_api_key("qa")
    
    if not api_key:
        print("❌ No API key found. Run setup_wizard.py first.")
        sys.exit(1)
    
    # Initialize client
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    client = NEJMAPIClient(base_url)
    
    # Set up authentication
    if '|' in api_key:
        user_id, key = api_key.split('|', 1)
        client.session.headers.update({
            "apiuser": user_id,
            "apikey": key
        })
    else:
        print("❌ API key format should be: userid|apikey")
        sys.exit(1)
    
    print("📊 Getting current database stats...")
    
    # Check current database size
    import requests
    try:
        response = requests.get("http://127.0.0.1:6333/collections/articles_ollama")
        if response.status_code == 200:
            current_count = response.json()["result"]["points_count"]
            print(f"📚 Current database has {current_count:,} chunks")
        else:
            print("⚠️  Could not get current database stats")
            current_count = "unknown"
    except:
        print("⚠️  Could not connect to Qdrant database")
        current_count = "unknown"
    
    # Fetch articles in batches to get 100 total
    # We'll get 50 from page 1 and 50 from page 2
    all_articles = []
    
    for page in [1, 2]:  # Get first 100 articles
        print(f"\n📖 Fetching page {page} (articles {(page-1)*50+1}-{page*50})...")
        
        endpoint = f"{base_url}/api/v1/simple"
        params = {
            "context": "nejm",
            "objectType": "nejm-article",
            "sortBy": "pubdate-descending",
            "pageLength": 50,
            "startPage": page,
            "showFacets": "N"
        }
        
        try:
            response = client.session.get(endpoint, params=params)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('results', [])
                print(f"✅ Found {len(articles)} articles on page {page}")
                all_articles.extend(articles)
            else:
                print(f"❌ Failed to fetch page {page}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error fetching page {page}: {e}")
    
    if not all_articles:
        print("❌ No articles found to ingest")
        return
    
    print(f"\n🎯 Total articles to ingest: {len(all_articles)}")
    
    # Ingest articles
    successful = 0
    failed = 0
    
    for i, article in enumerate(all_articles, 1):
        metadata = client.extract_article_metadata(article)
        title = metadata.get('title', 'Unknown')[:60]
        
        print(f"\n📄 Processing {i}/{len(all_articles)}: {title}...")
        
        try:
            if client.ingest_article(article, "nejm"):
                successful += 1
                print(f"✅ Success ({successful}/{i})")
            else:
                failed += 1
                print(f"❌ Failed ({failed}/{i})")
                
        except Exception as e:
            failed += 1
            print(f"❌ Error ingesting article {i}: {e}")
    
    # Final stats
    print(f"\n" + "="*60)
    print(f"📊 INGESTION COMPLETE")
    print(f"="*60)
    print(f"✅ Successfully ingested: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success rate: {successful/(successful+failed)*100:.1f}%")
    
    # Check new database size
    try:
        response = requests.get("http://127.0.0.1:6333/collections/articles_ollama")
        if response.status_code == 200:
            new_count = response.json()["result"]["points_count"]
            added = new_count - current_count if isinstance(current_count, int) else "unknown"
            print(f"📚 Database now has {new_count:,} chunks (+{added} new)")
        else:
            print("⚠️  Could not get updated database stats")
    except:
        print("⚠️  Could not connect to Qdrant for final stats")
    
    print(f"\n🎉 100 NEJM articles have been ingested!")
    print(f"💡 You can now search them using:")
    print(f"   python ai_research_assistant.py \"your research question\"")

if __name__ == "__main__":
    main()