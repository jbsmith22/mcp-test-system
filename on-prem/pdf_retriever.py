#!/usr/bin/env python3
"""
PDF Retriever for NEJM Articles
Downloads clean PDFs instead of messy text from semantic search results
"""

import requests
import json
import sys
import argparse
import os
from typing import List, Dict, Optional
from urllib.parse import quote
from config_manager import ConfigManager

# Configuration
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"

class PDFRetriever:
    def __init__(self):
        self.qdrant_url = QDRANT_URL
        self.ollama_url = OLLAMA_URL
        self.collection = COLLECTION
        
        # Get API credentials
        config = ConfigManager()
        credentials = config.get_api_key("qa")
        
        if credentials and '|' in credentials:
            user_id, key = credentials.split('|', 1)
            self.api_headers = {
                "apiuser": user_id,
                "apikey": key
            }
        else:
            self.api_headers = None
            print("⚠️  No API credentials found. PDF downloads may not work.")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text"""
        response = requests.post(
            f"{self.ollama_url}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text}
        )
        response.raise_for_status()
        return response.json()["embedding"]
    
    def search_for_best_article(self, query: str) -> Optional[Dict]:
        """Find the most relevant article for the query"""
        print(f"🔍 Searching for: '{query}'")
        
        # Get embedding
        query_embedding = self.get_embedding(query)
        
        # Search Qdrant
        search_payload = {
            "vector": query_embedding,
            "limit": 1,
            "with_payload": True,
            "score_threshold": 0.3
        }
        
        response = requests.post(
            f"{self.qdrant_url}/collections/{self.collection}/points/search",
            json=search_payload
        )
        response.raise_for_status()
        
        results = response.json().get("result", [])
        
        if not results:
            return None
        
        # Get the top result
        top_result = results[0]
        metadata = top_result.get("payload", {}).get("metadata", {})
        
        return {
            "score": top_result["score"],
            "title": metadata.get("title", "Unknown"),
            "doi": metadata.get("doi"),
            "year": metadata.get("year"),
            "source": metadata.get("source", "unknown")
        }
    
    def construct_pdf_urls(self, doi: str) -> List[str]:
        """Construct possible PDF URLs for a DOI"""
        if not doi:
            return []
        
        # Clean DOI
        clean_doi = doi.replace("10.1056/", "")
        
        # Common NEJM PDF URL patterns
        base_urls = [
            "https://www.nejm.org/doi/pdf/",
            "https://ai.nejm.org/doi/pdf/", 
            "https://catalyst.nejm.org/doi/pdf/",
            "https://evidence.nejm.org/doi/pdf/"
        ]
        
        pdf_urls = []
        for base_url in base_urls:
            pdf_urls.append(f"{base_url}{doi}")
            pdf_urls.append(f"{base_url}{clean_doi}")
        
        return pdf_urls
    
    def download_pdf(self, doi: str, output_path: str = None) -> Optional[str]:
        """Download PDF for a given DOI"""
        if not doi:
            print("❌ No DOI provided")
            return None
        
        print(f"📄 Attempting to download PDF for DOI: {doi}")
        
        # Try different PDF URL patterns
        pdf_urls = self.construct_pdf_urls(doi)
        
        for i, pdf_url in enumerate(pdf_urls, 1):
            print(f"🔗 Trying URL {i}/{len(pdf_urls)}: {pdf_url}")
            
            try:
                # Try with API credentials first
                headers = {}
                if self.api_headers:
                    headers.update(self.api_headers)
                
                response = requests.get(pdf_url, headers=headers, timeout=30)
                
                # Check if we got a PDF
                content_type = response.headers.get('content-type', '').lower()
                
                if response.status_code == 200 and 'pdf' in content_type:
                    # Success! Save the PDF
                    if not output_path:
                        safe_doi = doi.replace('/', '_').replace('.', '_')
                        output_path = f"article_{safe_doi}.pdf"
                    
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = len(response.content)
                    print(f"✅ PDF downloaded successfully!")
                    print(f"📁 Saved to: {output_path}")
                    print(f"📊 File size: {file_size:,} bytes")
                    
                    return output_path
                
                elif response.status_code == 200:
                    # Got a response but not PDF - might be HTML login page
                    print(f"⚠️  Got {content_type} instead of PDF")
                    
                else:
                    print(f"❌ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("❌ Could not download PDF from any URL")
        return None
    
    def search_and_download_pdf(self, query: str, output_path: str = None) -> Optional[str]:
        """Search for most relevant article and download its PDF"""
        # Find best matching article
        article = self.search_for_best_article(query)
        
        if not article:
            print("❌ No articles found matching your query")
            return None
        
        print(f"📄 Most relevant article (relevance: {article['score']:.1%}):")
        print(f"   Title: {article['title'][:80]}{'...' if len(article['title']) > 80 else ''}")
        print(f"   DOI: {article['doi']}")
        print(f"   Year: {article['year']}")
        print(f"   Source: {article['source']}")
        
        if not article['doi']:
            print("❌ Article has no DOI - cannot download PDF")
            return None
        
        # Download PDF
        return self.download_pdf(article['doi'], output_path)
    
    def download_pdf_by_doi(self, doi: str, output_path: str = None) -> Optional[str]:
        """Download PDF directly by DOI"""
        return self.download_pdf(doi, output_path)

def main():
    parser = argparse.ArgumentParser(description="Download PDFs of relevant medical articles")
    parser.add_argument("query", nargs='?', help="Search query (if not provided, will prompt)")
    parser.add_argument("--doi", help="Download specific DOI instead of searching")
    parser.add_argument("--output", "-o", help="Output filename")
    parser.add_argument("--directory", "-d", help="Output directory", default=".")
    
    args = parser.parse_args()
    
    retriever = PDFRetriever()
    
    try:
        if args.doi:
            # Download specific DOI
            output_path = args.output
            if not output_path:
                safe_doi = args.doi.replace('/', '_').replace('.', '_')
                output_path = f"article_{safe_doi}.pdf"
            
            if args.directory != ".":
                os.makedirs(args.directory, exist_ok=True)
                output_path = os.path.join(args.directory, output_path)
            
            result = retriever.download_pdf_by_doi(args.doi, output_path)
            
        else:
            # Search and download
            query = args.query
            if not query:
                query = input("🤔 Enter your search query: ").strip()
                if not query:
                    print("❌ No query provided")
                    return
            
            output_path = args.output
            if args.directory != "." and output_path:
                os.makedirs(args.directory, exist_ok=True)
                output_path = os.path.join(args.directory, output_path)
            
            result = retriever.search_and_download_pdf(query, output_path)
        
        if result:
            print(f"\n🎉 Success! PDF saved to: {result}")
            print(f"📖 You can now open the clean PDF instead of messy text!")
        else:
            print("\n❌ Failed to download PDF")
            print("💡 This might be due to:")
            print("   • Article requires subscription/login")
            print("   • PDF not available for this article")
            print("   • Network connectivity issues")
            print("   • Different URL pattern than expected")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()