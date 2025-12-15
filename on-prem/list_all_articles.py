#!/usr/bin/env python3
"""
List all articles that have been ingested into the database
"""

import requests
import json
from collections import defaultdict

# Configuration
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"

def get_all_articles():
    """Get all unique articles from the database"""
    
    # First, get the total count
    response = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}")
    if response.status_code != 200:
        print("❌ Could not connect to Qdrant database")
        return
    
    total_points = response.json()["result"]["points_count"]
    print(f"📊 Total chunks in database: {total_points:,}")
    
    # Get all points with metadata
    print("🔍 Retrieving all articles...")
    
    # Use scroll to get all points
    all_articles = {}
    offset = None
    batch_size = 1000
    
    while True:
        scroll_payload = {
            "limit": batch_size,
            "with_payload": True,
            "with_vector": False
        }
        
        if offset:
            scroll_payload["offset"] = offset
        
        response = requests.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
            json=scroll_payload
        )
        
        if response.status_code != 200:
            print(f"❌ Error retrieving points: {response.status_code}")
            break
        
        data = response.json()
        points = data.get("result", {}).get("points", [])
        
        if not points:
            break
        
        # Process points
        for point in points:
            metadata = point.get("payload", {}).get("metadata", {})
            title = metadata.get("title", "Unknown Title")
            doi = metadata.get("doi")
            year = metadata.get("year")
            source = metadata.get("source", "unknown")
            
            # Create unique key for article
            article_key = f"{title}|{doi}|{year}"
            
            if article_key not in all_articles:
                all_articles[article_key] = {
                    "title": title,
                    "doi": doi,
                    "year": year,
                    "source": source,
                    "chunk_count": 0
                }
            
            all_articles[article_key]["chunk_count"] += 1
        
        # Check if we have more points
        offset = data.get("result", {}).get("next_page_offset")
        if not offset:
            break
        
        print(f"📖 Processed {len(all_articles)} unique articles so far...")
    
    return all_articles

def display_articles(articles):
    """Display articles organized by source"""
    
    # Group by source
    by_source = defaultdict(list)
    
    for article_data in articles.values():
        source = article_data["source"]
        by_source[source].append(article_data)
    
    # Sort each source by year (newest first) then by title
    for source in by_source:
        by_source[source].sort(key=lambda x: (-(x["year"] or 0), x["title"]))
    
    print(f"\n" + "="*80)
    print(f"📚 ALL INGESTED ARTICLES ({len(articles)} unique articles)")
    print(f"="*80)
    
    total_chunks = sum(article["chunk_count"] for article in articles.values())
    print(f"📊 Total chunks: {total_chunks:,}")
    print(f"📊 Unique articles: {len(articles):,}")
    print(f"📊 Average chunks per article: {total_chunks/len(articles):.1f}")
    
    # Display by source
    for source in sorted(by_source.keys()):
        articles_in_source = by_source[source]
        chunks_in_source = sum(a["chunk_count"] for a in articles_in_source)
        
        print(f"\n" + "="*60)
        print(f"📖 {source.upper()} ({len(articles_in_source)} articles, {chunks_in_source} chunks)")
        print(f"="*60)
        
        for i, article in enumerate(articles_in_source, 1):
            title = article["title"]
            year = article["year"] or "Unknown"
            doi = article["doi"] or "No DOI"
            chunks = article["chunk_count"]
            
            # Truncate very long titles
            if len(title) > 100:
                title = title[:97] + "..."
            
            print(f"{i:3d}. {title}")
            print(f"     Year: {year} | DOI: {doi} | Chunks: {chunks}")
            print()

def save_to_file(articles, filename="all_articles.txt"):
    """Save article list to a text file"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"ALL INGESTED ARTICLES ({len(articles)} unique articles)\n")
        f.write("="*80 + "\n\n")
        
        total_chunks = sum(article["chunk_count"] for article in articles.values())
        f.write(f"Total chunks: {total_chunks:,}\n")
        f.write(f"Unique articles: {len(articles):,}\n")
        f.write(f"Average chunks per article: {total_chunks/len(articles):.1f}\n\n")
        
        # Group by source
        by_source = defaultdict(list)
        for article_data in articles.values():
            source = article_data["source"]
            by_source[source].append(article_data)
        
        # Sort each source by year (newest first) then by title
        for source in by_source:
            by_source[source].sort(key=lambda x: (-(x["year"] or 0), x["title"]))
        
        # Write by source
        for source in sorted(by_source.keys()):
            articles_in_source = by_source[source]
            chunks_in_source = sum(a["chunk_count"] for a in articles_in_source)
            
            f.write("="*60 + "\n")
            f.write(f"{source.upper()} ({len(articles_in_source)} articles, {chunks_in_source} chunks)\n")
            f.write("="*60 + "\n\n")
            
            for i, article in enumerate(articles_in_source, 1):
                title = article["title"]
                year = article["year"] or "Unknown"
                doi = article["doi"] or "No DOI"
                chunks = article["chunk_count"]
                
                f.write(f"{i:3d}. {title}\n")
                f.write(f"     Year: {year} | DOI: {doi} | Chunks: {chunks}\n\n")

def main():
    print("📚 Retrieving all ingested articles from database...")
    
    try:
        articles = get_all_articles()
        
        if not articles:
            print("❌ No articles found in database")
            return
        
        # Display articles
        display_articles(articles)
        
        # Save to file
        filename = "all_ingested_articles.txt"
        save_to_file(articles, filename)
        print(f"\n💾 Complete list saved to: {filename}")
        
        # Summary by source
        by_source = defaultdict(int)
        for article in articles.values():
            by_source[article["source"]] += 1
        
        print(f"\n📊 SUMMARY BY SOURCE:")
        for source, count in sorted(by_source.items()):
            print(f"   {source}: {count} articles")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()