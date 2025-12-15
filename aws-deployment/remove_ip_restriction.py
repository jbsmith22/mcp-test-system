#!/usr/bin/env python3
"""
Temporarily remove IP restrictions to test API
"""

import boto3
import json

def remove_api_gateway_policy():
    """Remove IP restrictions from API Gateway"""
    
    print("🔧 Removing IP restrictions from API Gateway...")
    
    # Open policy for testing
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": "arn:aws:execute-api:us-east-1:227027150061:lwi6jeeczi/*"
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
        
        print("✅ IP restrictions removed")
        return True
        
    except Exception as e:
        print(f"❌ Error removing restrictions: {e}")
        return False

def deploy_api_changes():
    """Deploy the API changes"""
    
    print("🚀 Deploying API changes...")
    
    try:
        client = boto3.client('apigateway', region_name='us-east-1')
        
        response = client.create_deployment(
            restApiId='lwi6jeeczi',
            stageName='prod',
            description='Temporarily removed IP restrictions for testing'
        )
        
        print(f"✅ API deployed: {response['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error deploying API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Temporarily Removing IP Restrictions")
    print("=" * 40)
    
    removed = remove_api_gateway_policy()
    
    if removed:
        deployed = deploy_api_changes()
        
        if deployed:
            print(f"\n🎉 SUCCESS! IP restrictions removed")
            print(f"   ⚠️ API is now open to all IPs (temporary)")
            print(f"   🧪 Test the website now")
            print(f"   🔒 Remember to restore IP security after testing")
        else:
            print(f"\n⚠️ Restrictions removed but deployment failed")
    else:
        print(f"\n❌ Failed to remove IP restrictions")