#!/usr/bin/env python3
"""
Secure configuration management for NEJM API
"""

import os
import json
from pathlib import Path
from typing import Optional

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / '.nejm_api'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(exist_ok=True)
        
        # Set restrictive permissions on config directory
        os.chmod(self.config_dir, 0o700)
    
    def save_api_key(self, api_key: str, environment: str = "qa"):
        """Securely save API key to config file"""
        config = self.load_config()
        config['api_keys'] = config.get('api_keys', {})
        config['api_keys'][environment] = api_key
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Set restrictive permissions on config file
        os.chmod(self.config_file, 0o600)
        print(f"✅ API key saved for {environment} environment")
    
    def get_api_key(self, environment: str = "qa") -> Optional[str]:
        """Get API key from config file or environment variable"""
        # First try environment variable
        env_var = f"NEJM_API_KEY_{environment.upper()}" if environment != "qa" else "NEJM_API_KEY"
        api_key = os.getenv(env_var)
        
        if api_key:
            return api_key
        
        # Then try config file
        config = self.load_config()
        return config.get('api_keys', {}).get(environment)
    
    def load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def list_environments(self):
        """List configured environments"""
        config = self.load_config()
        api_keys = config.get('api_keys', {})
        
        if not api_keys:
            print("No API keys configured")
            return
        
        print("Configured environments:")
        for env in api_keys.keys():
            print(f"  - {env}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage NEJM API configuration")
    parser.add_argument("--set-key", help="Set API key for environment")
    parser.add_argument("--environment", default="qa", help="Environment (qa/production)")
    parser.add_argument("--list", action="store_true", help="List configured environments")
    
    args = parser.parse_args()
    
    config = ConfigManager()
    
    if args.list:
        config.list_environments()
    elif args.set_key:
        config.save_api_key(args.set_key, args.environment)
    else:
        print("Usage examples:")
        print("  python config_manager.py --set-key 'your-api-key' --environment qa")
        print("  python config_manager.py --list")

if __name__ == "__main__":
    main()