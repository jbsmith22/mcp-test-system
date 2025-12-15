#!/usr/bin/env python3
"""
NEJM Research Web Interface
A simple web frontend for testing queries and monitoring database state
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime
from typing import Dict, List
import tempfile

# Import your existing modules
from ai_research_assistant import AIResearchAssistant
from list_all_articles import get_all_articles
from clean_article_retriever import CleanArticleRetriever

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Add security headers
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Configuration
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "articles_ollama"

class DatabaseStats:
    """Get database statistics and health info"""
    
    def __init__(self):
        self.qdrant_url = QDRANT_URL
        self.collection = COLLECTION
    
    def get_stats(self) -> Dict:
        """Get comprehensive database statistics"""
        try:
            # Get collection info
            response = requests.get(f"{self.qdrant_url}/collections/{self.collection}")
            if response.status_code != 200:
                return {"error": "Could not connect to Qdrant database"}
            
            collection_info = response.json()["result"]
            
            # Get all articles for detailed stats
            try:
                articles = get_all_articles()
                if articles:
                    # Group by source
                    by_source = {}
                    total_chunks = 0
                    
                    for article in articles.values():
                        source = article["source"]
                        if source not in by_source:
                            by_source[source] = {"count": 0, "chunks": 0}
                        by_source[source]["count"] += 1
                        by_source[source]["chunks"] += article["chunk_count"]
                        total_chunks += article["chunk_count"]
                    
                    return {
                        "status": "healthy",
                        "total_points": collection_info["points_count"],
                        "total_articles": len(articles),
                        "total_chunks": total_chunks,
                        "avg_chunks_per_article": total_chunks / len(articles) if articles else 0,
                        "by_source": by_source,
                        "vector_size": collection_info["config"]["params"]["vectors"]["size"],
                        "distance_metric": collection_info["config"]["params"]["vectors"]["distance"],
                        "last_updated": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "empty",
                        "total_points": collection_info["points_count"],
                        "message": "No articles found in database"
                    }
            except Exception as e:
                return {
                    "status": "partial",
                    "total_points": collection_info["points_count"],
                    "error": f"Could not get detailed stats: {e}"
                }
                
        except Exception as e:
            return {"error": f"Database connection failed: {e}"}

# Initialize components
db_stats = DatabaseStats()
ai_assistant = AIResearchAssistant()
clean_retriever = CleanArticleRetriever()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    """Get database statistics"""
    stats = db_stats.get_stats()
    return jsonify(stats)

@app.route('/api/search', methods=['POST'])
def api_search():
    """Perform AI research assistant search"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Get parameters
        limit = data.get('limit', 10)
        threshold = data.get('threshold', 0.4)
        save_file = data.get('save_file', '')
        
        # Perform search
        result = ai_assistant.ask_question(
            query=query,
            limit=limit,
            threshold=threshold,
            save_to_file=save_file if save_file else None
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/clean-search', methods=['POST'])
def api_clean_search():
    """Perform clean article search"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Get clean article
        clean_content = clean_retriever.search_and_get_clean_article(query)
        
        if clean_content:
            return jsonify({
                "success": True,
                "content": clean_content,
                "query": query
            })
        else:
            return jsonify({
                "success": False,
                "message": "No clean article content found",
                "query": query
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/articles')
def api_articles():
    """Get list of all articles"""
    try:
        articles = get_all_articles()
        if articles:
            # Convert to list format for JSON
            article_list = []
            for article_data in articles.values():
                article_list.append({
                    "title": article_data["title"],
                    "doi": article_data["doi"],
                    "year": article_data["year"],
                    "source": article_data["source"],
                    "chunk_count": article_data["chunk_count"]
                })
            
            # Sort by source, then by year (newest first)
            article_list.sort(key=lambda x: (x["source"], -(x["year"] or 0)))
            
            return jsonify({
                "success": True,
                "articles": article_list,
                "total": len(article_list)
            })
        else:
            return jsonify({
                "success": False,
                "message": "No articles found"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/import', methods=['POST'])
def api_import():
    """Import articles from various sources"""
    try:
        data = request.get_json()
        source = data.get('source', '').strip()
        article_type = data.get('article_type', '').strip()
        count = data.get('count', 10)
        
        if not source:
            return jsonify({"error": "Source is required"}), 400
        
        # Import based on source
        if source == 'nejm':
            from ingest_nejm_100 import main as ingest_nejm
            # Create a modified version that takes parameters
            result = import_nejm_articles(count)
        elif source == 'nejm-ai':
            from ingest_next_100 import main as ingest_nejm_ai
            result = import_nejm_ai_articles(count)
        elif source == 'catalyst':
            result = import_catalyst_articles(count)
        elif source == 'evidence':
            result = import_evidence_articles(count)
        elif source == 'clinician':
            result = import_clinician_articles(count)
        else:
            return jsonify({"error": f"Unknown source: {source}"}), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def import_nejm_articles(count):
    """Import NEJM articles avoiding duplicates"""
    from nejm_api_client import NEJMAPIClient
    from config_manager import ConfigManager
    
    # Get existing DOIs to avoid duplicates
    existing_dois = get_existing_dois('nejm-api-nejm')
    
    config = ConfigManager()
    api_key = config.get_api_key("qa")
    
    if not api_key:
        return {"error": "No API key found"}
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    client = NEJMAPIClient(base_url)
    
    if '|' in api_key:
        user_id, key = api_key.split('|', 1)
        client.session.headers.update({
            "apiuser": user_id,
            "apikey": key
        })
    
    # Fetch articles with pagination to avoid duplicates
    all_articles = []
    page = 1
    articles_needed = count
    
    while len(all_articles) < articles_needed and page <= 10:  # Max 10 pages
        endpoint = f"{base_url}/api/v1/simple"
        params = {
            "context": "nejm",
            "objectType": "nejm-article",
            "sortBy": "pubdate-descending",
            "pageLength": 50,
            "startPage": page,
            "showFacets": "N"
        }
        
        response = client.session.get(endpoint, params=params)
        if response.status_code != 200:
            break
            
        data = response.json()
        articles = data.get('results', [])
        
        # Filter out existing articles
        new_articles = []
        for article in articles:
            doi = article.get('doi')
            if doi and doi not in existing_dois:
                new_articles.append(article)
                if len(all_articles) + len(new_articles) >= articles_needed:
                    break
        
        all_articles.extend(new_articles)
        page += 1
    
    # Limit to requested count
    all_articles = all_articles[:count]
    
    # Ingest articles
    successful = 0
    failed = 0
    
    for article in all_articles:
        try:
            if client.ingest_article(article, "nejm"):
                successful += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    
    return {
        "success": True,
        "source": "nejm",
        "requested": count,
        "found": len(all_articles),
        "successful": successful,
        "failed": failed,
        "message": f"Successfully imported {successful} NEJM articles"
    }

def import_nejm_ai_articles(count):
    """Import NEJM-AI articles avoiding duplicates"""
    from nejm_api_client import NEJMAPIClient
    from config_manager import ConfigManager
    
    existing_dois = get_existing_dois('nejm-api-nejm-ai')
    
    config = ConfigManager()
    api_key = config.get_api_key("qa")
    
    if not api_key:
        return {"error": "No API key found"}
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    client = NEJMAPIClient(base_url)
    
    if '|' in api_key:
        user_id, key = api_key.split('|', 1)
        client.session.headers.update({
            "apiuser": user_id,
            "apikey": key
        })
    
    # Fetch articles avoiding duplicates
    all_articles = []
    page = 1
    
    while len(all_articles) < count and page <= 10:
        endpoint = f"{base_url}/api/v1/simple"
        params = {
            "context": "nejm-ai",
            "objectType": "nejm-ai-article",
            "sortBy": "pubdate-descending",
            "pageLength": 50,
            "startPage": page,
            "showFacets": "N"
        }
        
        response = client.session.get(endpoint, params=params)
        if response.status_code != 200:
            break
            
        data = response.json()
        articles = data.get('results', [])
        
        # Filter out existing articles
        for article in articles:
            doi = article.get('doi')
            if doi and doi not in existing_dois:
                all_articles.append(article)
                if len(all_articles) >= count:
                    break
        
        page += 1
    
    # Ingest articles
    successful = 0
    failed = 0
    
    for article in all_articles[:count]:
        try:
            if client.ingest_article(article, "nejm-ai"):
                successful += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    
    return {
        "success": True,
        "source": "nejm-ai",
        "requested": count,
        "found": len(all_articles),
        "successful": successful,
        "failed": failed,
        "message": f"Successfully imported {successful} NEJM-AI articles"
    }

def import_catalyst_articles(count):
    """Import Catalyst articles avoiding duplicates"""
    return import_nejm_context_articles("catalyst", count)

def import_evidence_articles(count):
    """Import Evidence articles avoiding duplicates"""
    return import_nejm_context_articles("evidence", count)

def import_clinician_articles(count):
    """Import Clinician articles avoiding duplicates"""
    return import_nejm_context_articles("clinician", count)

def import_nejm_context_articles(context, count):
    """Generic function to import from any NEJM context"""
    from nejm_api_client import NEJMAPIClient
    from config_manager import ConfigManager
    
    existing_dois = get_existing_dois(f'nejm-api-{context}')
    
    config = ConfigManager()
    api_key = config.get_api_key("qa")
    
    if not api_key:
        return {"error": "No API key found"}
    
    base_url = "https://onesearch-api.nejmgroup-qa.org"
    client = NEJMAPIClient(base_url)
    
    if '|' in api_key:
        user_id, key = api_key.split('|', 1)
        client.session.headers.update({
            "apiuser": user_id,
            "apikey": key
        })
    
    # Fetch articles avoiding duplicates
    all_articles = []
    page = 1
    
    while len(all_articles) < count and page <= 10:
        endpoint = f"{base_url}/api/v1/simple"
        params = {
            "context": context,
            "objectType": f"{context}-article",
            "sortBy": "pubdate-descending",
            "pageLength": 50,
            "startPage": page,
            "showFacets": "N"
        }
        
        response = client.session.get(endpoint, params=params)
        if response.status_code != 200:
            break
            
        data = response.json()
        articles = data.get('results', [])
        
        # Filter out existing articles
        for article in articles:
            doi = article.get('doi')
            if doi and doi not in existing_dois:
                all_articles.append(article)
                if len(all_articles) >= count:
                    break
        
        page += 1
    
    # Ingest articles
    successful = 0
    failed = 0
    
    for article in all_articles[:count]:
        try:
            if client.ingest_article(article, context):
                successful += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    
    return {
        "success": True,
        "source": context,
        "requested": count,
        "found": len(all_articles),
        "successful": successful,
        "failed": failed,
        "message": f"Successfully imported {successful} {context.title()} articles"
    }

def get_existing_dois(source_filter=None):
    """Get set of existing DOIs to avoid duplicates"""
    try:
        articles = get_all_articles()
        existing_dois = set()
        
        if articles:
            for article_data in articles.values():
                if source_filter is None or article_data["source"] == source_filter:
                    doi = article_data.get("doi")
                    if doi:
                        existing_dois.add(doi)
        
        return existing_dois
    except Exception:
        return set()

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    try:
        # Check Qdrant
        qdrant_response = requests.get(f"{QDRANT_URL}/healthz", timeout=5)
        qdrant_healthy = qdrant_response.status_code == 200
        
        # Check Ollama
        try:
            ollama_response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
            ollama_healthy = ollama_response.status_code == 200
            ollama_models = ollama_response.json().get("models", []) if ollama_healthy else []
        except:
            ollama_healthy = False
            ollama_models = []
        
        return jsonify({
            "status": "healthy" if (qdrant_healthy and ollama_healthy) else "degraded",
            "services": {
                "qdrant": {
                    "status": "healthy" if qdrant_healthy else "unhealthy",
                    "url": QDRANT_URL
                },
                "ollama": {
                    "status": "healthy" if ollama_healthy else "unhealthy",
                    "url": "http://127.0.0.1:11434",
                    "models": [model["name"] for model in ollama_models]
                }
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("🌐 Starting NEJM Research Web Interface...")
    print("📊 Dashboard: http://127.0.0.1:8080")
    print("🔍 Ready for queries!")
    
    app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)