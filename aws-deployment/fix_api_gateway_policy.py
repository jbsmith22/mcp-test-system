#!/usr/bin/env python3
"""
Fix API Gateway policy to allow access
"""

import boto3
import json

def update_api_gateway_policy():
    """Update API Gateway policy to allow broader access"""
    
    print("🔧 Updating API Gateway resource policy...")
    
    # More permissive policy for debugging
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": "arn:aws:execute-api:us-east-1:227027150061:lwi6jeeczi/*",
                "Condition": {
                    "IpAddress": {
                        "aws:SourceIp": [
                            "108.20.28.24/32",  # Your direct IP
                            "108.20.28.0/24",   # Your subnet
                            "54.230.0.0/16",    # CloudFront IP range 1
                            "54.239.128.0/18",  # CloudFront IP range 2
                            "99.84.0.0/16",     # CloudFront IP range 3
                            "205.251.192.0/19", # CloudFront IP range 4
                            "54.182.0.0/16",    # CloudFront IP range 5
                            "54.192.0.0/16"     # CloudFront IP range 6
                        ]
                    }
                }
            }
        ]
    }
    
    try:
        client = boto3.client('apigateway', region_name='us-east-1')
        
        response = client.update_rest_api(
            restApiId='lwi6jeeczi',
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/policy',
                    'value': json.dumps(policy)
                }
            ]
        )
        
        print("✅ API Gateway policy updated")
        return True
        
    except Exception as e:
        print(f"❌ Error updating policy: {e}")
        return False

def deploy_api_changes():
    """Deploy the API changes"""
    
    print("🚀 Deploying API changes...")
    
    try:
        client = boto3.client('apigateway', region_name='us-east-1')
        
        response = client.create_deployment(
            restApiId='lwi6jeeczi',
            stageName='prod',
            description='Updated IP policy for CloudFront compatibility'
        )
        
        print(f"✅ API deployed: {response['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error deploying API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Fixing API Gateway Access Issues")
    print("=" * 40)
    
    policy_updated = update_api_gateway_policy()
    
    if policy_updated:
        deployed = deploy_api_changes()
        
        if deployed:
            print(f"\n🎉 SUCCESS! API Gateway should now work")
            print(f"   📊 Statistics endpoint should be accessible")
            print(f"   🔍 Search endpoint should be accessible")
            print(f"   🌐 Website should work from browser")
        else:
            print(f"\n⚠️ Policy updated but deployment failed")
    else:
        print(f"\n❌ Failed to update API Gateway policy")