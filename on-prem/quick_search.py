#!/usr/bin/env python3
"""
Quick Semantic Search - Single query command line tool
Usage: python quick_search.py "your question here"
"""

import requests
import json
import sys
import argparse
from typing import List, Dict

# Configuration
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"

def get_embedding(text: str) -> List[float]:
    """Get embedding vector for text"""
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text}
    )
    response.raise_for_status()
    return response.json()["embedding"]

def search_articles(query: str, limit: int = 5) -> List[Dict]:
    """Search for articles and group by unique articles"""
    # Get embedding
    query_embedding = get_embedding(query)
    
    # Search Qdrant
    search_payload = {
        "vector": query_embedding,
        "limit": limit * 5,  # Get more to group by article
        "with_payload": True,
        "score_threshold": 0.5
    }
    
    response = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        json=search_payload
    )
    response.raise_for_status()
    
    results = response.json().get("result", [])
    
    # Group by article (using DOI or title as key)
    articles = {}
    for result in results:
        metadata = result.get("payload", {}).get("metadata", {})
        title = metadata.get("title", "Unknown")
        doi = metadata.get("doi", "")
        
        article_key = doi if doi else title
        
        if article_key not in articles or result["score"] > articles[article_key]["score"]:
            articles[article_key] = {
                "score": result["score"],
                "title": title,
                "doi": doi,
                "year": metadata.get("year"),
                "source": metadata.get("source", "unknown"),
                "chunk_text": result.get("payload", {}).get("document", "")[:200]
            }
    
    # Return top articles sorted by score
    return sorted(articles.values(), key=lambda x: x["score"], reverse=True)[:limit]

def main():
    parser = argparse.ArgumentParser(description="Quick semantic search of medical literature")
    parser.add_argument("query", help="Your search question")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Number of articles to return")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed results")
    
    args = parser.parse_args()
    
    print(f"🔍 Searching for: '{args.query}'")
    
    try:
        articles = search_articles(args.query, args.limit)
        
        if not articles:
            print("❌ No articles found matching your query.")
            return
        
        print(f"\n📚 Top {len(articles)} results:")
        print("=" * 50)
        
        for i, article in enumerate(articles, 1):
            score_pct = article["score"] * 100
            print(f"\n{i}. {article['title'][:80]}{'...' if len(article['title']) > 80 else ''}")
            print(f"   🎯 Relevance: {score_pct:.1f}%")
            
            if article.get('doi'):
                print(f"   🔗 DOI: {article['doi']}")
            if article.get('year'):
                print(f"   📅 Year: {article['year']}")
            print(f"   📊 Source: {article['source']}")
            
            if args.verbose:
                print(f"   📝 Preview: {article['chunk_text']}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()