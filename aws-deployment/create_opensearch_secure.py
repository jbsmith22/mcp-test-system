#!/usr/bin/env python3
"""
Secure OpenSearch Domain Creation
Creates OpenSearch domain with proper security configurations
"""

import boto3
import json
import time
from datetime import datetime

def create_secure_opensearch():
    """Create OpenSearch domain with security best practices"""
    
    print("🔒 Creating Secure OpenSearch Domain")
    print("=" * 40)
    
    # Initialize AWS clients
    opensearch_client = boto3.client('opensearch', region_name='us-east-1')
    sts_client = boto3.client('sts', region_name='us-east-1')
    
    # Get account ID
    account_id = sts_client.get_caller_identity()['Account']
    print(f"📋 AWS Account ID: {account_id}")
    
    # Your current IP (from previous check)
    your_ip = "108.20.28.24"
    print(f"🌐 Your IP Address: {your_ip}")
    
    # Create secure access policy
    access_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::{account_id}:root"
                },
                "Action": "es:*",
                "Resource": f"arn:aws:es:us-east-1:{account_id}:domain/nejm-research/*",
                "Condition": {
                    "IpAddress": {
                        "aws:sourceIp": [f"{your_ip}/32"]
                    }
                }
            }
        ]
    }
    
    print("🛡️ Access Policy Created:")
    print(f"   - Only allows access from IP: {your_ip}")
    print(f"   - Only allows your AWS account: {account_id}")
    
    # Domain configuration
    domain_config = {
        'DomainName': 'nejm-research',
        'EngineVersion': 'OpenSearch_2.11',
        'ClusterConfig': {
            'InstanceType': 't3.small.search',
            'InstanceCount': 1,
            'DedicatedMasterEnabled': False
        },
        'EBSOptions': {
            'EBSEnabled': True,
            'VolumeType': 'gp3',
            'VolumeSize': 20
        },
        'AccessPolicies': json.dumps(access_policy),
        'DomainEndpointOptions': {
            'EnforceHTTPS': True,
            'TLSSecurityPolicy': 'Policy-Min-TLS-1-2-2019-07'
        },
        'NodeToNodeEncryptionOptions': {
            'Enabled': True
        },
        'EncryptionAtRestOptions': {
            'Enabled': True
        },
        'AdvancedSecurityOptions': {
            'Enabled': False  # We're using IAM + IP restrictions instead
        },
        'TagList': [
            {'Key': 'Project', 'Value': 'NEJM-Research'},
            {'Key': 'Environment', 'Value': 'Development'},
            {'Key': 'Security', 'Value': 'IP-Restricted'},
            {'Key': 'Owner', 'Value': 'jbsmith22'}
        ]
    }
    
    print("\n🔧 Domain Configuration:")
    print(f"   - Instance Type: {domain_config['ClusterConfig']['InstanceType']}")
    print(f"   - Storage: {domain_config['EBSOptions']['VolumeSize']}GB GP3")
    print(f"   - HTTPS Enforced: {domain_config['DomainEndpointOptions']['EnforceHTTPS']}")
    print(f"   - Encryption at Rest: {domain_config['EncryptionAtRestOptions']['Enabled']}")
    print(f"   - Node-to-Node Encryption: {domain_config['NodeToNodeEncryptionOptions']['Enabled']}")
    
    # Check if domain already exists
    try:
        existing_domain = opensearch_client.describe_domain(DomainName='nejm-research')
        print("\n⚠️  Domain 'nejm-research' already exists!")
        print(f"   Status: {existing_domain['DomainStatus']['Processing']}")
        
        if existing_domain['DomainStatus']['Processing']:
            print("   Domain is still being created/updated...")
        else:
            print("   Domain is active")
            endpoint = existing_domain['DomainStatus'].get('Endpoint')
            if endpoint:
                print(f"   Endpoint: https://{endpoint}")
        
        return existing_domain['DomainStatus']
        
    except opensearch_client.exceptions.ResourceNotFoundException:
        print("\n✅ Domain doesn't exist yet, creating new one...")
    
    # Create the domain
    try:
        print("\n🚀 Creating OpenSearch domain...")
        response = opensearch_client.create_domain(**domain_config)
        
        domain_status = response['DomainStatus']
        
        print("✅ Domain creation initiated successfully!")
        print(f"   Domain ARN: {domain_status['ARN']}")
        print(f"   Domain ID: {domain_status['DomainId']}")
        print(f"   Created: {domain_status['Created']}")
        
        print("\n⏳ Domain Status:")
        print(f"   Processing: {domain_status['Processing']}")
        print(f"   Upgrade Processing: {domain_status.get('UpgradeProcessing', False)}")
        
        print("\n🔒 Security Features Enabled:")
        print(f"   ✅ HTTPS Enforced")
        print(f"   ✅ Encryption at Rest")
        print(f"   ✅ Node-to-Node Encryption")
        print(f"   ✅ IP Address Restriction ({your_ip})")
        print(f"   ✅ IAM-based Access Control")
        
        print(f"\n⏱️  Expected completion time: 10-15 minutes")
        print(f"   You can check status with: aws opensearch describe-domain --domain-name nejm-research")
        
        return domain_status
        
    except Exception as e:
        print(f"\n❌ Error creating domain: {e}")
        return None

def check_domain_status():
    """Check the current status of the domain"""
    
    print("\n🔍 Checking Domain Status...")
    
    try:
        client = boto3.client('opensearch', region_name='us-east-1')
        response = client.describe_domain(DomainName='nejm-research')
        
        domain = response['DomainStatus']
        
        print(f"Domain Name: {domain['DomainName']}")
        print(f"Processing: {domain['Processing']}")
        print(f"Created: {domain['Created']}")
        
        if domain.get('Endpoint'):
            print(f"Endpoint: https://{domain['Endpoint']}")
        else:
            print("Endpoint: Not yet available")
        
        # Security status
        print(f"\nSecurity Status:")
        print(f"   HTTPS Enforced: {domain.get('DomainEndpointOptions', {}).get('EnforceHTTPS', False)}")
        print(f"   Encryption at Rest: {domain.get('EncryptionAtRestOptions', {}).get('Enabled', False)}")
        print(f"   Node Encryption: {domain.get('NodeToNodeEncryptionOptions', {}).get('Enabled', False)}")
        
        return domain
        
    except Exception as e:
        print(f"❌ Error checking domain: {e}")
        return None

def main():
    """Main function"""
    
    print("🔒 NEJM Research - Secure OpenSearch Deployment")
    print("=" * 50)
    
    # Create the domain
    domain_status = create_secure_opensearch()
    
    if domain_status:
        print(f"\n🎉 Success! Domain creation initiated.")
        
        # Update setup state
        try:
            import sys
            sys.path.append('.')
            from setup_manager import SetupStateManager
            
            manager = SetupStateManager()
            manager.mark_step_complete("OpenSearch domain creation initiated")
            manager.add_note("OpenSearch domain 'nejm-research' created with full security: IP restrictions, encryption, HTTPS-only")
            
            print("📝 Updated setup state with progress")
            
        except Exception as e:
            print(f"⚠️  Could not update setup state: {e}")
        
        print(f"\n📋 Next Steps:")
        print(f"1. Wait 10-15 minutes for domain to become active")
        print(f"2. Run: python3 validate_security.py")
        print(f"3. Test domain access with your IP")
        print(f"4. Proceed to next component (S3, Secrets Manager)")
        
    else:
        print(f"\n❌ Domain creation failed. Please check AWS permissions and try again.")

if __name__ == "__main__":
    main()