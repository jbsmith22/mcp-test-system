#!/usr/bin/env python3
"""
Interactive setup wizard for NEJM API integration
"""

import os
import sys
import getpass
from config_manager import ConfigManager

def welcome():
    print("🚀 NEJM API Integration Setup Wizard")
    print("=" * 50)
    print("This wizard will help you securely configure your API keys.")
    print()

def get_api_credentials_securely():
    """Get user ID and API key"""
    print("📋 NEJM API Credentials Setup")
    print("-" * 30)
    print("NEJM API requires both a User ID and API Key.")
    print()
    
    try:
        user_id = input("User ID: ").strip()
        if not user_id:
            print("❌ No User ID entered")
            return None
        
        print("(API Key will be hidden as you type for security)")
        api_key = getpass.getpass("API Key: ").strip()
        if not api_key:
            print("❌ No API key entered")
            return None
            
        # Combine into single credential string
        return f"{user_id}|{api_key}"
        
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled")
        return None

def choose_environment():
    """Let user choose environment"""
    print("\n🌍 Environment Selection")
    print("-" * 25)
    print("1. QA Environment (recommended for testing)")
    print("2. Production Environment")
    print("3. Both")
    
    while True:
        choice = input("\nChoose environment (1/2/3): ").strip()
        if choice == "1":
            return ["qa"]
        elif choice == "2":
            return ["production"]
        elif choice == "3":
            return ["qa", "production"]
        else:
            print("Please enter 1, 2, or 3")

def test_api_key(api_key, environment):
    """Test if API key works"""
    print(f"\n🧪 Testing API key for {environment} environment...")
    
    try:
        from nejm_api_client import NEJMAPIClient
        
        base_url = "https://onesearch-api.nejmgroup-qa.org" if environment == "qa" else "https://onesearch-api.nejmgroup-production.org"
        client = NEJMAPIClient(base_url)
        # NEJM API uses two headers: apiuser and apikey
        if '|' in api_key:
            user_id, key = api_key.split('|', 1)
            client.session.headers.update({
                "apiuser": user_id,
                "apikey": key
            })
        else:
            print("❌ API key format should be: userid|apikey")
            return False
        
        # Try to fetch 1 article
        articles = client.get_recent_articles(limit=1, context="nejm")
        
        if articles:
            print(f"✅ API key works! Found {len(articles)} article(s)")
            return True
        else:
            print("⚠️  API key accepted but no articles returned")
            return True  # Still valid, might be empty result
            
    except Exception as e:
        print(f"❌ API key test failed: {e}")
        return False

def main():
    welcome()
    
    # Get API credentials
    credentials = get_api_credentials_securely()
    if not credentials:
        sys.exit(1)
    
    # Choose environments
    environments = choose_environment()
    
    # Setup config manager
    config = ConfigManager()
    
    # Test and save for each environment
    success_count = 0
    for env in environments:
        if test_api_key(credentials, env):
            config.save_api_key(credentials, env)
            success_count += 1
        else:
            print(f"❌ Skipping {env} environment due to test failure")
    
    # Summary
    print(f"\n📊 Setup Summary")
    print("=" * 20)
    
    if success_count > 0:
        print(f"✅ Successfully configured {success_count} environment(s)")
        print("\n🎯 Next Steps:")
        print("1. Test your setup:")
        print("   python nejm_api_client.py --dry-run --limit 3")
        print("\n2. Start ingesting articles:")
        print("   python nejm_api_client.py --limit 10")
        print("\n3. Set up automation:")
        print("   python automated_ingestion.py")
    else:
        print("❌ No environments were configured successfully")
        print("Please check your API key and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()