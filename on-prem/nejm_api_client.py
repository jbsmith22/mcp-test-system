#!/usr/bin/env python3
"""
NEJM API Client for fetching and ingesting articles into Qdrant
"""

import requests
import json
import subprocess
import tempfile
import os
from typing import List, Dict, Optional
from datetime import datetime
import argparse
from config_manager import ConfigManager


class NEJMAPIClient:
    def __init__(self, base_url: str = "https://onesearch-api.nejmgroup-qa.org"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def get_recent_articles(self, limit: int = 10, context: str = "nejm") -> List[Dict]:
        """
        Fetch recent articles from NEJM API using the correct search endpoint
        """
        endpoint = f"{self.base_url}/api/v1/simple"
        
        params = {
            "context": context,
            "objectType": f"{context}-article",  # nejm-article, catalyst-article, etc.
            "sortBy": "pubdate-descending",  # Most recent first
            "pageLength": min(limit, 100),  # API max is 100
            "startPage": 1,
            "showFacets": "N"
        }
        
        try:
            print(f"Fetching recent articles from {endpoint}")
            print(f"Parameters: {params}")
            
            response = self.session.get(endpoint, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"✅ Found {len(results)} articles")
                return results
            else:
                print(f"❌ Status {response.status_code}: {response.text[:500]}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching articles: {e}")
            return []
    
    def get_article_content(self, doi: str, context: str = "nejm") -> Optional[Dict]:
        """
        Get full article content using the /content endpoint
        """
        endpoint = f"{self.base_url}/api/v1/content"
        
        params = {
            "context": context,
            "doi": doi,
            "format": "json"  # Get JSON format with full content
        }
        
        try:
            print(f"Fetching article content for DOI: {doi}")
            response = self.session.get(endpoint, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get article {doi}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching article {doi}: {e}")
            return None
    

    
    def extract_article_metadata(self, article: Dict) -> Dict:
        """Extract standardized metadata from NEJM API response"""
        metadata = {}
        
        # Based on the API spec, articles have these fields:
        if 'text' in article:  # This is the title field
            metadata['title'] = article['text']
        
        if 'doi' in article:
            metadata['doi'] = article['doi']
            
        if 'pubdate' in article:
            metadata['date'] = article['pubdate']
            # Extract year from pubdate
            try:
                if article['pubdate']:
                    # Try to parse year from various date formats
                    date_str = str(article['pubdate'])
                    if len(date_str) >= 4 and date_str[:4].isdigit():
                        metadata['year'] = int(date_str[:4])
            except (ValueError, TypeError):
                pass
        
        # Additional fields from the API
        if 'displayAbstract' in article:
            metadata['abstract'] = article['displayAbstract']
            
        if 'publication' in article:
            metadata['publication'] = article['publication']
            
        if 'volume' in article:
            metadata['volume'] = article['volume']
            
        if 'issue' in article:
            metadata['issue'] = article['issue']
        
        return metadata
    
    def ingest_article(self, article: Dict, context: str = "nejm", ingest_script_path: str = "nejm_text_ingest.py") -> bool:
        """
        Get full article content and ingest into Qdrant using existing script
        """
        try:
            # Extract metadata from search result
            metadata = self.extract_article_metadata(article)
            
            if not metadata.get('doi'):
                print(f"❌ No DOI found for article: {metadata.get('title', 'Unknown')}")
                return False
            
            # Use available content from search results
            content_parts = []
            
            # Add title
            if metadata.get('title'):
                content_parts.append(f"Title: {metadata['title']}")
            
            # Add abstract if available
            if metadata.get('abstract'):
                content_parts.append(f"Abstract: {metadata['abstract']}")
            
            # Add any text content from the search result
            if 'text' in article and article['text']:
                content_parts.append(f"Content: {article['text']}")
            
            # Add snippet if available
            if 'snippet' in article and article['snippet']:
                content_parts.append(f"Snippet: {article['snippet']}")
            
            # Try to get full content from API as additional source
            try:
                article_content = self.get_article_content(metadata['doi'], context)
                if article_content and 'document' in article_content:
                    # Try to extract additional content
                    doc_text = self._extract_text_from_document(article_content.get('document', {}))
                    if doc_text.strip():
                        content_parts.append(f"Full Content: {doc_text}")
            except Exception as e:
                print(f"Note: Could not fetch full content, using search result content: {e}")
            
            content_text = '\n\n'.join(content_parts)
            
            if not content_text.strip():
                print(f"❌ No text content available for: {metadata.get('title')}")
                return False
            
            # Create temporary text file
            filename = f"nejm_article_{metadata['doi'].replace('/', '_').replace('.', '_')}.txt"
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content_text)
            
            # Build ingest command for text-based ingestion
            cmd = [
                "python", ingest_script_path,
                "--text-file", temp_path,
                "--title", metadata.get('title', 'Unknown Title'),
                "--source", f"nejm-api-{context}"
            ]
            
            if metadata.get('doi'):
                cmd.extend(["--doi", metadata['doi']])
            if metadata.get('year'):
                cmd.extend(["--year", str(metadata['year'])])
            
            # Run ingestion
            print(f"Ingesting: {metadata.get('title', 'Unknown')}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Successfully ingested: {metadata.get('title')}")
                # Clean up temp file
                os.unlink(temp_path)
                return True
            else:
                print(f"❌ Ingestion failed: {result.stderr}")
                print(f"Command output: {result.stdout}")
                return False
                
        except Exception as e:
            print(f"❌ Error ingesting article: {e}")
            return False
    
    def _extract_text_from_document(self, doc_data: Dict) -> str:
        """
        Extract readable text from document structure
        This is a basic implementation - may need refinement based on actual XML structure
        """
        text_parts = []
        
        def extract_text_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ['text', 'content', 'body', 'abstract', 'title']:
                        if isinstance(value, str):
                            text_parts.append(value)
                    extract_text_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text_recursive(item)
            elif isinstance(obj, str) and len(obj) > 20:  # Only include substantial text
                text_parts.append(obj)
        
        extract_text_recursive(doc_data)
        return '\n\n'.join(text_parts)


def main():
    parser = argparse.ArgumentParser(description="Fetch and ingest NEJM articles")
    parser.add_argument("--limit", type=int, default=10, help="Number of articles to fetch")
    parser.add_argument("--context", default="nejm", choices=["nejm", "catalyst", "clinician", "evidence", "nejm-ai"], 
                       help="Journal context to search")
    parser.add_argument("--environment", default="qa", choices=["qa", "production"], 
                       help="API environment to use (default: qa)")
    parser.add_argument("--dry-run", action="store_true", help="Show articles without ingesting")
    parser.add_argument("--api-key", help="API key if required")
    
    args = parser.parse_args()
    
    # Set base URL based on environment
    if args.environment == "production":
        base_url = "https://onesearch-api.nejmgroup-production.org"
    else:
        base_url = "https://onesearch-api.nejmgroup-qa.org"
    
    # Initialize client
    client = NEJMAPIClient(base_url)
    
    # Get API key from multiple sources
    config = ConfigManager()
    api_key = args.api_key or config.get_api_key(args.environment)
    
    if not api_key:
        print(f"❌ No API key found for {args.environment} environment")
        print("Options:")
        print(f"1. Use --api-key flag: python nejm_api_client.py --api-key 'your-key'")
        print(f"2. Set environment variable: export NEJM_API_KEY='your-key'")
        print(f"3. Save to config: python config_manager.py --set-key 'your-key' --environment {args.environment}")
        return
    
    # NEJM API uses two headers: apiuser and apikey
    if '|' in api_key:
        # Format: "userid|apikey"
        user_id, key = api_key.split('|', 1)
        client.session.headers.update({
            "apiuser": user_id,
            "apikey": key
        })
    else:
        # Assume it's just the key, prompt for user ID
        print("❌ API key format should be: userid|apikey")
        print("Example: python nejm_api_client.py --api-key 'your-userid|your-apikey'")
        return
    
    print(f"Fetching {args.limit} recent articles from {args.context.upper()} via NEJM API ({args.environment})...")
    
    # Fetch articles
    articles = client.get_recent_articles(args.limit, args.context)
    
    if not articles:
        print("No articles found. Check API endpoint and authentication.")
        return
    
    print(f"Found {len(articles)} articles")
    
    # Process articles
    success_count = 0
    for i, article in enumerate(articles, 1):
        metadata = client.extract_article_metadata(article)
        print(f"\n{i}. {metadata.get('title', 'Unknown Title')}")
        print(f"   DOI: {metadata.get('doi', 'N/A')}")
        print(f"   Year: {metadata.get('year', 'N/A')}")
        print(f"   Publication: {metadata.get('publication', 'N/A')}")
        
        if args.dry_run:
            print(f"   ✅ Ready for ingestion")
        else:
            if client.ingest_article(article, args.context):
                success_count += 1
    
    if not args.dry_run:
        print(f"\n✅ Successfully ingested {success_count}/{len(articles)} articles")


if __name__ == "__main__":
    main()