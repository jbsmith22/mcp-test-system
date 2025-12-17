#!/usr/bin/env python3
"""
NEJM Research Assistant MCP Server
Exposes semantic search and article retrieval as MCP tools with full vector visibility
"""

import asyncio
import json
import sys
from typing import Any, Sequence
import requests
from datetime import datetime

# MCP SDK imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Configuration
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768

# Initialize MCP server
app = Server("nejm-research-assistant")

class VectorSearchEngine:
    """Handles vector operations with full visibility"""
    
    def __init__(self):
        self.qdrant_url = QDRANT_URL
        self.ollama_url = OLLAMA_URL
        self.collection = COLLECTION
        self.embed_model = EMBED_MODEL
        self.embed_dim = EMBED_DIM
    
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
                "text_length": len(text)
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
                "with_vector": True,  # Include vectors in response
                "score_threshold": threshold
            }
            
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection}/points/search",
                json=search_payload,
                timeout=30
            )
            response.raise_for_status()
            results = response.json().get("result", [])
            
            # Group by article and include vector info
            articles = self._group_results_with_vectors(results)
            
            return {
                "query": {
                    "text": query,
                    "embedding": {
                        "model": self.embed_model,
                        "dimension": self.embed_dim,
                        "vector_preview": query_vector[:10],  # First 10 dimensions
                        "vector_norm": sum(x*x for x in query_vector) ** 0.5
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
        
        # Sort by score and return
        return sorted(articles.values(), key=lambda x: x["score"], reverse=True)

# Initialize search engine
search_engine = VectorSearchEngine()

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="search_articles",
            description="Search NEJM medical literature using semantic search. Returns articles with full vector visibility including embeddings, similarity scores, and weights.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query (e.g., 'AI in clinical documentation', 'diabetes treatment outcomes')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of articles to return (default: 10)",
                        "default": 10
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Minimum similarity score threshold 0-1 (default: 0.5)",
                        "default": 0.5
                    },
                    "show_vectors": {
                        "type": "boolean",
                        "description": "Include full vector embeddings in response (default: false, shows preview only)",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_database_stats",
            description="Get statistics about the NEJM article database including article counts, sources, and collection info.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_article_by_doi",
            description="Retrieve a specific article by its DOI with all associated chunks and vectors.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doi": {
                        "type": "string",
                        "description": "Article DOI (e.g., '10.1056/NEJMoa2345678')"
                    },
                    "include_vectors": {
                        "type": "boolean",
                        "description": "Include vector embeddings for all chunks (default: false)",
                        "default": False
                    }
                },
                "required": ["doi"]
            }
        ),
        Tool(
            name="compare_embeddings",
            description="Compare embedding vectors between two text inputs to see similarity scores and vector differences.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text1": {
                        "type": "string",
                        "description": "First text to compare"
                    },
                    "text2": {
                        "type": "string",
                        "description": "Second text to compare"
                    }
                },
                "required": ["text1", "text2"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    
    if name == "search_articles":
        query = arguments.get("query")
        limit = arguments.get("limit", 10)
        threshold = arguments.get("threshold", 0.5)
        show_vectors = arguments.get("show_vectors", False)
        
        result = await search_engine.search_with_vectors(query, limit, threshold)
        
        # Format response
        if "error" in result:
            return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
        
        # Build detailed response
        response_parts = []
        response_parts.append("# 🔍 NEJM Semantic Search Results\n")
        response_parts.append(f"**Query:** {result['query']['text']}\n")
        response_parts.append(f"**Found:** {result['unique_articles']} articles from {result['total_chunks_found']} chunks\n\n")
        
        # Query embedding info
        response_parts.append("## 📊 Query Embedding\n")
        emb = result['query']['embedding']
        response_parts.append(f"- **Model:** {emb['model']}\n")
        response_parts.append(f"- **Dimension:** {emb['dimension']}\n")
        response_parts.append(f"- **Vector Norm:** {emb['vector_norm']:.4f}\n")
        response_parts.append(f"- **Preview (first 10 dims):** {emb['vector_preview']}\n\n")
        
        # Results
        response_parts.append("## 📚 Top Articles\n\n")
        for i, article in enumerate(result['results'][:limit], 1):
            response_parts.append(f"### {i}. {article['title']}\n")
            response_parts.append(f"- **Relevance Score:** {article['relevance_score']}%\n")
            response_parts.append(f"- **DOI:** {article['doi'] or 'N/A'}\n")
            response_parts.append(f"- **Year:** {article['year'] or 'N/A'}\n")
            response_parts.append(f"- **Source:** {article['source']}\n")
            
            # Vector info
            vec_info = article['vector_info']
            response_parts.append(f"- **Vector Dimension:** {vec_info['dimension']}\n")
            response_parts.append(f"- **Vector Norm:** {vec_info['vector_norm']:.4f}\n")
            
            if show_vectors:
                response_parts.append(f"- **Full Vector:** {vec_info.get('full_vector', 'Not included')}\n")
            else:
                response_parts.append(f"- **Vector Preview:** {vec_info['vector_preview']}\n")
            
            response_parts.append(f"- **Content Preview:** {article['chunk_preview']}...\n\n")
        
        return [TextContent(type="text", text="".join(response_parts))]
    
    elif name == "get_database_stats":
        try:
            # Get collection info
            response = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}")
            response.raise_for_status()
            info = response.json()["result"]
            
            stats_text = "# 📊 NEJM Database Statistics\n\n"
            stats_text += f"**Collection:** {COLLECTION}\n"
            stats_text += f"**Total Points:** {info['points_count']}\n"
            stats_text += f"**Vector Dimension:** {info['config']['params']['vectors']['size']}\n"
            stats_text += f"**Distance Metric:** {info['config']['params']['vectors']['distance']}\n"
            stats_text += f"**Status:** {info['status']}\n\n"
            
            return [TextContent(type="text", text=stats_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error getting stats: {str(e)}")]
    
    elif name == "get_article_by_doi":
        doi = arguments.get("doi")
        include_vectors = arguments.get("include_vectors", False)
        
        try:
            # Search for article by DOI
            response = requests.post(
                f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
                json={
                    "filter": {
                        "must": [
                            {"key": "metadata.doi", "match": {"value": doi}}
                        ]
                    },
                    "limit": 100,
                    "with_payload": True,
                    "with_vector": include_vectors
                }
            )
            response.raise_for_status()
            points = response.json()["result"]["points"]
            
            if not points:
                return [TextContent(type="text", text=f"❌ No article found with DOI: {doi}")]
            
            # Format response
            article_text = f"# 📄 Article: {doi}\n\n"
            article_text += f"**Total Chunks:** {len(points)}\n\n"
            
            for i, point in enumerate(points, 1):
                metadata = point["payload"]["metadata"]
                article_text += f"## Chunk {i}\n"
                article_text += f"**Title:** {metadata.get('title', 'N/A')}\n"
                article_text += f"**Year:** {metadata.get('year', 'N/A')}\n"
                article_text += f"**Source:** {metadata.get('source', 'N/A')}\n"
                
                if include_vectors and "vector" in point:
                    vec = point["vector"]
                    article_text += f"**Vector Dimension:** {len(vec)}\n"
                    article_text += f"**Vector Preview:** {vec[:10]}\n"
                
                article_text += f"**Content:** {point['payload']['document'][:300]}...\n\n"
            
            return [TextContent(type="text", text=article_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
    
    elif name == "compare_embeddings":
        text1 = arguments.get("text1")
        text2 = arguments.get("text2")
        
        # Get embeddings for both texts
        emb1 = await search_engine.get_embedding(text1)
        emb2 = await search_engine.get_embedding(text2)
        
        if "error" in emb1 or "error" in emb2:
            return [TextContent(type="text", text="❌ Error getting embeddings")]
        
        # Calculate cosine similarity
        vec1 = emb1["vector"]
        vec2 = emb2["vector"]
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(x * x for x in vec1) ** 0.5
        norm2 = sum(x * x for x in vec2) ** 0.5
        similarity = dot_product / (norm1 * norm2)
        
        # Format response
        response = "# 🔬 Embedding Comparison\n\n"
        response += f"## Text 1\n**Content:** {text1}\n"
        response += f"**Vector Norm:** {norm1:.4f}\n"
        response += f"**Preview:** {vec1[:10]}\n\n"
        
        response += f"## Text 2\n**Content:** {text2}\n"
        response += f"**Vector Norm:** {norm2:.4f}\n"
        response += f"**Preview:** {vec2[:10]}\n\n"
        
        response += f"## Similarity\n"
        response += f"**Cosine Similarity:** {similarity:.4f} ({similarity * 100:.2f}%)\n"
        response += f"**Interpretation:** "
        if similarity > 0.8:
            response += "Very similar concepts\n"
        elif similarity > 0.6:
            response += "Related concepts\n"
        elif similarity > 0.4:
            response += "Somewhat related\n"
        else:
            response += "Different concepts\n"
        
        return [TextContent(type="text", text=response)]
    
    else:
        return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
