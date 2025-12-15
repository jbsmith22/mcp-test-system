#!/usr/bin/env python3
"""
Text-based ingestion for NEJM API content
Modified version of the original Ingest.py to handle text content instead of PDFs
"""

import argparse
import json
import uuid
import requests
import tiktoken
from typing import List, Dict, Any

# Configuration - matches your existing setup
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768

def chunk_text(text: str, target_tokens: int = 512, overlap_tokens: int = 128) -> List[str]:
    """
    Chunk text using tiktoken, similar to original Ingest.py
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback to simple character-based chunking
        chunk_size = target_tokens * 4  # Rough estimate: 4 chars per token
        overlap_size = overlap_tokens * 4
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap_size
            if start >= len(text):
                break
        return chunks
    
    tokens = encoding.encode(text)
    chunks = []
    
    start = 0
    while start < len(tokens):
        end = start + target_tokens
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        start = end - overlap_tokens
        if start >= len(tokens):
            break
    
    return chunks

def get_embedding(text: str) -> List[float]:
    """
    Get embedding from Ollama, matching original Ingest.py
    """
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={
            "model": EMBED_MODEL,
            "prompt": text
        }
    )
    response.raise_for_status()
    return response.json()["embedding"]

def ingest_text_content(title: str, content: str, doi: str = None, year: int = None, source: str = "nejm-api"):
    """
    Ingest text content into Qdrant
    """
    print(f"Processing: {title}")
    
    # Chunk the content
    chunks = chunk_text(content)
    print(f"Created {len(chunks)} chunks")
    
    # Prepare points for Qdrant
    points = []
    
    for i, chunk in enumerate(chunks):
        # Get embedding
        try:
            embedding = get_embedding(chunk)
        except Exception as e:
            print(f"❌ Failed to get embedding for chunk {i+1}: {e}")
            continue
        
        # Create point
        point = {
            "id": str(uuid.uuid4()),
            "vector": embedding,
            "payload": {
                "document": chunk,
                "metadata": {
                    "title": title,
                    "doi": doi,
                    "year": year,
                    "source": source,
                    "chunk": f"chunk_{i+1}_of_{len(chunks)}"
                }
            }
        }
        points.append(point)
    
    # Upsert to Qdrant
    if points:
        try:
            response = requests.put(
                f"{QDRANT_URL}/collections/{COLLECTION}/points",
                json={"points": points}
            )
            response.raise_for_status()
            print(f"✅ Successfully ingested {len(points)} chunks")
            return True
        except Exception as e:
            print(f"❌ Failed to upsert to Qdrant: {e}")
            return False
    else:
        print("❌ No chunks to ingest")
        return False

def main():
    parser = argparse.ArgumentParser(description="Ingest text content into Qdrant")
    parser.add_argument("--text-file", required=True, help="Path to text file")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--doi", help="DOI")
    parser.add_argument("--year", type=int, help="Publication year")
    parser.add_argument("--source", default="nejm-api", help="Source identifier")
    
    args = parser.parse_args()
    
    # Read text content
    try:
        with open(args.text_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Failed to read text file: {e}")
        return False
    
    # Ingest content
    success = ingest_text_content(
        title=args.title,
        content=content,
        doi=args.doi,
        year=args.year,
        source=args.source
    )
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)