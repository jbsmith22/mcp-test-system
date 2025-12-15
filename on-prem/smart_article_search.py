#!/usr/bin/env python3
"""
Smart Article Search - The best way to get clean, readable articles
Combines semantic search with clean JATS XML retrieval from NEJM API
"""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Smart article search with clean content")
    parser.add_argument("query", nargs='?', help="Your search question")
    parser.add_argument("--save", "-s", help="Save clean article to file")
    parser.add_argument("--summary", action="store_true", help="Show only summary, not full text")
    
    args = parser.parse_args()
    
    query = args.query
    if not query:
        query = input("🤔 What would you like to search for? ").strip()
        if not query:
            print("❌ No query provided")
            return
    
    print("🔍 Smart Article Search")
    print("=" * 50)
    print("✨ Getting clean, readable content from NEJM API...")
    print()
    
    try:
        from clean_article_retriever import CleanArticleRetriever
        
        retriever = CleanArticleRetriever()
        clean_content = retriever.search_and_get_clean_article(query)
        
        if clean_content:
            if args.summary:
                # Show just the header part
                lines = clean_content.split('\n')
                header_end = 0
                for i, line in enumerate(lines):
                    if line.startswith('ABSTRACT'):
                        header_end = i
                        break
                
                summary_content = '\n'.join(lines[:header_end])
                print(summary_content)
                print("\n💡 Use without --summary to see full article content")
            else:
                print(clean_content)
            
            if args.save:
                with open(args.save, 'w', encoding='utf-8') as f:
                    f.write(clean_content)
                print(f"\n💾 Clean article saved to: {args.save}")
            
            print(f"\n✨ This clean format is much better than messy chunked text!")
            print(f"🎯 Perfect for reading, analysis, and research!")
            
        else:
            print("❌ Could not retrieve clean article content")
            print("💡 Try a different search query or check your API credentials")
            
    except ImportError:
        print("❌ Clean article retriever not available")
        print("💡 Make sure clean_article_retriever.py is in the same directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()