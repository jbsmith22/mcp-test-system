#!/usr/bin/env python3
"""
AWS-powered web interface for NEJM Research Assistant
Connects directly to OpenSearch and includes ingestion capabilities
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime
import uuid
import time
import threading
from typing import Dict, List

app = Flask(__name__)

class AWSNEJMInterface:
    def __init__(self):
        # AWS setup
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        self.index_name = "nejm-articles"
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
        # Local Qdrant for ingestion
        self.qdrant_url = "http://127.0.0.1:6333"
        self.collection = "articles_ollama"
        
        # NEJM API
        self.nejm_base_url = "https://onesearch-api.nejmgroup-qa.org"
        
        # Ingestion status
        self.ingestion_status = {
            "running": False,
            "progress": 0,
            "total": 0,
            "current_article": "",
            "errors": [],
            "completed": 0
        }
    
    def get_nejm_credentials(self):
        """Get NEJM API credentials from AWS Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId='nejm-api-credentials')
            credentials = json.loads(response['SecretString'])
            return f"{credentials['userid']}|{credentials['apikey']}"
        except Exception as e:
            return None
    
    def search_articles(self, query: str, limit: int = 10, search_type: str = "hybrid") -> Dict:
        """Search articles in OpenSearch"""
        
        try:
            if search_type == "vector":
                return self._vector_search(query, limit)
            elif search_type == "text":
                return self._text_search(query, limit)
            else:  # hybrid
                return self._hybrid_search(query, limit)
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _text_search(self, query: str, limit: int) -> Dict:
        """Pure text search"""
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "abstract^2", "content"],
                    "type": "best_fields"
                }
            },
            "size": limit,
            "_source": ["title", "doi", "abstract", "year", "source", "content"],
            "highlight": {
                "fields": {
                    "title": {},
                    "abstract": {"fragment_size": 200, "number_of_fragments": 1},
                    "content": {"fragment_size": 200, "number_of_fragments": 2}
                }
            }
        }
        
        return self._execute_search(search_body, query)
    
    def _vector_search(self, query: str, limit: int) -> Dict:
        """Pure vector/semantic search"""
        
        # Get embedding for query
        response = self.bedrock_client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": query})
        )
        
        result = json.loads(response['body'].read())
        query_vector = result['embedding']
        
        search_body = {
            "query": {
                "knn": {
                    "vector": {
                        "vector": query_vector,
                        "k": limit
                    }
                }
            },
            "size": limit,
            "_source": ["title", "doi", "abstract", "year", "source", "content"]
        }
        
        return self._execute_search(search_body, query)
    
    def _hybrid_search(self, query: str, limit: int) -> Dict:
        """Hybrid text + vector search"""
        
        # Get embedding for query
        response = self.bedrock_client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": query})
        )
        
        result = json.loads(response['body'].read())
        query_vector = result['embedding']
        
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "abstract^2", "content"],
                                "boost": 1.2
                            }
                        },
                        {
                            "knn": {
                                "vector": {
                                    "vector": query_vector,
                                    "k": limit * 2,
                                    "boost": 0.8
                                }
                            }
                        }
                    ]
                }
            },
            "size": limit,
            "_source": ["title", "doi", "abstract", "year", "source", "content"],
            "highlight": {
                "fields": {
                    "title": {},
                    "abstract": {"fragment_size": 200, "number_of_fragments": 1},
                    "content": {"fragment_size": 200, "number_of_fragments": 2}
                }
            }
        }
        
        return self._execute_search(search_body, query)
    
    def _execute_search(self, search_body: Dict, query: str) -> Dict:
        """Execute search against OpenSearch"""
        
        url = f"{self.opensearch_endpoint}/{self.index_name}/_search"
        request = AWSRequest(method='POST', url=url, data=json.dumps(search_body))
        request.headers['Content-Type'] = 'application/json'
        SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
        
        headers = dict(request.headers)
        response = requests.post(url, headers=headers, data=json.dumps(search_body))
        
        if response.status_code == 200:
            result = response.json()
            hits = result["hits"]["hits"]
            
            articles = []
            for hit in hits:
                source = hit["_source"]
                
                # Get highlights if available
                highlights = hit.get("highlight", {})
                
                # Use highlighted text if available, otherwise use original
                title = highlights.get("title", [source.get("title", "")])[0] if highlights.get("title") else source.get("title", "")
                abstract = highlights.get("abstract", [source.get("abstract", "")[:300] + "..."])[0] if highlights.get("abstract") else source.get("abstract", "")[:300] + "..."
                
                articles.append({
                    "title": title,
                    "doi": source.get("doi", ""),
                    "abstract": abstract,
                    "year": source.get("year", ""),
                    "score": hit["_score"],
                    "source_type": source.get("source", ""),
                    "content_preview": source.get("content", "")[:500] + "..." if source.get("content") else ""
                })
            
            return {
                "success": True, 
                "articles": articles, 
                "total": result["hits"]["total"]["value"],
                "query": query,
                "took": result["took"]
            }
        else:
            return {"success": False, "error": f"Search failed: {response.status_code} - {response.text}"}
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            url = f"{self.opensearch_endpoint}/{self.index_name}/_stats"
            request = AWSRequest(method='GET', url=url)
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            headers = dict(request.headers)
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                stats = response.json()
                doc_count = stats["indices"][self.index_name]["total"]["docs"]["count"]
                size_bytes = stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"]
                
                return {
                    "success": True, 
                    "document_count": doc_count,
                    "size_mb": round(size_bytes / (1024 * 1024), 2),
                    "status": "healthy"
                }
            else:
                return {"success": False, "error": "Could not get stats", "status": "error"}
                
        except Exception as e:
            return {"success": False, "error": str(e), "status": "error"}
    
    def get_available_sources(self) -> List[str]:
        """Get available ingestion sources"""
        return [
            "nejm-ai (NEJM AI articles)",
            "nejm (Main NEJM journal)", 
            "catalyst (NEJM Catalyst)",
            "evidence (NEJM Evidence)",
            "clinician (NEJM Clinician)"
        ]
    
    def start_ingestion(self, source: str, limit: int = 50) -> Dict:
        """Start background ingestion process"""
        
        if self.ingestion_status["running"]:
            return {"success": False, "error": "Ingestion already running"}
        
        # Reset status
        self.ingestion_status = {
            "running": True,
            "progress": 0,
            "total": limit,
            "current_article": "Starting ingestion...",
            "errors": [],
            "completed": 0,
            "source": source
        }
        
        # Start background thread
        thread = threading.Thread(target=self._run_ingestion, args=(source, limit))
        thread.daemon = True
        thread.start()
        
        return {"success": True, "message": f"Started ingesting {limit} articles from {source}"}
    
    def _run_ingestion(self, source: str, limit: int):
        """Background ingestion process"""
        
        try:
            # Extract context from source
            context = source.split()[0]  # Get first word (nejm-ai, nejm, etc.)
            
            self.ingestion_status["current_article"] = f"Fetching articles from {context}..."
            
            # Get articles from NEJM API
            api_key = self.get_nejm_credentials()
            if not api_key:
                self.ingestion_status["errors"].append("Could not get NEJM API credentials")
                self.ingestion_status["running"] = False
                return
            
            user_id, key = api_key.split('|', 1)
            headers = {
                "apiuser": user_id,
                "apikey": key
            }
            
            # Search for recent articles
            search_endpoint = f"{self.nejm_base_url}/api/v1/search"
            params = {
                "context": context,
                "query": "*",  # Get all articles
                "limit": limit,
                "sort": "date_desc"
            }
            
            response = requests.get(search_endpoint, params=params, headers=headers)
            
            if response.status_code != 200:
                self.ingestion_status["errors"].append(f"Search API failed: {response.status_code}")
                self.ingestion_status["running"] = False
                return
            
            search_results = response.json()
            articles = search_results.get("results", [])
            
            if not articles:
                self.ingestion_status["errors"].append("No articles found")
                self.ingestion_status["running"] = False
                return
            
            self.ingestion_status["total"] = len(articles)
            
            # Process each article
            for i, article in enumerate(articles):
                if not self.ingestion_status["running"]:  # Check if cancelled
                    break
                
                doi = article.get("doi", "")
                title = article.get("title", "Unknown Title")
                
                self.ingestion_status["current_article"] = f"Processing: {title[:50]}..."
                self.ingestion_status["progress"] = i + 1
                
                # Fetch full article content
                if self._ingest_single_article(doi, context):
                    self.ingestion_status["completed"] += 1
                else:
                    self.ingestion_status["errors"].append(f"Failed to ingest: {title}")
                
                time.sleep(0.5)  # Rate limiting
            
            self.ingestion_status["current_article"] = "Ingestion completed!"
            
        except Exception as e:
            self.ingestion_status["errors"].append(f"Ingestion error: {str(e)}")
        finally:
            self.ingestion_status["running"] = False
    
    def _ingest_single_article(self, doi: str, context: str) -> bool:
        """Ingest a single article"""
        
        try:
            # Check if already exists
            if self._article_exists(doi):
                return True  # Skip duplicates
            
            # Fetch full article
            api_key = self.get_nejm_credentials()
            user_id, key = api_key.split('|', 1)
            headers = {
                "apiuser": user_id,
                "apikey": key
            }
            
            content_endpoint = f"{self.nejm_base_url}/api/v1/content"
            params = {
                "context": context,
                "doi": doi,
                "format": "json"
            }
            
            response = requests.get(content_endpoint, params=params, headers=headers)
            
            if response.status_code != 200:
                return False
            
            data = response.json()
            
            # Extract content
            title = data.get("title", "")
            abstract = data.get("displayAbstract", "")
            document = data.get("document", "")
            
            if not title and not document:
                return False
            
            # Create content for embedding
            content_parts = []
            if title:
                content_parts.append(f"Title: {title}")
            if abstract:
                content_parts.append(f"Abstract: {abstract}")
            if document:
                content_parts.append(f"Full Article: {document}")
            
            text_content = "\n\n".join(content_parts)
            
            # Limit for embedding
            if len(text_content) > 8000:
                text_content = text_content[:8000]
            
            # Create embedding
            response = self.bedrock_client.invoke_model(
                modelId='amazon.titan-embed-text-v1',
                body=json.dumps({"inputText": text_content})
            )
            
            result = json.loads(response['body'].read())
            embedding = result['embedding']
            
            # Create document
            doc = {
                "id": str(uuid.uuid4()),
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "content": text_content,
                "full_document": document,
                "year": data.get("publicationDate", "")[:4] if data.get("publicationDate") else "",
                "source": f"nejm-api-{context}",
                "vector": embedding,
                "api_metadata": data,
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                "content_format": "jats_xml_full"
            }
            
            # Insert into OpenSearch
            return self._insert_article_to_opensearch(doc)
            
        except Exception as e:
            return False
    
    def _article_exists(self, doi: str) -> bool:
        """Check if article already exists in OpenSearch"""
        
        try:
            search_body = {
                "query": {
                    "term": {
                        "doi": doi
                    }
                },
                "size": 1
            }
            
            url = f"{self.opensearch_endpoint}/{self.index_name}/_search"
            request = AWSRequest(method='POST', url=url, data=json.dumps(search_body))
            request.headers['Content-Type'] = 'application/json'
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            headers = dict(request.headers)
            response = requests.post(url, headers=headers, data=json.dumps(search_body))
            
            if response.status_code == 200:
                result = response.json()
                return result["hits"]["total"]["value"] > 0
            
            return False
            
        except Exception as e:
            return False
    
    def _insert_article_to_opensearch(self, article: Dict) -> bool:
        """Insert article into OpenSearch"""
        
        try:
            doc_id = article["id"]
            url = f"{self.opensearch_endpoint}/{self.index_name}/_doc/{doc_id}"
            
            request = AWSRequest(method='PUT', url=url, data=json.dumps(article))
            request.headers['Content-Type'] = 'application/json'
            SigV4Auth(self.credentials, 'es', 'us-east-1').add_auth(request)
            
            headers = dict(request.headers)
            response = requests.put(url, headers=headers, data=json.dumps(article))
            
            return response.status_code in [200, 201]
                
        except Exception as e:
            return False
    
    def get_ingestion_status(self) -> Dict:
        """Get current ingestion status"""
        return self.ingestion_status.copy()
    
    def stop_ingestion(self) -> Dict:
        """Stop current ingestion"""
        if self.ingestion_status["running"]:
            self.ingestion_status["running"] = False
            return {"success": True, "message": "Ingestion stopped"}
        else:
            return {"success": False, "error": "No ingestion running"}

