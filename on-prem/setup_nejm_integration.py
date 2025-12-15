#!/usr/bin/env python3
"""
Setup script for NEJM API integration
"""

import os
import subprocess
import sys

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    # Check if we're in the right virtual environment
    try:
        result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        print(f"✅ Python: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Python check failed: {e}")
        return False
    
    # Check required packages
    required_packages = ["requests", "pypdf"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: installed")
        except ImportError:
            print(f"❌ {package}: missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Install missing packages:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_services():
    """Check if Qdrant and Ollama are running"""
    print("\n🔍 Checking services...")
    
    # Check Qdrant
    try:
        result = subprocess.run(["curl", "-s", "http://127.0.0.1:6333/healthz"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Qdrant: running")
        else:
            print("❌ Qdrant: not responding")
            return False
    except Exception as e:
        print(f"❌ Qdrant: error checking - {e}")
        return False
    
    # Check Ollama
    try:
        result = subprocess.run(["curl", "-s", "http://127.0.0.1:11434/api/tags"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ollama: running")
        else:
            print("❌ Ollama: not responding")
            return False
    except Exception as e:
        print(f"❌ Ollama: error checking - {e}")
        return False
    
    return True

def show_next_steps():
    """Show what to do next"""
    print("\n🚀 Next Steps:")
    print("=" * 50)
    
    print("\n1. Get NEJM API Key:")
    print("   - Contact NEJM to obtain API access")
    print("   - Set environment variable: export NEJM_API_KEY='your-key'")
    
    print("\n2. Test the integration:")
    print("   python test_nejm_api.py")
    
    print("\n3. Test with your API key (QA environment):")
    print("   python nejm_api_client.py --api-key YOUR_KEY --dry-run --limit 3")
    
    print("\n4. Start ingesting articles (QA):")
    print("   python nejm_api_client.py --api-key YOUR_KEY --limit 10")
    
    print("\n5. Use production environment:")
    print("   python nejm_api_client.py --api-key YOUR_KEY --environment production --limit 10")
    
    print("\n6. Set up automation (optional):")
    print("   export NEJM_API_KEY='your-key'")
    print("   python automated_ingestion.py  # Uses QA by default")
    
    print("\n7. Compare environments:")
    print("   python compare_environments.py")
    
    print("\n8. Schedule regular ingestion:")
    print("   # Add to crontab for daily ingestion at 6 AM:")
    print("   # 0 6 * * * cd /path/to/project && python automated_ingestion.py")

def main():
    print("🔧 NEJM API Integration Setup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return False
    
    # Check services
    if not check_services():
        print("\n❌ Please start required services first")
        print("Start Qdrant: docker start qdrant")
        print("Start Ollama: ollama serve")
        return False
    
    print("\n✅ All checks passed!")
    show_next_steps()
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)