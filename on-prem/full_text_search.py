#!/usr/bin/env python3
"""
Full Text Semantic Search - Returns complete article content
Usage: python full_text_search.py "your question here"
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

def get_all_chunks_for_article(article_key: str, metadata: Dict) -> List[Dict]:
    """Get all chunks for a specific article to reconstruct full text"""
    # Search for all chunks with the same title and DOI
    title = metadata.get("title", "")
    doi = metadata.get("doi", "")
    
    # Build filter conditions
    filter_conditions = []
    
    if doi:
        filter_conditions.append({
            "key": "metadata.doi",
            "match": {"value": doi}
        })
    
    if title and not doi:
        filter_conditions.append({
            "key": "metadata.title", 
            "match": {"value": title}
        })
    
    if not filter_conditions:
        return []
    
    # Search with filter
    search_payload = {
        "filter": {
            "must": filter_conditions
        },
        "limit": 1000,  # Get all chunks
        "with_payload": True
    }
    
    try:
        response = requests.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
            json=search_payload
        )
        response.raise_for_status()
        
        results = response.json().get("result", {}).get("points", [])
        
        # Sort chunks by chunk number if available
        def get_chunk_number(chunk_id):
            try:
                if "chunk_" in chunk_id:
                    return int(chunk_id.split("_")[1])
                return 0
            except:
                return 0
        
        sorted_chunks = sorted(results, key=lambda x: get_chunk_number(
            x.get("payload", {}).get("metadata", {}).get("chunk", "chunk_0")
        ))
        
        return sorted_chunks
        
    except Exception as e:
        print(f"Error getting full article chunks: {e}")
        return []

def search_and_get_full_text(query: str) -> Dict:
    """Search for most relevant article and return its full text"""
    print(f"🔍 Searching for: '{query}'")
    
    # Get embedding
    query_embedding = get_embedding(query)
    
    # Search Qdrant for most relevant chunk
    search_payload = {
        "vector": query_embedding,
        "limit": 1,  # Just get the top result
        "with_payload": True,
        "score_threshold": 0.3
    }
    
    response = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        json=search_payload
    )
    response.raise_for_status()
    
    results = response.json().get("result", [])
    
    if not results:
        return None
    
    # Get the top result
    top_result = results[0]
    metadata = top_result.get("payload", {}).get("metadata", {})
    
    print(f"📄 Most relevant article found (relevance: {top_result['score']:.1%})")
    print(f"Title: {metadata.get('title', 'Unknown')}")
    
    # Get all chunks for this article
    print("📚 Reconstructing full article text...")
    all_chunks = get_all_chunks_for_article(
        metadata.get('doi') or metadata.get('title'), 
        metadata
    )
    
    if not all_chunks:
        # Fallback to just the single chunk
        return {
            "metadata": metadata,
            "score": top_result["score"],
            "full_text": top_result.get("payload", {}).get("document", ""),
            "chunk_count": 1
        }
    
    # Combine all chunks into full text
    full_text_parts = []
    for chunk in all_chunks:
        chunk_text = chunk.get("payload", {}).get("document", "")
        if chunk_text:
            full_text_parts.append(chunk_text)
    
    full_text = "\n\n".join(full_text_parts)
    
    return {
        "metadata": metadata,
        "score": top_result["score"],
        "full_text": full_text,
        "chunk_count": len(all_chunks)
    }

def format_full_article(article_data: Dict) -> str:
    """Format the complete article for display"""
    if not article_data:
        return "❌ No article found matching your query."
    
    metadata = article_data["metadata"]
    
    output = []
    output.append("=" * 80)
    output.append("📄 FULL ARTICLE TEXT")
    output.append("=" * 80)
    output.append(f"Title: {metadata.get('title', 'Unknown')}")
    
    if metadata.get('doi'):
        output.append(f"DOI: {metadata['doi']}")
    if metadata.get('year'):
        output.append(f"Year: {metadata['year']}")
    
    output.append(f"Source: {metadata.get('source', 'unknown')}")
    output.append(f"Relevance Score: {article_data['score']:.1%}")
    output.append(f"Reconstructed from: {article_data['chunk_count']} chunks")
    output.append("")
    output.append("=" * 80)
    output.append("CONTENT:")
    output.append("=" * 80)
    output.append("")
    output.append(article_data["full_text"])
    output.append("")
    output.append("=" * 80)
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Get full text of most relevant article")
    parser.add_argument("query", help="Your search question")
    parser.add_argument("--save", "-s", help="Save full text to file")
    parser.add_argument("--summary", action="store_true", help="Show only metadata, not full text")
    parser.add_argument("--pdf", action="store_true", help="Try to download PDF instead of showing text")
    
    args = parser.parse_args()
    
    try:
        article_data = search_and_get_full_text(args.query)
        
        if not article_data:
            print("❌ No articles found matching your query.")
            return
        
        metadata = article_data["metadata"]
        
        # PDF download option
        if args.pdf and metadata.get('doi'):
            print(f"\n📄 Found relevant article:")
            print(f"Title: {metadata.get('title', 'Unknown')[:80]}{'...' if len(metadata.get('title', '')) > 80 else ''}")
            print(f"DOI: {metadata['doi']}")
            print(f"Relevance: {article_data['score']:.1%}")
            
            try:
                from pdf_retriever import PDFRetriever
                retriever = PDFRetriever()
                
                safe_doi = metadata['doi'].replace('/', '_').replace('.', '_')
                pdf_path = f"article_{safe_doi}.pdf"
                
                result = retriever.download_pdf(metadata['doi'], pdf_path)
                if result:
                    print(f"\n🎉 PDF downloaded successfully: {result}")
                    return
                else:
                    print(f"\n⚠️  PDF download failed, showing text instead...")
                    
            except ImportError:
                print(f"\n⚠️  PDF retriever not available, showing text instead...")
        
        if args.summary:
            # Show only metadata
            print(f"\n📄 Article Summary:")
            print(f"Title: {metadata.get('title', 'Unknown')}")
            if metadata.get('doi'):
                print(f"DOI: {metadata['doi']}")
            if metadata.get('year'):
                print(f"Year: {metadata['year']}")
            print(f"Source: {metadata.get('source', 'unknown')}")
            print(f"Relevance: {article_data['score']:.1%}")
            print(f"Text length: {len(article_data['full_text']):,} characters")
            print(f"Chunks: {article_data['chunk_count']}")
            
            # Offer PDF download
            if metadata.get('doi'):
                print(f"\n💡 To download clean PDF instead of text:")
                print(f"   python pdf_retriever.py --doi {metadata['doi']}")
        else:
            # Show full article
            formatted_article = format_full_article(article_data)
            print(formatted_article)
            
            # Offer PDF download
            if metadata.get('doi'):
                print(f"\n💡 To download clean PDF instead of messy text:")
                print(f"   python pdf_retriever.py --doi {metadata['doi']}")
        
        # Save to file if requested
        if args.save:
            with open(args.save, 'w', encoding='utf-8') as f:
                f.write(format_full_article(article_data))
            print(f"\n💾 Full article saved to: {args.save}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()