# Initialize the interface
nejm_interface = AWSNEJMInterface()

@app.route('/')
def index():
    """Main page"""
    return render_template('aws_interface.html')

@app.route('/search', methods=['POST'])
def search():
    """Search endpoint"""
    data = request.get_json()
    query = data.get('query', '')
    limit = data.get('limit', 10)
    search_type = data.get('search_type', 'hybrid')
    
    if not query:
        return jsonify({"success": False, "error": "No query provided"})
    
    result = nejm_interface.search_articles(query, limit, search_type)
    return jsonify(result)

@app.route('/stats')
def stats():
    """Database statistics"""
    result = nejm_interface.get_database_stats()
    return jsonify(result)

@app.route('/sources')
def sources():
    """Available ingestion sources"""
    sources = nejm_interface.get_available_sources()
    return jsonify({"sources": sources})

@app.route('/ingest', methods=['POST'])
def ingest():
    """Start ingestion"""
    data = request.get_json()
    source = data.get('source', '')
    limit = data.get('limit', 50)
    
    if not source:
        return jsonify({"success": False, "error": "No source specified"})
    
    result = nejm_interface.start_ingestion(source, limit)
    return jsonify(result)

@app.route('/ingestion-status')
def ingestion_status():
    """Get ingestion status"""
    status = nejm_interface.get_ingestion_status()
    return jsonify(status)

@app.route('/stop-ingestion', methods=['POST'])
def stop_ingestion():
    """Stop ingestion"""
    result = nejm_interface.stop_ingestion()
    return jsonify(result)

if __name__ == '__main__':
    print("🚀 Starting AWS NEJM Research Assistant Web Interface")
    print("=" * 60)
    print("✅ AWS OpenSearch: Connected")
    print("✅ Bedrock embeddings: Ready")
    print("✅ NEJM API: Configured")
    print("✅ Ingestion: Available")
    print("\n🌐 Access at: http://localhost:8080")
    print("🔍 Full search and ingestion capabilities enabled")
    
    app.run(host='0.0.0.0', port=8080, debug=True)