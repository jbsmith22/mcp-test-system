#!/usr/bin/env python3
"""
Deploy Lambda layer with dependencies for NEJM ingestion
"""

import boto3
import subprocess
import tempfile
import zipfile
import os
import shutil

def create_lambda_layer():
    """Create Lambda layer with required dependencies"""
    
    print("📦 Creating Lambda layer with dependencies...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        python_dir = os.path.join(temp_dir, 'python')
        os.makedirs(python_dir)
        
        # Install dependencies
        dependencies = [
            'requests>=2.31.0',
            'opensearch-py>=2.4.0',
            'boto3>=1.34.0',
            'botocore>=1.34.0'
        ]
        
        print(f"Installing dependencies: {', '.join(dependencies)}")
        
        for dep in dependencies:
            cmd = [
                'pip', 'install', dep,
                '--target', python_dir,
                '--platform', 'linux_x86_64',
                '--only-binary=:all:',
                '--no-deps'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to install {dep}: {result.stderr}")
                return None
        
        # Create zip file
        layer_zip = os.path.join(temp_dir, 'layer.zip')
        
        with zipfile.ZipFile(layer_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(python_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, temp_dir)
                    zip_file.write(file_path, arc_path)
        
        # Read zip content
        with open(layer_zip, 'rb') as f:
            zip_content = f.read()
        
        print(f"✅ Layer package created ({len(zip_content)} bytes)")
        return zip_content

def deploy_layer():
    """Deploy the Lambda layer"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create layer package
    zip_content = create_lambda_layer()
    if not zip_content:
        return None
    
    try:
        print("🚀 Deploying Lambda layer...")
        
        response = lambda_client.publish_layer_version(
            LayerName='nejm-ingestion-dependencies',
            Description='Dependencies for NEJM article ingestion (requests, opensearch-py)',
            Content={'ZipFile': zip_content},
            CompatibleRuntimes=['python3.12'],
            CompatibleArchitectures=['x86_64']
        )
        
        layer_arn = response['LayerVersionArn']
        print(f"✅ Layer deployed successfully")
        print(f"   Layer ARN: {layer_arn}")
        
        return layer_arn
        
    except Exception as e:
        print(f"❌ Error deploying layer: {e}")
        return None

def update_lambda_with_layer(layer_arn):
    """Update Lambda function to use the layer"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        print("🔧 Updating Lambda function with layer...")
        
        # Update function configuration
        lambda_client.update_function_configuration(
            FunctionName='nejm-content-ingestion',
            Layers=[layer_arn]
        )
        
        print("✅ Lambda function updated with layer")
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {e}")
        return False

def test_lambda_with_dependencies():
    """Test Lambda function with dependencies"""
    
    import json
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    test_payload = {
        "context": "nejm-ai",
        "limit": 2,
        "dry_run": True
    }
    
    try:
        print("🧪 Testing Lambda function with dependencies...")
        
        response = lambda_client.invoke(
            FunctionName='nejm-content-ingestion',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            
            print(f"✅ Lambda test successful!")
            print(f"   Articles found: {body.get('articles_found', 0)}")
            print(f"   Articles processed: {body.get('articles_processed', 0)}")
            
            if body.get('results'):
                print(f"   Sample articles:")
                for i, article in enumerate(body['results'][:2], 1):
                    print(f"     {i}. {article.get('title', 'Unknown')[:60]}...")
                    print(f"        DOI: {article.get('doi', 'N/A')}")
                    print(f"        Status: {article.get('status', 'Unknown')}")
            
            return True
        else:
            print(f"❌ Lambda test failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Lambda test error: {e}")
        return False

def main():
    import json
    
    print("📦 Deploying NEJM Ingestion Lambda Layer")
    print("=" * 50)
    
    # Step 1: Deploy layer
    layer_arn = deploy_layer()
    if not layer_arn:
        print("❌ Failed to deploy layer")
        return
    
    # Step 2: Update Lambda function
    if not update_lambda_with_layer(layer_arn):
        print("❌ Failed to update Lambda function")
        return
    
    # Step 3: Wait for deployment
    print("⏳ Waiting for deployment...")
    import time
    time.sleep(15)
    
    # Step 4: Test function
    if test_lambda_with_dependencies():
        print(f"\n🎉 SUCCESS! NEJM ingestion Lambda is fully operational")
        print(f"📋 Ready for article ingestion from NEJM API")
        print(f"🔗 Function: nejm-content-ingestion")
        print(f"📦 Layer: {layer_arn}")
    else:
        print(f"\n⚠️ Layer deployed but Lambda test failed")

if __name__ == "__main__":
    main()