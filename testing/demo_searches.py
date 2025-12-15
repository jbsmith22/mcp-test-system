#!/usr/bin/env python3
"""
Demo searches to show off your NEJM database capabilities
"""

from nejm_search_cli import NEJMSearchCLI, print_results

def run_demo_searches():
    """Run several demo searches to showcase the database"""
    
    searcher = NEJMSearchCLI()
    
    print("🏥 NEJM Research Database - Demo Searches")
    print("=" * 60)
    
    # Get database stats
    stats = searcher.get_database_stats()
    if stats["success"]:
        print(f"📊 Database: {stats['document_count']} articles ({stats['size_mb']} MB)")
    
    # Demo searches
    demo_queries = [
        "artificial intelligence machine learning",
        "cancer treatment immunotherapy",
        "diabetes management glucose",
        "heart failure treatment",
        "COVID-19 vaccine effectiveness"
    ]
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'='*60}")
        print(f"Demo Search {i}: '{query}'")
        print(f"{'='*60}")
        
        results = searcher.search_articles(query, limit=3, search_type="hybrid")
        
        if results["success"]:
            articles = results["articles"]
            print(f"Found {len(articles)} articles:")
            
            for j, article in enumerate(articles, 1):
                print(f"\n{j}. {article['title']}")
                print(f"   DOI: {article['doi']}")
                print(f"   Score: {article['score']:.2f}")
                print(f"   Abstract: {article['abstract'][:150]}...")
        else:
            print(f"❌ Search failed: {results['error']}")
    
    print(f"\n{'='*60}")
    print("🎉 Your NEJM research database is fully operational!")
    print("💡 Use 'python nejm_search_cli.py' for interactive searching")
    print("💡 Or 'python nejm_search_cli.py \"your query\"' for direct search")

if __name__ == "__main__":
    run_demo_searches()