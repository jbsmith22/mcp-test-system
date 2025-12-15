#!/usr/bin/env python3
"""
Automated ingestion pipeline for NEJM articles
Can be run as a cron job or scheduled task
"""

import os
import sys
import json
import logging
from datetime import datetime
from nejm_api_client import NEJMAPIClient
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nejm_ingestion.log'),
        logging.StreamHandler()
    ]
)

class AutomatedIngestion:
    def __init__(self, api_key: str, environment: str = "qa"):
        base_url = "https://onesearch-api.nejmgroup-qa.org" if environment == "qa" else "https://onesearch-api.nejmgroup-production.org"
        self.client = NEJMAPIClient(base_url)
        # NEJM API uses two headers: apiuser and apikey
        if '|' in api_key:
            user_id, key = api_key.split('|', 1)
            self.client.session.headers.update({
                "apiuser": user_id,
                "apikey": key
            })
        else:
            raise ValueError("API key format should be: userid|apikey")
        self.stats_file = "ingestion_stats.json"
        
    def load_stats(self) -> dict:
        """Load ingestion statistics"""
        if os.path.exists(self.stats_file):
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {
            "last_run": None,
            "total_ingested": 0,
            "runs": []
        }
    
    def save_stats(self, stats: dict):
        """Save ingestion statistics"""
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def run_ingestion(self, contexts: list = ["nejm"], articles_per_context: int = 10):
        """Run automated ingestion for specified contexts"""
        stats = self.load_stats()
        run_start = datetime.now()
        
        logging.info(f"Starting automated ingestion at {run_start}")
        logging.info(f"Contexts: {contexts}, Articles per context: {articles_per_context}")
        
        total_success = 0
        total_attempted = 0
        
        for context in contexts:
            logging.info(f"Processing context: {context}")
            
            try:
                # Fetch recent articles
                articles = self.client.get_recent_articles(articles_per_context, context)
                
                if not articles:
                    logging.warning(f"No articles found for context: {context}")
                    continue
                
                logging.info(f"Found {len(articles)} articles in {context}")
                
                # Process each article
                for i, article in enumerate(articles, 1):
                    total_attempted += 1
                    metadata = self.client.extract_article_metadata(article)
                    
                    logging.info(f"Processing {i}/{len(articles)}: {metadata.get('title', 'Unknown')[:50]}...")
                    
                    if self.client.ingest_article(article, context):
                        total_success += 1
                        logging.info(f"✅ Successfully ingested article {i}")
                    else:
                        logging.error(f"❌ Failed to ingest article {i}")
                        
            except Exception as e:
                logging.error(f"Error processing context {context}: {e}")
        
        # Update statistics
        run_end = datetime.now()
        duration = (run_end - run_start).total_seconds()
        
        run_stats = {
            "timestamp": run_start.isoformat(),
            "duration_seconds": duration,
            "contexts": contexts,
            "articles_per_context": articles_per_context,
            "attempted": total_attempted,
            "successful": total_success,
            "success_rate": total_success / total_attempted if total_attempted > 0 else 0
        }
        
        stats["last_run"] = run_start.isoformat()
        stats["total_ingested"] += total_success
        stats["runs"].append(run_stats)
        
        # Keep only last 50 runs
        stats["runs"] = stats["runs"][-50:]
        
        self.save_stats(stats)
        
        logging.info(f"Ingestion completed in {duration:.1f}s")
        logging.info(f"Success rate: {total_success}/{total_attempted} ({run_stats['success_rate']:.1%})")
        
        return run_stats

def main():
    # Configuration
    ENVIRONMENT = os.getenv("NEJM_ENVIRONMENT", "qa")  # Default to QA
    
    # Get API key from multiple sources
    config = ConfigManager()
    API_KEY = config.get_api_key(ENVIRONMENT)
    
    if not API_KEY:
        print(f"❌ Error: No API key found for {ENVIRONMENT} environment")
        print("Options:")
        print(f"1. Set environment variable: export NEJM_API_KEY='your-key'")
        print(f"2. Save to config: python config_manager.py --set-key 'your-key' --environment {ENVIRONMENT}")
        sys.exit(1)
    
    # Default configuration - adjust as needed
    CONTEXTS = ["nejm", "catalyst", "evidence"]  # Which journals to monitor
    ARTICLES_PER_CONTEXT = 5  # How many recent articles per journal
    
    # Override from command line if provided
    if len(sys.argv) > 1:
        ARTICLES_PER_CONTEXT = int(sys.argv[1])
    
    print(f"Using {ENVIRONMENT.upper()} environment")
    
    # Run ingestion
    ingestion = AutomatedIngestion(API_KEY, ENVIRONMENT)
    
    try:
        stats = ingestion.run_ingestion(CONTEXTS, ARTICLES_PER_CONTEXT)
        
        if stats['successful'] > 0:
            print(f"✅ Successfully ingested {stats['successful']} articles")
        else:
            print("⚠️  No articles were ingested")
            
    except Exception as e:
        logging.error(f"Fatal error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()