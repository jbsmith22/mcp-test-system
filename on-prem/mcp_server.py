#!/usr/bin/env python3
"""
NEJM Research Assistant MCP Server
Complete RAG system exposed as MCP tools with full vector visibility
ALL searches, ingestion, and article management go through this server
"""

import asyncio
import json
import sys
import os
from typing import Any, Sequence, List, Dict, Optional
import requests
from datetime import datetime

# MCP SDK imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Configuration from environment variables
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
COLLECTION = os.getenv("COLLECTION", "articles_ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2")
EMBED_DIM = 768

# NEJM API Configuration
NEJM_API_BASE = os.getenv("NEJM_API_BASE", "https://onesearch-api.nejmgroup-qa.org")
NEJM_API_USER = os.getenv("NEJM_API_USER", "")
NEJM_API_KEY = os.getenv("NEJM_API_KEY", "")

# Initialize MCP server
app = Server("nejm-research-assistant")


class NEJMResearchEngine:
    """Complete NEJM Research Assistant with RAG, vector search, and article management"""
    
    def __init__(self):
        self.qdrant_url = QDRANT_URL
        self.ollama_url = OLLAMA_URL
        self.collection = COLLECTION
        self.embed_model = EMBED_MODEL
        self.chat_model = CHAT_MODEL
        self.embed_dim = EMBED_DIM
        self.nejm_api_base = NEJM_API_BASE
        self.nejm_api_user = NEJM_API_USER
        self.nejm_api_key = NEJM_API_KEY
    
    async def get_embedding(self, text: str) -> dict:
        """Get embedding vector with metadata"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text},
                timeout=30
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            
            return {
                "vector": embedding,
                "dimension": len(embedding),
                "model": self.embed_model,
                "text": text,
                "text_length": len(text),
                "vector_norm": sum(x*x for x in embedding) ** 0.5
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def search_with_vectors(self, query: str, limit: int = 10, threshold: float = 0.5) -> dict:
        """Search with full vector visibility"""
        
        # Get query embedding
        query_embedding_info = await self.get_embedding(query)
        if "error" in query_embedding_info:
            return {"error": f"Failed to get query embedding: {query_embedding_info['error']}"}
        
        query_vector = query_embedding_info["vector"]
        
        # Search Qdrant
        try:
            search_payload = {
                "vector": query_vector,
                "limit": limit * 3,
                "with_payload": True,
                "with_vector": True,
                "score_threshold": threshold
            }
            
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection}/points/search",
                json=search_payload,
                timeout=30
            )
            response.raise_for_status()
            results = response.json().get("result", [])
            
            # Group by article
            articles = self._group_results_with_vectors(results)
            
            return {
                "query": {
                    "text": query,
                    "embedding": {
                        "model": self.embed_model,
                        "dimension": self.embed_dim,
                        "vector_preview": query_vector[:10],
                        "vector_norm": query_embedding_info["vector_norm"]
                    }
                },
                "results": articles,
                "total_chunks_found": len(results),
                "unique_articles": len(articles),
                "search_params": {
                    "limit": limit,
                    "threshold": threshold,
                    "collection": self.collection
                }
            }
            
        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}
    
    def _group_results_with_vectors(self, results: list) -> list:
        """Group chunks by article with vector information"""
        articles = {}
        
        for result in results:
            metadata = result.get("payload", {}).get("metadata", {})
            title = metadata.get("title", "Unknown")
            doi = metadata.get("doi", "")
            article_key = doi if doi else title
            
            if article_key not in articles or result["score"] > articles[article_key]["score"]:
                vector = result.get("vector", [])
                articles[article_key] = {
                    "title": title,
                    "doi": doi,
                    "year": metadata.get("year"),
                    "source": metadata.get("source", "unknown"),
                    "relevance_score": round(result["score"] * 100, 2),
                    "chunk_preview": result.get("payload", {}).get("document", "")[:200],
                    "vector_info": {
                        "dimension": len(vector),
                        "vector_preview": vector[:10] if vector else [],
                        "vector_norm": sum(x*x for x in vector) ** 0.5 if vector else 0
                    },
                    "score": result["score"]
                }
        
        return sorted(articles.values(), key=lambda x: x["score"], reverse=True)
    
    async def ask_research_question(self, question: str, limit: int = 10, threshold: float = 0.4) -> dict:
        """Ask a research question and get AI-generated answer with sources"""
        
        # First, search for relevant chunks
        search_result = await self.search_with_vectors(question, limit, threshold)
        
        if "error" in search_result:
            return search_result
        
        if not search_result["results"]:
            return {"error": "No relevant articles found"}
        
        # Build context from top results
        context_parts = []
        for i, article in enumerate(search_result["results"][:10], 1):
            context_parts.append(
                f"[Source {i}] {article['title']} ({article['relevance_score']}% relevant): "
                f"{article['chunk_preview']}"
            )
        
        context = "\n\n".join(context_parts)
        
        # Create prompt for LLM
        prompt = f"""Based on the following medical research sources, please answer this question: {question}

