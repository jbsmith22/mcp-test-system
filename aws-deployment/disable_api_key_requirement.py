#!/usr/bin/env python3
"""
Disable API key requirement for the research endpoint
"""

import boto3

def disable_api_key_requirement():
    """Disable API key requirement for POST method"""
    
    print("🔧 Disabling API key requirement...")
    
    try:
        client = boto3.client('apigateway', region_name='us-east-1')
        
        # Update the POST method to not require API key
        response = client.update_method(
            restApiId='lwi6jeeczi',
            resourceId='wu11z3',
            httpMethod='POST',
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/apiKeyRequired',
                    'value': 'false'
                }
            ]
        )
        
        print("✅ API key requirement disabled")
        return True
        
    except Exception as e:
        print(f"❌ Error disabling API key requirement: {e}")
        return False

def deploy_api_changes():
    """Deploy the API changes"""
    
    print("🚀 Deploying API changes...")
    
    try:
        client = boto3.client('apigateway', region_name='us-east-1')
        
        response = client.create_deployment(
            restApiId='lwi6jeeczi',
            stageName='prod',
            description='Disabled API key requirement for browser access'
        )
        
        print(f"✅ API deployed: {response['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error deploying API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Disabling API Key Requirement")
    print("=" * 35)
    
    disabled = disable_api_key_requirement()
    
    if disabled:
        deployed = deploy_api_changes()
        
        if deployed:
            print(f"\n🎉 SUCCESS! API key requirement disabled")
            print(f"   🌐 Website should now work without API keys")
            print(f"   📊 Statistics should be accessible")
            print(f"   🔍 Search should be accessible")
        else:
            print(f"\n⚠️ API key disabled but deployment failed")
    else:
        print(f"\n❌ Failed to disable API key requirement")