#!/usr/bin/env python3
"""
Interactive Semantic Search for Medical Literature
Prompts for natural language questions and returns best matching articles
"""

import requests
import json
import sys
from typing import List, Dict, Any
from datetime import datetime

# Configuration - matches your existing setup
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"

class SemanticSearcher:
    def __init__(self):
        self.qdrant_url = QDRANT_URL
        self.ollama_url = OLLAMA_URL
        self.collection = COLLECTION
        self.embed_model = EMBED_MODEL
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using Ollama"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": self.embed_model,
                    "prompt": text
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            print(f"❌ Error getting embedding: {e}")
            return None
    
    def search_articles(self, query: str, limit: int = 10, score_threshold: float = 0.5) -> List[Dict]:
        """Search for articles using semantic similarity"""
        print(f"🔍 Searching for: '{query}'")
        print("⏳ Getting embedding...")
        
        # Get query embedding
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
        
        print("⏳ Searching database...")
        
        # Search Qdrant
        try:
            search_payload = {
                "vector": query_embedding,
                "limit": limit * 3,  # Get more results to filter and group
                "with_payload": True,
                "score_threshold": score_threshold
            }
            
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection}/points/search",
                json=search_payload,
                timeout=30
            )
            response.raise_for_status()
            
            results = response.json().get("result", [])
            print(f"✅ Found {len(results)} matching chunks")
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching database: {e}")
            return []
    
    def group_by_article(self, results: List[Dict]) -> List[Dict]:
        """Group chunks by article and keep the best scoring chunk per article"""
        articles = {}
        
        for result in results:
            metadata = result.get("payload", {}).get("metadata", {})
            title = metadata.get("title", "Unknown")
            doi = metadata.get("doi", "")
            
            # Use DOI as primary key, fallback to title
            article_key = doi if doi else title
            
            # Keep the highest scoring chunk for each article
            if article_key not in articles or result["score"] > articles[article_key]["score"]:
                articles[article_key] = {
                    "score": result["score"],
                    "title": title,
                    "doi": doi,
                    "year": metadata.get("year"),
                    "source": metadata.get("source", "unknown"),
                    "chunk_text": result.get("payload", {}).get("document", ""),
                    "chunk_id": metadata.get("chunk", "")
                }
        
        # Sort by score (highest first)
        return sorted(articles.values(), key=lambda x: x["score"], reverse=True)
    
    def format_results(self, articles: List[Dict], show_chunks: bool = False) -> str:
        """Format search results for display"""
        if not articles:
            return "❌ No articles found matching your query."
        
        output = []
        output.append(f"\n📚 Found {len(articles)} relevant articles:")
        output.append("=" * 60)
        
        for i, article in enumerate(articles, 1):
            score_bar = "█" * int(article["score"] * 20)  # Visual score bar
            score_pct = article["score"] * 100
            
            output.append(f"\n{i}. 📄 {article['title'][:100]}{'...' if len(article['title']) > 100 else ''}")
            output.append(f"   🎯 Relevance: {score_bar} {score_pct:.1f}%")
            
            if article.get('doi'):
                output.append(f"   🔗 DOI: {article['doi']}")
            
            if article.get('year'):
                output.append(f"   📅 Year: {article['year']}")
            
            output.append(f"   📊 Source: {article['source']}")
            
            if show_chunks and article.get('chunk_text'):
                chunk_preview = article['chunk_text'][:200].replace('\n', ' ')
                output.append(f"   📝 Preview: {chunk_preview}...")
                output.append(f"   📍 Chunk: {article.get('chunk_id', 'N/A')}")
            
            output.append("")
        
        return "\n".join(output)
    
    def interactive_search(self):
        """Interactive search loop"""
        print("🔬 Medical Literature Semantic Search")
        print("=" * 50)
        print("Ask natural language questions about medical research!")
        print("Examples:")
        print("  • 'AI scribes for clinical documentation'")
        print("  • 'machine learning in cardiology'") 
        print("  • 'artificial intelligence diagnostic accuracy'")
        print("  • 'clinical decision support systems'")
        print("\nType 'quit' or 'exit' to stop, 'help' for options")
        print("-" * 50)
        
        while True:
            try:
                # Get user query
                query = input("\n🤔 Your question: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if query.lower() in ['help', 'h']:
                    self.show_help()
                    continue
                
                if query.lower().startswith('settings'):
                    self.show_settings()
                    continue
                
                # Parse any options from query
                show_chunks = '--chunks' in query or '-c' in query
                limit = 10
                threshold = 0.5
                
                # Extract limit if specified
                if '--limit' in query:
                    try:
                        parts = query.split('--limit')
                        limit_part = parts[1].strip().split()[0]
                        limit = int(limit_part)
                        query = parts[0].strip()
                    except:
                        pass
                
                # Extract threshold if specified  
                if '--threshold' in query:
                    try:
                        parts = query.split('--threshold')
                        threshold_part = parts[1].strip().split()[0]
                        threshold = float(threshold_part)
                        query = parts[0].strip()
                    except:
                        pass
                
                # Clean query of options
                query = query.replace('--chunks', '').replace('-c', '').strip()
                
                # Perform search
                start_time = datetime.now()
                results = self.search_articles(query, limit=limit, score_threshold=threshold)
                
                if results:
                    # Group by article
                    articles = self.group_by_article(results)
                    
                    # Limit final results
                    articles = articles[:limit]
                    
                    # Display results
                    formatted_results = self.format_results(articles, show_chunks=show_chunks)
                    print(formatted_results)
                    
                    # Show timing
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"⏱️  Search completed in {elapsed:.2f} seconds")
                    
                    # Ask for follow-up
                    follow_up = input("\n💡 Options: [number] for details, [number]f for full text, or Enter to continue: ").strip()
                    if follow_up.isdigit():
                        idx = int(follow_up) - 1
                        if 0 <= idx < len(articles):
                            self.show_article_details(articles[idx])
                    elif follow_up.endswith('f') and follow_up[:-1].isdigit():
                        idx = int(follow_up[:-1]) - 1
                        if 0 <= idx < len(articles):
                            self.show_full_article_text(articles[idx])
                
                else:
                    print("❌ No articles found. Try rephrasing your question or lowering the threshold.")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def show_article_details(self, article: Dict):
        """Show detailed information about a specific article"""
        print("\n" + "=" * 60)
        print("📄 ARTICLE DETAILS")
        print("=" * 60)
        print(f"Title: {article['title']}")
        if article.get('doi'):
            print(f"DOI: {article['doi']}")
        if article.get('year'):
            print(f"Year: {article['year']}")
        print(f"Source: {article['source']}")
        print(f"Relevance Score: {article['score']:.3f}")
        print(f"Chunk: {article.get('chunk_id', 'N/A')}")
        print("\nContent Preview:")
        print("-" * 40)
        print(article.get('chunk_text', 'No content available')[:500])
        if len(article.get('chunk_text', '')) > 500:
            print("...")
        print("-" * 40)
    
    def show_full_article_text(self, article: Dict):
        """Show complete article text by fetching all chunks"""
        print(f"\n📚 Fetching full text for: {article['title'][:60]}...")
        
        try:
            # Get all chunks for this article
            all_chunks = self.get_all_chunks_for_article(article)
            
            if not all_chunks:
                print("❌ Could not retrieve full article text")
                return
            
            # Combine chunks
            full_text_parts = []
            for chunk in all_chunks:
                chunk_text = chunk.get("payload", {}).get("document", "")
                if chunk_text:
                    full_text_parts.append(chunk_text)
            
            full_text = "\n\n".join(full_text_parts)
            
            print("\n" + "=" * 80)
            print("📄 FULL ARTICLE TEXT")
            print("=" * 80)
            print(f"Title: {article['title']}")
            if article.get('doi'):
                print(f"DOI: {article['doi']}")
            if article.get('year'):
                print(f"Year: {article['year']}")
            print(f"Source: {article['source']}")
            print(f"Relevance Score: {article['score']:.3f}")
            print(f"Reconstructed from: {len(all_chunks)} chunks")
            print("\n" + "=" * 80)
            print("CONTENT:")
            print("=" * 80)
            print(full_text)
            print("=" * 80)
            
            # Ask if user wants to save
            save_option = input("\n💾 Save this article to file? (y/N): ").strip().lower()
            if save_option == 'y':
                filename = f"article_{article.get('doi', 'unknown').replace('/', '_').replace('.', '_')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {article['title']}\n")
                    if article.get('doi'):
                        f.write(f"DOI: {article['doi']}\n")
                    if article.get('year'):
                        f.write(f"Year: {article['year']}\n")
                    f.write(f"Source: {article['source']}\n")
                    f.write(f"Relevance Score: {article['score']:.3f}\n")
                    f.write("\n" + "=" * 80 + "\n")
                    f.write(full_text)
                print(f"✅ Article saved to: {filename}")
            
        except Exception as e:
            print(f"❌ Error retrieving full text: {e}")
    
    def get_all_chunks_for_article(self, article: Dict) -> List[Dict]:
        """Get all chunks for a specific article"""
        title = article.get("title", "")
        doi = article.get("doi", "")
        
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
            "limit": 1000,
            "with_payload": True
        }
        
        response = requests.post(
            f"{self.qdrant_url}/collections/{self.collection}/points/scroll",
            json=search_payload
        )
        response.raise_for_status()
        
        results = response.json().get("result", {}).get("points", [])
        
        # Sort chunks by chunk number
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
    
    def show_help(self):
        """Show help information"""
        print("\n📖 HELP - Search Options")
        print("-" * 30)
        print("Basic search:")
        print("  Just type your question naturally")
        print("\nOptions:")
        print("  --chunks or -c     Show chunk previews")
        print("  --limit N          Return N articles (default: 10)")
        print("  --threshold X      Minimum relevance score (0.0-1.0, default: 0.5)")
        print("\nExamples:")
        print("  AI in radiology --limit 5")
        print("  machine learning diagnosis --chunks")
        print("  clinical decision support --threshold 0.7")
        print("\nCommands:")
        print("  help or h          Show this help")
        print("  settings           Show current settings")
        print("  quit or exit       Exit the program")
    
    def show_settings(self):
        """Show current configuration"""
        print("\n⚙️  CURRENT SETTINGS")
        print("-" * 25)
        print(f"Qdrant URL: {self.qdrant_url}")
        print(f"Collection: {self.collection}")
        print(f"Ollama URL: {self.ollama_url}")
        print(f"Embedding Model: {self.embed_model}")
        
        # Test connectivity
        try:
            # Test Qdrant
            response = requests.get(f"{self.qdrant_url}/collections/{self.collection}")
            if response.status_code == 200:
                data = response.json()
                count = data.get("result", {}).get("points_count", 0)
                print(f"✅ Qdrant: Connected ({count:,} articles)")
            else:
                print("❌ Qdrant: Connection failed")
        except:
            print("❌ Qdrant: Connection failed")
        
        try:
            # Test Ollama
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                print("✅ Ollama: Connected")
            else:
                print("❌ Ollama: Connection failed")
        except:
            print("❌ Ollama: Connection failed")

def main():
    """Main function"""
    searcher = SemanticSearcher()
    searcher.interactive_search()

if __name__ == "__main__":
    main()