Sources:
{context}

Please provide a comprehensive answer based on these sources. Be specific and cite which sources support your points."""
        
        try:
            # Generate answer with LLM
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.chat_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            answer = response.json().get("response", "")
            
            return {
                "question": question,
                "answer": answer,
                "sources": search_result["results"][:10],
                "total_sources": len(search_result["results"]),
                "query_embedding": search_result["query"]["embedding"]
            }
        except Exception as e:
            return {"error": f"Failed to generate answer: {str(e)}"}
    
    async def get_database_stats(self) -> dict:
        """Get database statistics"""
        try:
            response = requests.get(f"{self.qdrant_url}/collections/{self.collection}")
            response.raise_for_status()
            info = response.json()["result"]
            
            return {
                "collection": self.collection,
                "total_points": info["points_count"],
                "vector_dimension": info["config"]["params"]["vectors"]["size"],
                "distance_metric": info["config"]["params"]["vectors"]["distance"],
                "status": info["status"]
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def list_articles(self, source_filter: Optional[str] = None, limit: int = 100) -> dict:
        """List all articles in database"""
        try:
            scroll_filter = {}
            if source_filter:
                scroll_filter = {
                    "filter": {
                        "must": [{"key": "metadata.source", "match": {"value": source_filter}}]
                    }
                }
            
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection}/points/scroll",
                json={**scroll_filter, "limit": limit, "with_payload": True, "with_vector": False},
                timeout=30
            )
            response.raise_for_status()
            points = response.json()["result"]["points"]
            
            # Group by article
            articles = {}
            for point in points:
                metadata = point["payload"]["metadata"]
                doi = metadata.get("doi", "")
                title = metadata.get("title", "Unknown")
                key = doi if doi else title
                
                if key not in articles:
                    articles[key] = {
                        "title": title,
                        "doi": doi,
                        "year": metadata.get("year"),
                        "source": metadata.get("source"),
                        "chunks": 0
                    }
                articles[key]["chunks"] += 1
            
            return {
                "total_articles": len(articles),
                "total_chunks": len(points),
                "articles": list(articles.values())
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_article_by_doi(self, doi: str, include_vectors: bool = False) -> dict:
        """Retrieve article by DOI from database"""
        try:
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection}/points/scroll",
                json={
                    "filter": {"must": [{"key": "metadata.doi", "match": {"value": doi}}]},
                    "limit": 100,
                    "with_payload": True,
                    "with_vector": include_vectors
                }
            )
            response.raise_for_status()
            points = response.json()["result"]["points"]
            
            if not points:
                return {"error": f"No article found with DOI: {doi}"}
            
            chunks = []
            for point in points:
                chunk_data = {
                    "text": point["payload"]["document"],
                    "metadata": point["payload"]["metadata"]
                }
                if include_vectors and "vector" in point:
                    vec = point["vector"]
                    chunk_data["vector_info"] = {
                        "dimension": len(vec),
                        "preview": vec[:10],
                        "norm": sum(x*x for x in vec) ** 0.5
                    }
                chunks.append(chunk_data)
            
            return {
                "doi": doi,
                "title": chunks[0]["metadata"].get("title", "Unknown"),
                "total_chunks": len(chunks),
                "chunks": chunks
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_clean_article_from_api(self, doi: str) -> dict:
        """Retrieve clean article from NEJM API"""
        if not self.nejm_api_user or not self.nejm_api_key:
            return {"error": "NEJM API credentials not configured"}
        
        try:
            url = f"{self.nejm_api_base}/api/v1/content/{doi}"
            headers = {"apiuser": self.nejm_api_user, "apikey": self.nejm_api_key}
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            content = response.json()
            
            return {
                "doi": doi,
                "title": content.get("title", ""),
                "abstract": content.get("displayAbstract", ""),
                "content": content.get("document", ""),
                "publication_date": content.get("publicationDate", ""),
                "authors": content.get("authors", [])
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def compare_embeddings(self, text1: str, text2: str) -> dict:
        """Compare embeddings between two texts"""
        emb1 = await self.get_embedding(text1)
        emb2 = await self.get_embedding(text2)
        
        if "error" in emb1 or "error" in emb2:
            return {"error": "Failed to get embeddings"}
        
        vec1 = emb1["vector"]
        vec2 = emb2["vector"]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        similarity = dot_product / (emb1["vector_norm"] * emb2["vector_norm"])
        
        return {
            "text1": {"content": text1, "norm": emb1["vector_norm"], "preview": vec1[:10]},
            "text2": {"content": text2, "norm": emb2["vector_norm"], "preview": vec2[:10]},
            "similarity": similarity,
            "similarity_percent": round(similarity * 100, 2)
        }


# Initialize engine
engine = NEJMResearchEngine()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools"""
    return [
        Tool(
            name="search_articles",
            description="Search NEJM medical literature using semantic search with full vector visibility",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "limit": {"type": "integer", "description": "Max articles (default: 10)", "default": 10},
                    "threshold": {"type": "number", "description": "Min similarity 0-1 (default: 0.5)", "default": 0.5},
                    "show_vectors": {"type": "boolean", "description": "Show full vectors (default: false)", "default": False}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="ask_research_question",
            description="Ask a research question and get AI-generated answer with source attribution and vector visibility",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Your research question"},
                    "limit": {"type": "integer", "description": "Max chunks to analyze (default: 10)", "default": 10},
                    "threshold": {"type": "number", "description": "Relevance threshold (default: 0.4)", "default": 0.4}
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="list_all_articles",
            description="List all articles in the database with metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_filter": {"type": "string", "description": "Filter by source (optional)"},
                    "limit": {"type": "integer", "description": "Max articles (default: 100)", "default": 100}
                }
            }
        ),
        Tool(
            name="get_database_stats",
            description="Get database statistics and health info",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_article_by_doi",
            description="Retrieve specific article by DOI with all chunks and optional vectors",
            inputSchema={
                "type": "object",
                "properties": {
                    "doi": {"type": "string", "description": "Article DOI"},
                    "include_vectors": {"type": "boolean", "description": "Include vectors (default: false)", "default": False}
                },
                "required": ["doi"]
            }
        ),
        Tool(
            name="get_clean_article",
            description="Retrieve clean, formatted article from NEJM API by DOI",
            inputSchema={
                "type": "object",
                "properties": {"doi": {"type": "string", "description": "Article DOI"}},
                "required": ["doi"]
            }
        ),
        Tool(
            name="compare_embeddings",
            description="Compare embedding vectors between two texts",
            inputSchema={
                "type": "object",
                "properties": {
                    "text1": {"type": "string", "description": "First text"},
                    "text2": {"type": "string", "description": "Second text"}
                },
                "required": ["text1", "text2"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle all tool calls"""
    
    if name == "search_articles":
        result = await engine.search_with_vectors(
            arguments.get("query"),
            arguments.get("limit", 10),
            arguments.get("threshold", 0.5)
        )
        
        if "error" in result:
            return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
        
        response = f"# 🔍 NEJM Semantic Search Results\n\n"
        response += f"**Query:** {result['query']['text']}\n"
        response += f"**Found:** {result['unique_articles']} articles from {result['total_chunks_found']} chunks\n\n"
        
        response += "## 📊 Query Embedding\n"
        emb = result['query']['embedding']
        response += f"- **Model:** {emb['model']}\n"
        response += f"- **Dimension:** {emb['dimension']}\n"
        response += f"- **Vector Norm:** {emb['vector_norm']:.4f}\n"
        response += f"- **Preview:** {emb['vector_preview']}\n\n"
        
        response += "## 📚 Top Articles\n\n"
        for i, article in enumerate(result['results'][:arguments.get("limit", 10)], 1):
            response += f"### {i}. {article['title']}\n"
            response += f"- **Relevance:** {article['relevance_score']}%\n"
            response += f"- **DOI:** {article['doi'] or 'N/A'}\n"
            response += f"- **Year:** {article['year'] or 'N/A'}\n"
            response += f"- **Source:** {article['source']}\n"
            response += f"- **Vector Norm:** {article['vector_info']['vector_norm']:.4f}\n"
            response += f"- **Vector Preview:** {article['vector_info']['vector_preview']}\n"
            response += f"- **Content:** {article['chunk_preview']}...\n\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "ask_research_question":
        result = await engine.ask_research_question(
            arguments.get("question"),
            arguments.get("limit", 10),
            arguments.get("threshold", 0.4)
        )
        
        if "error" in result:
            return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
        
        response = f"# 🧠 AI Research Assistant Answer\n\n"
        response += f"**Question:** {result['question']}\n\n"
        response += f"## 💡 Answer\n\n{result['answer']}\n\n"
        response += f"## 📚 Sources Used ({result['total_sources']} articles)\n\n"
        
        for i, source in enumerate(result['sources'], 1):
            response += f"{i}. **{source['title']}** ({source['relevance_score']}% relevant)\n"
            response += f"   - DOI: {source['doi'] or 'N/A'}\n"
            response += f"   - Year: {source['year'] or 'N/A'}\n\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "list_all_articles":
        result = await engine.list_articles(
            arguments.get("source_filter"),
            arguments.get("limit", 100)
        )
        
        if "error" in result:
            return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
        
        response = f"# 📚 NEJM Article Database\n\n"
        response += f"**Total Articles:** {result['total_articles']}\n"
        response += f"**Total Chunks:** {result['total_chunks']}\n\n"
        
        for article in result['articles'][:50]:
            response += f"- **{article['title']}**\n"
            response += f"  - DOI: {article['doi'] or 'N/A'}\n"
            response += f"  - Year: {article['year'] or 'N/A'}\n"
            response += f"  - Source: {article['source']}\n"
            response += f"  - Chunks: {article['chunks']}\n\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "get_database_stats":
        result = await engine.get_database_stats()
        
        if "error" in result:
            return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
        
        response = f"# 📊 Database Statistics\n\n"
        response += f"- **Collection:** {result['collection']}\n"
        response += f"- **Total Points:** {result['total_points']}\n"
        response += f"- **Vector Dimension:** {result['vector_dimension']}\n"
        response += f"- **Distance Metric:** {result['distance_metric']}\n"
        response += f"- **Status:** {result['status']}\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "get_article_by_doi":
        result = await engine.get_article_by_doi(
            arguments.get("doi"),
            arguments.get("include_vectors", False)
        )
        
        if "error" in result:
            return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
        
        response = f"# 📄 Article: {result['title']}\n\n"
        response += f"**DOI:** {result['doi']}\n"
        response += f"**Total Chunks:** {result['total_chunks']}\n\n"
        
        for i, chunk in enumerate(result['chunks'], 1):
            response += f"## Chunk {i}\n"
            response += f"{chunk['text'][:300]}...\n\n"
            if "vector_info" in chunk:
                response += f"**Vector Info:**\n"
                response += f"- Dimension: {chunk['vector_info']['dimension']}\n"
                response += f"- Norm: {chunk['vector_info']['norm']:.4f}\n"
                response += f"- Preview: {chunk['vector_info']['preview']}\n\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "get_clean_article":
        result = await engine.get_clean_article_from_api(arguments.get("doi"))
        
        if "error" in result:
            return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
        
        response = f"# 📄 {result['title']}\n\n"
        response += f"**DOI:** {result['doi']}\n"
        response += f"**Published:** {result['publication_date']}\n\n"
        response += f"## Abstract\n\n{result['abstract']}\n\n"
        response += f"## Full Content\n\n{result['content'][:1000]}...\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "compare_embeddings":
        result = await engine.compare_embeddings(
            arguments.get("text1"),
            arguments.get("text2")
        )
        
        if "error" in result:
            return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
        
        response = f"# 🔬 Embedding Comparison\n\n"
        response += f"## Text 1\n**Content:** {result['text1']['content']}\n"
        response += f"**Norm:** {result['text1']['norm']:.4f}\n"
        response += f"**Preview:** {result['text1']['preview']}\n\n"
        response += f"## Text 2\n**Content:** {result['text2']['content']}\n"
        response += f"**Norm:** {result['text2']['norm']:.4f}\n"
        response += f"**Preview:** {result['text2']['preview']}\n\n"
        response += f"## Similarity\n"
        response += f"**Score:** {result['similarity']:.4f} ({result['similarity_percent']}%)\n"
        
        return [TextContent(type="text", text=response)]
    
    else:
        return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
