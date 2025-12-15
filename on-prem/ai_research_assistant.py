#!/usr/bin/env python3
"""
AI Research Assistant - Natural Language Q&A with Source Attribution
Uses semantic search to find relevant chunks, then generates answers with detailed source breakdown
"""

import requests
import json
import argparse
import sys
from typing import List, Dict, Optional
from datetime import datetime

# Configuration
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "llama3.2"  # You can change this to your preferred model

class AIResearchAssistant:
    def __init__(self):
        self.qdrant_url = QDRANT_URL
        self.ollama_url = OLLAMA_URL
        self.collection = COLLECTION
        self.chat_model = CHAT_MODEL
        
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            print(f"❌ Error getting embedding: {e}")
            return None
    
    def search_relevant_chunks(self, query: str, limit: int = 10, threshold: float = 0.4) -> List[Dict]:
        """Search for relevant chunks using semantic similarity"""
        print(f"🔍 Searching for relevant information about: '{query}'")
        
        # Get query embedding
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
        
        # Search Qdrant
        search_payload = {
            "vector": query_embedding,
            "limit": limit,
            "with_payload": True,
            "score_threshold": threshold
        }
        
        try:
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection}/points/search",
                json=search_payload
            )
            response.raise_for_status()
            
            results = response.json().get("result", [])
            print(f"📚 Found {len(results)} relevant chunks (threshold: {threshold})")
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching database: {e}")
            return []
    
    def generate_answer(self, query: str, chunks: List[Dict]) -> Optional[str]:
        """Generate a natural language answer using the relevant chunks"""
        if not chunks:
            return None
        
        # Prepare context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            document = chunk.get("payload", {}).get("document", "")
            metadata = chunk.get("payload", {}).get("metadata", {})
            title = metadata.get("title", "Unknown")
            score = chunk.get("score", 0)
            
            context_parts.append(f"Source {i} (relevance: {score:.1%}):\nFrom: {title}\nContent: {document}\n")
        
        context = "\n".join(context_parts)
        
        # Create prompt for the AI
        prompt = f"""You are a medical research assistant. Based on the following research articles and papers, please provide a comprehensive and accurate answer to the user's question.

Question: {query}

Research Sources:
{context}

Instructions:
1. Provide a clear, well-structured answer based on the research sources provided
2. Focus on accuracy and cite specific findings when possible
3. If the sources don't fully answer the question, acknowledge the limitations
4. Use medical terminology appropriately but explain complex concepts
5. Structure your response with clear paragraphs
6. Do not make claims beyond what the sources support

Answer:"""

        print("🤖 Generating natural language answer...")
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.chat_model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
            return None
    
    def format_source_breakdown(self, chunks: List[Dict]) -> str:
        """Format detailed breakdown of sources used"""
        if not chunks:
            return "No sources found."
        
        breakdown = []
        breakdown.append("=" * 80)
        breakdown.append("📊 SOURCE BREAKDOWN")
        breakdown.append("=" * 80)
        
        # Group chunks by article
        articles = {}
        for chunk in chunks:
            metadata = chunk.get("payload", {}).get("metadata", {})
            title = metadata.get("title", "Unknown")
            doi = metadata.get("doi")
            year = metadata.get("year")
            source = metadata.get("source", "unknown")
            score = chunk.get("score", 0)
            document = chunk.get("payload", {}).get("document", "")
            
            article_key = f"{title}|{doi}"
            
            if article_key not in articles:
                articles[article_key] = {
                    "title": title,
                    "doi": doi,
                    "year": year,
                    "source": source,
                    "chunks": []
                }
            
            articles[article_key]["chunks"].append({
                "score": score,
                "content": document
            })
        
        # Sort articles by highest chunk score
        sorted_articles = sorted(articles.items(), 
                               key=lambda x: max(chunk["score"] for chunk in x[1]["chunks"]), 
                               reverse=True)
        
        for i, (article_key, article_data) in enumerate(sorted_articles, 1):
            title = article_data["title"]
            doi = article_data["doi"] or "No DOI"
            year = article_data["year"] or "Unknown"
            source = article_data["source"]
            chunks = article_data["chunks"]
            
            # Calculate average relevance
            avg_relevance = sum(chunk["score"] for chunk in chunks) / len(chunks)
            
            breakdown.append(f"\n📄 SOURCE {i}: {title[:80]}{'...' if len(title) > 80 else ''}")
            breakdown.append(f"   DOI: {doi}")
            breakdown.append(f"   Year: {year} | Source: {source}")
            breakdown.append(f"   Relevance: {avg_relevance:.1%} | Chunks used: {len(chunks)}")
            
            # Show chunk details
            for j, chunk in enumerate(sorted(chunks, key=lambda x: x["score"], reverse=True), 1):
                content_preview = chunk["content"][:150].replace('\n', ' ')
                breakdown.append(f"   Chunk {j} ({chunk['score']:.1%}): {content_preview}...")
            
            breakdown.append("")
        
        # Summary statistics
        breakdown.append("=" * 60)
        breakdown.append("📈 SEARCH STATISTICS")
        breakdown.append("=" * 60)
        breakdown.append(f"Total chunks analyzed: {len(chunks)}")
        breakdown.append(f"Unique articles: {len(articles)}")
        if chunks:
            breakdown.append(f"Average relevance: {sum(chunk.get('score', 0) for chunk in chunks) / len(chunks):.1%}")
            breakdown.append(f"Relevance range: {min(chunk.get('score', 0) for chunk in chunks):.1%} - {max(chunk.get('score', 0) for chunk in chunks):.1%}")
        else:
            breakdown.append("Average relevance: N/A")
            breakdown.append("Relevance range: N/A")
        
        return "\n".join(breakdown)
    
    def ask_question(self, query: str, limit: int = 10, threshold: float = 0.4, save_to_file: str = None) -> Dict:
        """Main method to ask a question and get a comprehensive answer"""
        print("🧠 AI Research Assistant")
        print("=" * 50)
        print(f"Question: {query}")
        print("=" * 50)
        
        # Search for relevant chunks
        chunks = self.search_relevant_chunks(query, limit, threshold)
        
        if not chunks:
            result = {
                "query": query,
                "answer": "I couldn't find any relevant information in the database to answer your question. Try rephrasing your query or using broader terms.",
                "sources": [],
                "timestamp": datetime.now().isoformat()
            }
            print("\n❌ No relevant information found.")
            return result
        
        # Generate natural language answer
        answer = self.generate_answer(query, chunks)
        
        if not answer:
            result = {
                "query": query,
                "answer": "I found relevant information but couldn't generate a proper answer. Please try again.",
                "sources": chunks,
                "timestamp": datetime.now().isoformat()
            }
            print("\n❌ Could not generate answer.")
            return result
        
        # Format the complete response
        print("\n" + "=" * 80)
        print("🎯 ANSWER")
        print("=" * 80)
        print(answer)
        print("\n")
        
        # Show source breakdown
        source_breakdown = self.format_source_breakdown(chunks)
        print(source_breakdown)
        
        # Prepare result
        result = {
            "query": query,
            "answer": answer,
            "sources": chunks,
            "source_breakdown": source_breakdown,
            "timestamp": datetime.now().isoformat(),
            "search_params": {
                "limit": limit,
                "threshold": threshold,
                "chunks_found": len(chunks)
            }
        }
        
        # Save to file if requested
        if save_to_file:
            self.save_result(result, save_to_file)
        
        return result
    
    def save_result(self, result: Dict, filename: str):
        """Save the complete result to a file"""
        try:
            # Create a formatted text version
            content = []
            content.append("AI RESEARCH ASSISTANT RESPONSE")
            content.append("=" * 50)
            content.append(f"Timestamp: {result['timestamp']}")
            content.append(f"Question: {result['query']}")
            content.append("")
            content.append("ANSWER:")
            content.append("-" * 30)
            content.append(result['answer'])
            content.append("")
            content.append(result['source_breakdown'])
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            print(f"\n💾 Complete response saved to: {filename}")
            
        except Exception as e:
            print(f"❌ Error saving to file: {e}")

def main():
    parser = argparse.ArgumentParser(description="AI Research Assistant - Natural Language Q&A with Sources")
    parser.add_argument("query", nargs='?', help="Your research question")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Maximum chunks to analyze (default: 10)")
    parser.add_argument("--threshold", "-t", type=float, default=0.4, help="Relevance threshold (default: 0.4)")
    parser.add_argument("--save", "-s", help="Save response to file")
    parser.add_argument("--model", "-m", default=CHAT_MODEL, help=f"Chat model to use (default: {CHAT_MODEL})")
    
    args = parser.parse_args()
    
    # Use the specified model
    chat_model = args.model
    
    # Get query
    query = args.query
    if not query:
        query = input("🤔 What would you like to know about medical AI research? ").strip()
        if not query:
            print("❌ No question provided")
            return
    
    # Initialize assistant
    assistant = AIResearchAssistant()
    assistant.chat_model = chat_model
    
    try:
        # Ask the question
        result = assistant.ask_question(
            query=query,
            limit=args.limit,
            threshold=args.threshold,
            save_to_file=args.save
        )
        
        print(f"\n✨ Analysis complete! Found {len(result['sources'])} relevant sources.")
        
        if args.save:
            print(f"📄 Full response saved to: {args.save}")
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()