#!/usr/bin/env python3
"""
Remove usage plan to eliminate API key requirements
"""

import boto3

def remove_usage_plan_association():
    """Remove the API from the usage plan"""
    
    print("🔧 Removing usage plan association...")
    
    try:
        client = boto3.client('apigateway', region_name='us-east-1')
        
        # Remove the API stage from the usage plan
        response = client.update_usage_plan(
            usagePlanId='nmspgd',
            patchOperations=[
                {
                    'op': 'remove',
                    'path': '/apiStages',
                    'value': 'lwi6jeeczi:prod'
                }
            ]
        )
        
        print("✅ Usage plan association removed")
        return True
        
    except Exception as e:
        print(f"❌ Error removing usage plan: {e}")
        return False

def deploy_api_changes():
    """Deploy the API changes"""
    
    print("🚀 Deploying API changes...")
    
    try:
        client = boto3.client('apigateway', region_name='us-east-1')
        
        response = client.create_deployment(
            restApiId='lwi6jeeczi',
            stageName='prod',
            description='Removed usage plan for open access'
        )
        
        print(f"✅ API deployed: {response['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error deploying API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Removing Usage Plan Restrictions")
    print("=" * 35)
    
    removed = remove_usage_plan_association()
    
    if removed:
        deployed = deploy_api_changes()
        
        if deployed:
            print(f"\n🎉 SUCCESS! Usage plan restrictions removed")
            print(f"   🌐 API should now be accessible without keys")
            print(f"   📊 Statistics should work")
            print(f"   🔍 Search should work")
        else:
            print(f"\n⚠️ Usage plan removed but deployment failed")
    else:
        print(f"\n❌ Failed to remove usage plan")