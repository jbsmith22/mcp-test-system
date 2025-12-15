#!/usr/bin/env python3
"""
Command-line interface for searching NEJM articles in AWS OpenSearch
"""

import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import sys

class NEJMSearchCLI:
    def __init__(self):
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.opensearch_endpoint = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
        self.index_name = "nejm-articles"
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    def search_articles(self, query, limit=5, search_type="hybrid"):
        """Search articles using text, vector, or hybrid search"""
        
        try:
            if search_type == "vector":
                return self._vector_search(query, limit)
            elif search_type == "text":
                return self._text_search(query, limit)
            else:  # hybrid
                return self._hybrid_search(query, limit)
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _text_search(self, query, limit):
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
            "_source": ["title", "doi", "abstract", "year", "source"],
            "highlight": {
                "fields": {
                    "title": {},
                    "abstract": {"fragment_size": 150}
                }
            }
        }
        
        return self._execute_search(search_body)
    
    def _vector_search(self, query, limit):
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
            "_source": ["title", "doi", "abstract", "year", "source"]
        }
        
        return self._execute_search(search_body)
    
    def _hybrid_search(self, query, limit):
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
            "_source": ["title", "doi", "abstract", "year", "source"],
            "highlight": {
                "fields": {
                    "title": {},
                    "abstract": {"fragment_size": 150}
                }
            }
        }
        
        return self._execute_search(search_body)
    
    def _execute_search(self, search_body):
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
                highlighted_abstract = highlights.get("abstract", [source.get("abstract", "")[:200] + "..."])[0]
                
                articles.append({
                    "title": source.get("title", "Unknown Title"),
                    "doi": source.get("doi", ""),
                    "abstract": highlighted_abstract,
                    "year": source.get("year", ""),
                    "score": hit["_score"],
                    "source_type": source.get("source", "")
                })
            
            return {
                "success": True, 
                "articles": articles, 
                "total": result["hits"]["total"]["value"],
                "query": search_body["query"]
            }
        else:
            return {"success": False, "error": f"Search failed: {response.status_code}"}
    
    def get_database_stats(self):
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
                    "size_mb": round(size_bytes / (1024 * 1024), 2)
                }
            else:
                return {"success": False, "error": "Could not get stats"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

def print_results(results, query):
    """Print search results in a nice format"""
    
    if not results["success"]:
        print(f"❌ Search failed: {results['error']}")
        return
    
    articles = results["articles"]
    total = results.get("total", len(articles))
    
    print(f"\n🔍 Search Results for: '{query}'")
    print(f"📊 Found {len(articles)} articles (total: {total})")
    print("=" * 80)
    
    if not articles:
        print("No articles found. Try different keywords.")
        return
    
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title']}")
        print(f"   📄 DOI: {article['doi']}")
        print(f"   📅 Year: {article['year']} | 📊 Score: {article['score']:.2f}")
        print(f"   📝 {article['abstract']}")
        if i < len(articles):
            print("-" * 80)

def interactive_search():
    """Interactive search interface"""
    
    searcher = NEJMSearchCLI()
    
    print("🏥 NEJM Research Assistant - Command Line Interface")
    print("=" * 60)
    
    # Show database stats
    stats = searcher.get_database_stats()
    if stats["success"]:
        print(f"📊 Database: {stats['document_count']} articles ({stats['size_mb']} MB)")
    else:
        print(f"⚠️ Database status: {stats['error']}")
    
    print("\n💡 Search Types:")
    print("   • Just type your query for hybrid search (recommended)")
    print("   • Add --text for text-only search")
    print("   • Add --vector for semantic-only search")
    print("   • Type 'quit' to exit")
    
    while True:
        print("\n" + "=" * 60)
        query = input("🔍 Enter your medical research question: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not query:
            continue
        
        # Parse search type
        search_type = "hybrid"
        if query.endswith(" --text"):
            search_type = "text"
            query = query[:-7].strip()
        elif query.endswith(" --vector"):
            search_type = "vector"
            query = query[:-9].strip()
        
        print(f"⏳ Searching ({search_type})...")
        
        results = searcher.search_articles(query, limit=5, search_type=search_type)
        print_results(results, query)

def main():
    if len(sys.argv) > 1:
        # Command line search
        query = " ".join(sys.argv[1:])
        
        searcher = NEJMSearchCLI()
        results = searcher.search_articles(query, limit=5)
        print_results(results, query)
    else:
        # Interactive mode
        interactive_search()

if __name__ == "__main__":
    main()