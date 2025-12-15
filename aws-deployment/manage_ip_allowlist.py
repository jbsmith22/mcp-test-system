#!/usr/bin/env python3
"""
Manage IP allowlist for NEJM Research Assistant
"""

import boto3
import json
import sys
import requests

def get_current_ip():
    """Get the current public IP address"""
    try:
        response = requests.get('https://ipinfo.io/ip', timeout=10)
        return response.text.strip()
    except:
        try:
            response = requests.get('https://api.ipify.org', timeout=10)
            return response.text.strip()
        except:
            return None

def get_current_allowed_ips():
    """Get currently allowed IPs from all services"""
    
    try:
        # Get from Lambda (most reliable source)
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function_configuration(FunctionName='nejm-research-assistant')
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        allowed_ips_str = env_vars.get('ALLOWED_IPS', '')
        if allowed_ips_str:
            return [ip.strip() for ip in allowed_ips_str.split(',') if ip.strip()]
        else:
            return []
            
    except Exception as e:
        print(f"❌ Error getting current IPs: {e}")
        return []

def update_all_services(allowed_ips):
    """Update IP allowlist across all services"""
    
    success_count = 0
    
    # Convert single IP to list
    if isinstance(allowed_ips, str):
        allowed_ips = [allowed_ips]
    
    # Remove duplicates and empty strings
    allowed_ips = list(set([ip.strip() for ip in allowed_ips if ip.strip()]))
    
    print(f"🔄 Updating IP allowlist: {', '.join(allowed_ips)}")
    
    # 1. Update S3 bucket policy
    try:
        from implement_ip_security import apply_s3_security
        if apply_s3_security('nejm-research-web-interface', allowed_ips):
            success_count += 1
    except Exception as e:
        print(f"❌ S3 update failed: {e}")
    
    # 2. Update API Gateway policy
    try:
        from implement_ip_security import apply_api_gateway_security
        if apply_api_gateway_security('lwi6jeeczi', allowed_ips):
            success_count += 1
    except Exception as e:
        print(f"❌ API Gateway update failed: {e}")
    
    # 3. Update Lambda environment
    try:
        from implement_ip_security import update_lambda_ip_validation
        if update_lambda_ip_validation('nejm-research-assistant', allowed_ips):
            success_count += 1
    except Exception as e:
        print(f"❌ Lambda update failed: {e}")
    
    return success_count == 3

def add_ip(new_ip):
    """Add an IP to the allowlist"""
    
    print(f"➕ Adding IP to allowlist: {new_ip}")
    
    # Get current IPs
    current_ips = get_current_allowed_ips()
    
    # Add new IP if not already present
    if new_ip not in current_ips:
        current_ips.append(new_ip)
        print(f"   Added {new_ip} to allowlist")
    else:
        print(f"   IP {new_ip} already in allowlist")
    
    # Update all services
    if update_all_services(current_ips):
        print(f"✅ Successfully added {new_ip} to all services")
        return True
    else:
        print(f"❌ Failed to add {new_ip} to some services")
        return False

def remove_ip(remove_ip):
    """Remove an IP from the allowlist"""
    
    print(f"➖ Removing IP from allowlist: {remove_ip}")
    
    # Get current IPs
    current_ips = get_current_allowed_ips()
    
    # Remove IP if present
    if remove_ip in current_ips:
        current_ips.remove(remove_ip)
        print(f"   Removed {remove_ip} from allowlist")
    else:
        print(f"   IP {remove_ip} not found in allowlist")
        return True  # Not an error if IP wasn't there
    
    # Ensure at least one IP remains
    if not current_ips:
        current_ip = get_current_ip()
        if current_ip:
            current_ips = [current_ip]
            print(f"   Added current IP {current_ip} to prevent lockout")
        else:
            print(f"❌ Cannot remove last IP - would cause lockout")
            return False
    
    # Update all services
    if update_all_services(current_ips):
        print(f"✅ Successfully removed {remove_ip} from all services")
        return True
    else:
        print(f"❌ Failed to remove {remove_ip} from some services")
        return False

def list_ips():
    """List all currently allowed IPs"""
    
    print("📋 Current IP Allowlist:")
    
    # Get security status from all services
    try:
        from implement_ip_security import get_security_status
        status = get_security_status()
        
        if status:
            current_ip = get_current_ip()
            
            print(f"\n🌐 Your current IP: {current_ip}")
            print(f"\n🔒 Security Status by Service:")
            
            for service, config in status.items():
                secured_status = "🔒 SECURED" if config['secured'] else "🔓 OPEN"
                print(f"\n   {service.upper()}: {secured_status}")
                
                if config['ips']:
                    for i, ip in enumerate(config['ips'], 1):
                        is_current = " (current)" if ip == current_ip else ""
                        print(f"      {i}. {ip}{is_current}")
                else:
                    print(f"      No IP restrictions")
            
            # Show unified allowlist
            all_ips = set()
            for config in status.values():
                all_ips.update(config['ips'])
            
            if all_ips:
                print(f"\n📊 Unified Allowlist ({len(all_ips)} IPs):")
                for i, ip in enumerate(sorted(all_ips), 1):
                    is_current = " (current)" if ip == current_ip else ""
                    print(f"   {i}. {ip}{is_current}")
            
        else:
            print("❌ Could not retrieve security status")
            
    except Exception as e:
        print(f"❌ Error listing IPs: {e}")

def show_usage():
    """Show usage instructions"""
    
    print("🔐 NEJM Research Assistant - IP Allowlist Management")
    print("=" * 55)
    print()
    print("Usage:")
    print("  python manage_ip_allowlist.py list                    # List current IPs")
    print("  python manage_ip_allowlist.py add <ip_address>        # Add an IP")
    print("  python manage_ip_allowlist.py remove <ip_address>     # Remove an IP")
    print("  python manage_ip_allowlist.py add-current             # Add current IP")
    print()
    print("Examples:")
    print("  python manage_ip_allowlist.py list")
    print("  python manage_ip_allowlist.py add 192.168.1.100")
    print("  python manage_ip_allowlist.py remove 192.168.1.100")
    print("  python manage_ip_allowlist.py add-current")
    print()

def main():
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_ips()
        
    elif command == 'add':
        if len(sys.argv) < 3:
            print("❌ Error: Please specify an IP address to add")
            print("Usage: python manage_ip_allowlist.py add <ip_address>")
            return
        
        ip_to_add = sys.argv[2]
        add_ip(ip_to_add)
        
    elif command == 'add-current':
        current_ip = get_current_ip()
        if current_ip:
            add_ip(current_ip)
        else:
            print("❌ Could not determine current IP address")
            
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("❌ Error: Please specify an IP address to remove")
            print("Usage: python manage_ip_allowlist.py remove <ip_address>")
            return
        
        ip_to_remove = sys.argv[2]
        remove_ip(ip_to_remove)
        
    else:
        print(f"❌ Unknown command: {command}")
        show_usage()

if __name__ == "__main__":
    main()