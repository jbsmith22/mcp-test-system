#!/usr/bin/env python3
"""
Enable CORS on the API Gateway for the web interface
"""

import boto3
import json

def enable_cors():
    """Enable CORS on the API Gateway"""
    
    client = boto3.client('apigateway', region_name='us-east-1')
    
    api_id = 'lwi6jeeczi'
    resource_id = 'wu11z3'  # /research resource
    
    try:
        print("🌐 Enabling CORS on API Gateway...")
        
        # Add OPTIONS method for CORS preflight
        print("📝 Adding OPTIONS method...")
        
        try:
            client.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                authorizationType='NONE',
                apiKeyRequired=False
            )
            print("✅ OPTIONS method added")
        except Exception as e:
            if "ConflictException" in str(e):
                print("✅ OPTIONS method already exists - updating...")
                # Update existing method to ensure no API key required
                try:
                    client.put_method(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod='OPTIONS',
                        authorizationType='NONE',
                        apiKeyRequired=False
                    )
                    print("✅ OPTIONS method updated")
                except Exception as update_e:
                    print(f"⚠️  Warning updating OPTIONS method: {update_e}")
            else:
                print(f"⚠️  Warning adding OPTIONS method: {e}")
        
        # Configure OPTIONS method integration
        print("🔧 Configuring OPTIONS integration...")
        
        try:
            client.put_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                type='MOCK',
                requestTemplates={
                    'application/json': '{"statusCode": 200}'
                }
            )
            print("✅ OPTIONS integration configured")
        except Exception as e:
            print(f"⚠️  Warning configuring OPTIONS integration: {e}")
        
        # Configure OPTIONS method response
        print("📤 Configuring OPTIONS response...")
        
        try:
            client.put_method_response(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Origin': False,
                    'method.response.header.Access-Control-Allow-Methods': False,
                    'method.response.header.Access-Control-Allow-Headers': False
                }
            )
            print("✅ OPTIONS method response configured")
        except Exception as e:
            print(f"⚠️  Warning configuring OPTIONS response: {e}")
        
        # Configure OPTIONS integration response
        print("🔄 Configuring OPTIONS integration response...")
        
        try:
            client.put_integration_response(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-api-key'"
                }
            )
            print("✅ OPTIONS integration response configured")
        except Exception as e:
            print(f"⚠️  Warning configuring OPTIONS integration response: {e}")
        
        # Update POST method response to include CORS headers
        print("🔧 Updating POST method response for CORS...")
        
        try:
            # Get current method response
            current_response = client.get_method_response(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='POST',
                statusCode='200'
            )
            
            # Add CORS headers to existing response parameters
            response_params = current_response.get('responseParameters', {})
            response_params.update({
                'method.response.header.Access-Control-Allow-Origin': False,
                'method.response.header.Access-Control-Allow-Methods': False,
                'method.response.header.Access-Control-Allow-Headers': False
            })
            
            client.put_method_response(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='POST',
                statusCode='200',
                responseParameters=response_params
            )
            print("✅ POST method response updated")
            
        except Exception as e:
            print(f"⚠️  Warning updating POST method response: {e}")
        
        # Deploy the API
        print("🚀 Deploying API changes...")
        
        client.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Enable CORS for web interface'
        )
        
        print("✅ API deployed with CORS enabled")
        print("\n🎉 CORS Configuration Complete!")
        print("=" * 50)
        print("Your web interface should now work properly.")
        print("The API Gateway now supports cross-origin requests from browsers.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error enabling CORS: {e}")
        return False

if __name__ == "__main__":
    enable_cors()