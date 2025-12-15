#!/usr/bin/env python3
"""
Demonstrate IP security management for NEJM Research Assistant
"""

import subprocess
import sys

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🔐 NEJM Research Assistant - Security Demo")
    print("=" * 50)
    
    # Show current status
    print("\n1️⃣ Current Security Status:")
    success, output, error = run_command("python3 manage_ip_allowlist.py list")
    if success:
        print(output)
    else:
        print(f"❌ Error: {error}")
    
    # Show how to add an IP
    print("\n2️⃣ How to Add Additional IPs:")
    print("To add a new IP address (e.g., office, home, colleague):")
    print("   python3 manage_ip_allowlist.py add 192.168.1.100")
    print("   python3 manage_ip_allowlist.py add 10.0.0.50")
    print("   python3 manage_ip_allowlist.py add-current  # Add your current IP")
    
    print("\n3️⃣ How to Remove IPs:")
    print("To remove an IP address:")
    print("   python3 manage_ip_allowlist.py remove 192.168.1.100")
    
    print("\n4️⃣ Security Features Active:")
    print("✅ S3 Website: Only allowed IPs can access")
    print("✅ API Gateway: IP + API key authentication")
    print("✅ Lambda Function: IP validation as backup")
    print("✅ Web Interface: Shows security status in real-time")
    
    print("\n5️⃣ Test Your Security:")
    print("🌐 Visit: http://nejm-research-web-interface.s3-website-us-east-1.amazonaws.com")
    print("🔍 Check the 'Security Status' tile in the sidebar")
    print("📱 Try accessing from a different network (should be blocked)")
    
    print("\n6️⃣ Emergency Access:")
    print("If you get locked out, run from an authorized location:")
    print("   python3 manage_ip_allowlist.py add-current")
    
    print(f"\n🎯 Your system is now secured and ready for controlled access!")

if __name__ == "__main__":
    main()