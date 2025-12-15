#!/usr/bin/env python3
"""
Clean Article Retriever - Gets clean, formatted article content
Uses JATS XML from NEJM API to provide clean text instead of messy chunks
"""

import requests
import json
import sys
import argparse
import re
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET
from config_manager import ConfigManager

# Configuration
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"

class CleanArticleRetriever:
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
            self.base_url = "https://onesearch-api.nejmgroup-qa.org"
        else:
            self.api_headers = None
            print("❌ No API credentials found")
            sys.exit(1)
    
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
    
    def get_clean_article_content(self, doi: str, context: str) -> Optional[Dict]:
        """Get clean article content using JATS XML format"""
        endpoint = f"{self.base_url}/api/v1/content"
        
        params = {
            "context": context,
            "doi": doi,
            "format": "jats"  # Get clean JATS XML
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=self.api_headers)
            
            if response.status_code == 200:
                return {
                    "xml_content": response.text,
                    "content_type": response.headers.get("content-type", "")
                }
            else:
                print(f"❌ API returned status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching article: {e}")
            return None
    
    def parse_jats_xml(self, xml_content: str) -> Dict:
        """Parse JATS XML and extract clean, structured content using regex"""
        try:
            article_data = {
                "title": "",
                "authors": [],
                "abstract": "",
                "content": "",
                "sections": []
            }
            
            # Extract title using regex
            title_match = re.search(r'<article-title[^>]*>(.*?)</article-title>', xml_content, re.DOTALL)
            if title_match:
                article_data["title"] = self.clean_html_tags(title_match.group(1))
            
            # Extract authors
            author_matches = re.findall(r'<string-name[^>]*>(.*?)</string-name>', xml_content, re.DOTALL)
            for author_match in author_matches:
                clean_author = self.clean_html_tags(author_match)
                if clean_author and clean_author not in article_data["authors"]:
                    article_data["authors"].append(clean_author)
            
            # Extract abstract
            abstract_match = re.search(r'<abstract[^>]*>(.*?)</abstract>', xml_content, re.DOTALL)
            if abstract_match:
                article_data["abstract"] = self.clean_html_tags(abstract_match.group(1))
            
            # Extract main content sections
            section_matches = re.findall(r'<sec[^>]*>(.*?)</sec>', xml_content, re.DOTALL)
            for section_content in section_matches:
                # Extract section title
                title_match = re.search(r'<title[^>]*>(.*?)</title>', section_content, re.DOTALL)
                section_title = self.clean_html_tags(title_match.group(1)) if title_match else "Section"
                
                # Extract paragraphs
                paragraph_matches = re.findall(r'<p[^>]*>(.*?)</p>', section_content, re.DOTALL)
                paragraphs = []
                for para in paragraph_matches:
                    clean_para = self.clean_html_tags(para)
                    if clean_para and len(clean_para) > 20:  # Only substantial paragraphs
                        paragraphs.append(clean_para)
                
                if paragraphs:
                    article_data["sections"].append({
                        "title": section_title,
                        "content": paragraphs
                    })
            
            # Create a combined content string
            content_parts = []
            if article_data["abstract"]:
                content_parts.append(f"ABSTRACT\n{article_data['abstract']}")
            
            for section in article_data["sections"]:
                content_parts.append(f"\n{section['title'].upper()}")
                content_parts.extend(section['content'])
            
            article_data["content"] = "\n\n".join(content_parts)
            
            return article_data
            
        except Exception as e:
            print(f"❌ Error parsing XML: {e}")
            return None
    
    def clean_html_tags(self, text: str) -> str:
        """Remove HTML/XML tags and clean up text"""
        if not text:
            return ""
        
        # Remove XML/HTML tags
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text)
        clean_text = clean_text.strip()
        
        # Decode common HTML entities
        clean_text = clean_text.replace('&lt;', '<')
        clean_text = clean_text.replace('&gt;', '>')
        clean_text = clean_text.replace('&amp;', '&')
        clean_text = clean_text.replace('&quot;', '"')
        clean_text = clean_text.replace('&#x27;', "'")
        
        return clean_text
    
    def clean_text(self, element) -> str:
        """Extract clean text from XML element, removing tags but preserving content"""
        if element is None:
            return ""
        
        # Get all text content, including from child elements
        text_parts = []
        
        def extract_text(elem):
            if elem.text:
                text_parts.append(elem.text)
            for child in elem:
                extract_text(child)
                if child.tail:
                    text_parts.append(child.tail)
        
        extract_text(element)
        
        # Join and clean up
        text = ''.join(text_parts)
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        
        return text
    
    def format_clean_article(self, article_data: Dict, metadata: Dict) -> str:
        """Format the clean article data for display"""
        output = []
        output.append("=" * 80)
        output.append("📄 CLEAN ARTICLE CONTENT")
        output.append("=" * 80)
        
        # Metadata
        output.append(f"Title: {article_data.get('title', metadata.get('title', 'Unknown'))}")
        if metadata.get('doi'):
            output.append(f"DOI: {metadata['doi']}")
        if metadata.get('year'):
            output.append(f"Year: {metadata['year']}")
        output.append(f"Source: {metadata.get('source', 'unknown')}")
        output.append(f"Relevance Score: {metadata.get('score', 0):.1%}")
        
        # Authors
        if article_data.get('authors'):
            output.append(f"Authors: {', '.join(article_data['authors'])}")
        
        output.append("")
        output.append("=" * 80)
        
        # Abstract
        if article_data.get('abstract'):
            output.append("ABSTRACT")
            output.append("-" * 40)
            output.append(article_data['abstract'])
            output.append("")
        
        # Main content sections
        for section in article_data.get('sections', []):
            output.append(f"{section['title'].upper()}")
            output.append("-" * 40)
            
            for paragraph in section['content']:
                output.append(paragraph)
                output.append("")
        
        output.append("=" * 80)
        
        return "\n".join(output)
    
    def search_and_get_clean_article(self, query: str) -> Optional[str]:
        """Search for most relevant article and return clean formatted content"""
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
            print("❌ Article has no DOI - cannot retrieve clean content")
            return None
        
        # Determine context from source
        source = article['source'].lower()
        if 'nejm-ai' in source:
            context = 'nejm-ai'
        elif 'catalyst' in source:
            context = 'catalyst'
        elif 'evidence' in source:
            context = 'evidence'
        elif 'clinician' in source:
            context = 'clinician'
        else:
            context = 'nejm'
        
        print(f"📚 Retrieving clean content from {context} context...")
        
        # Get clean content
        content_data = self.get_clean_article_content(article['doi'], context)
        
        if not content_data:
            print("❌ Could not retrieve article content")
            return None
        
        print("🧹 Parsing and cleaning article content...")
        
        # Parse XML content
        parsed_article = self.parse_jats_xml(content_data['xml_content'])
        
        if not parsed_article:
            print("❌ Could not parse article content")
            return None
        
        # Format for display
        article['score'] = article['score']  # Add score to metadata
        formatted_content = self.format_clean_article(parsed_article, article)
        
        return formatted_content

def main():
    parser = argparse.ArgumentParser(description="Get clean, formatted article content")
    parser.add_argument("query", nargs='?', help="Search query")
    parser.add_argument("--save", "-s", help="Save to file")
    
    args = parser.parse_args()
    
    retriever = CleanArticleRetriever()
    
    try:
        query = args.query
        if not query:
            query = input("🤔 Enter your search query: ").strip()
            if not query:
                print("❌ No query provided")
                return
        
        # Get clean article
        clean_content = retriever.search_and_get_clean_article(query)
        
        if clean_content:
            print("\n" + clean_content)
            
            # Save if requested
            if args.save:
                with open(args.save, 'w', encoding='utf-8') as f:
                    f.write(clean_content)
                print(f"\n💾 Clean article saved to: {args.save}")
            
            print(f"\n✨ Much cleaner than the messy chunked text!")
        else:
            print("❌ Could not retrieve clean article content")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()