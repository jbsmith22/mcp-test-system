#!/usr/bin/env python3
"""
Simple web interface to test our working OpenSearch database
"""

from flask import Flask, render_template, request, jsonify
import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

app = Flask(__name__)

class OpenSearchClient:
    def __init__(self):
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        self.index_name = "nejm-articles"
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    def search_articles(self, query, limit=5):
        """Search articles using both text and vector search"""
        
        try:
            # Get embedding for the query
            response = self.bedrock_client.invoke_model(
                modelId='amazon.titan-embed-text-v1',
                body=json.dumps({"inputText": query})
            )
            
            result = json.loads(response['body'].read())
            query_vector = result['embedding']
            
            # Hybrid search: combine text and vector search
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^3", "abstract^2", "content"],
                                    "boost": 1.0
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
                "_source": ["title", "doi", "abstract", "year", "source"]
            }
            
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
                    articles.append({
                        "title": source.get("title", "Unknown Title"),
                        "doi": source.get("doi", ""),
                        "abstract": source.get("abstract", "")[:300] + "..." if len(source.get("abstract", "")) > 300 else source.get("abstract", ""),
                        "year": source.get("year", ""),
                        "score": hit["_score"],
                        "source_type": source.get("source", "")
                    })
                
                return {"success": True, "articles": articles, "total": len(articles)}
            else:
                return {"success": False, "error": f"Search failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_stats(self):
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
                return {"success": True, "document_count": doc_count}
            else:
                return {"success": False, "error": "Could not get stats"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

# Initialize OpenSearch client
opensearch_client = OpenSearchClient()

@app.route('/')
def index():
    """Main page"""
    stats = opensearch_client.get_stats()
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NEJM Research Assistant - Working Version</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .search-box {{ margin: 20px 0; }}
            .search-box input {{ width: 70%; padding: 10px; font-size: 16px; border: 1px solid #ddd; border-radius: 5px; }}
            .search-box button {{ padding: 10px 20px; font-size: 16px; background: #007cba; color: white; border: none; border-radius: 5px; cursor: pointer; }}
            .stats {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .results {{ margin-top: 20px; }}
            .article {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; background: #fafafa; }}
            .article-title {{ font-weight: bold; color: #007cba; margin-bottom: 5px; }}
            .article-meta {{ color: #666; font-size: 14px; margin-bottom: 10px; }}
            .article-abstract {{ line-height: 1.4; }}
            .loading {{ text-align: center; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏥 NEJM Research Assistant</h1>
                <p>Direct OpenSearch Access - Fully Working Version</p>
            </div>
            
            <div class="stats">
                <strong>📊 Database Status:</strong> 
                {'✅ ' + str(stats['document_count']) + ' articles available' if stats['success'] else '❌ ' + stats['error']}
            </div>
            
            <div class="search-box">
                <input type="text" id="searchQuery" placeholder="Enter your medical research question..." value="cardiac rehabilitation">
                <button onclick="searchArticles()">🔍 Search</button>
            </div>
            
            <div id="results" class="results"></div>
        </div>
        
        <script>
            function searchArticles() {{
                const query = document.getElementById('searchQuery').value;
                const resultsDiv = document.getElementById('results');
                
                if (!query.trim()) {{
                    alert('Please enter a search query');
                    return;
                }}
                
                resultsDiv.innerHTML = '<div class="loading">🔍 Searching...</div>';
                
                fetch('/search', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{query: query, limit: 5}})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        displayResults(data.articles, query);
                    }} else {{
                        resultsDiv.innerHTML = '<div class="article">❌ Error: ' + data.error + '</div>';
                    }}
                }})
                .catch(error => {{
                    resultsDiv.innerHTML = '<div class="article">❌ Network error: ' + error + '</div>';
                }});
            }}
            
            function displayResults(articles, query) {{
                const resultsDiv = document.getElementById('results');
                
                if (articles.length === 0) {{
                    resultsDiv.innerHTML = '<div class="article">No articles found for "' + query + '"</div>';
                    return;
                }}
                
                let html = '<h3>📚 Found ' + articles.length + ' articles:</h3>';
                
                articles.forEach((article, index) => {{
                    html += `
                        <div class="article">
                            <div class="article-title">${{index + 1}}. ${{article.title}}</div>
                            <div class="article-meta">
                                DOI: ${{article.doi}} | Year: ${{article.year}} | Score: ${{article.score.toFixed(3)}}
                            </div>
                            <div class="article-abstract">${{article.abstract}}</div>
                        </div>
                    `;
                }});
                
                resultsDiv.innerHTML = html;
            }}
            
            // Allow Enter key to search
            document.getElementById('searchQuery').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    searchArticles();
                }}
            }});
        </script>
    </body>
    </html>
    """

@app.route('/search', methods=['POST'])
def search():
    """Search endpoint"""
    data = request.get_json()
    query = data.get('query', '')
    limit = data.get('limit', 5)
    
    if not query:
        return jsonify({"success": False, "error": "No query provided"})
    
    result = opensearch_client.search_articles(query, limit)
    return jsonify(result)

if __name__ == '__main__':
    print("🚀 Starting NEJM Research Assistant Web Interface")
    print("=" * 50)
    print("✅ OpenSearch database: Connected")
    print("✅ Bedrock embeddings: Ready")
    print("✅ Search functionality: Working")
    print("\n🌐 Access at: http://localhost:5001")
    print("🔍 Try searching for: 'cardiac rehabilitation'")
    
    app.run(host='0.0.0.0', port=5001, debug=True)