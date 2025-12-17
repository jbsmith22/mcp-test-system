#!/usr/bin/env python3
"""
Deploy MCP Web Interface to AWS S3
Creates a publicly accessible website that uses the MCP Lambda API
"""

import boto3
import json
import os
from botocore.exceptions import ClientError

def create_s3_bucket_and_website():
    """Create S3 bucket and configure it for static website hosting"""
    
    # Initialize AWS clients
    s3_client = boto3.client('s3')
    
    # Bucket configuration
    bucket_name = 'nejm-mcp-research-web'
    region = 'us-east-1'
    
    try:
        # Create S3 bucket
        print(f"🪣 Creating S3 bucket: {bucket_name}")
        
        try:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"✅ Created bucket: {bucket_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                print(f"✅ Bucket {bucket_name} already exists and is owned by you")
            else:
                raise e
        
        # Configure bucket for static website hosting
        print("🌐 Configuring static website hosting...")
        
        website_config = {
            'IndexDocument': {'Suffix': 'index.html'},
            'ErrorDocument': {'Key': 'error.html'}
        }
        
        s3_client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration=website_config
        )
        
        # Disable block public access (required for public website)
        print("🔧 Configuring public access settings...")
        
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        
        # Wait a moment for the setting to take effect
        import time
        time.sleep(2)
        
        # Configure bucket policy for public read access
        print("🔓 Setting bucket policy for public access...")
        
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        # Upload the HTML file
        print("📤 Uploading web interface...")
        
        html_file = 'aws-deployment/mcp_web_interface.html'
        if not os.path.exists(html_file):
            print(f"❌ HTML file not found: {html_file}")
            return None
        
        # Upload as index.html
        s3_client.upload_file(
            html_file,
            bucket_name,
            'index.html',
            ExtraArgs={
                'ContentType': 'text/html',
                'CacheControl': 'no-cache'
            }
        )
        
        # Create a simple error page
        error_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - NEJM Research Assistant</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #e74c3c; }
            </style>
        </head>
        <body>
            <h1 class="error">404 - Page Not Found</h1>
            <p>The page you're looking for doesn't exist.</p>
            <a href="/">Return to NEJM Research Assistant</a>
        </body>
        </html>
        """
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key='error.html',
            Body=error_html,
            ContentType='text/html'
        )
        
        # Get website URL
        website_url = f"http://{bucket_name}.s3-website-{region}.amazonaws.com"
        
        print(f"\n🎉 SUCCESS! MCP Web Interface deployed!")
        print(f"🌐 Website URL: {website_url}")
        print(f"📊 MCP API: https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research")
        
        return {
            'bucket_name': bucket_name,
            'website_url': website_url,
            'region': region
        }
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        return None

def test_website_deployment(website_url):
    """Test that the website is accessible"""
    import requests
    
    try:
        print(f"\n🧪 Testing website accessibility...")
        response = requests.get(website_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Website is accessible at {website_url}")
            print(f"📄 Content length: {len(response.content)} bytes")
            
            # Check if it contains our expected content
            if 'NEJM Research Assistant' in response.text:
                print("✅ Website content looks correct")
            else:
                print("⚠️ Website content may not be correct")
                
        else:
            print(f"❌ Website returned status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Website test failed: {str(e)}")

def main():
    """Main deployment function"""
    print("🚀 Deploying NEJM MCP Web Interface to AWS S3...")
    print("=" * 60)
    
    # Deploy the website
    result = create_s3_bucket_and_website()
    
    if result:
        # Test the deployment
        test_website_deployment(result['website_url'])
        
        print("\n" + "=" * 60)
        print("📋 DEPLOYMENT SUMMARY")
        print("=" * 60)
        print(f"✅ S3 Bucket: {result['bucket_name']}")
        print(f"🌐 Website URL: {result['website_url']}")
        print(f"🔧 MCP API Endpoint: https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research")
        print(f"📊 Database: 412 NEJM articles in OpenSearch")
        print(f"🤖 AI Model: Claude 3.5 Sonnet")
        
        print("\n🎯 WHAT YOU CAN DO NOW:")
        print(f"1. Visit {result['website_url']} in your browser")
        print("2. Search medical literature using natural language")
        print("3. Get AI-powered research answers")
        print("4. View vector embeddings and relevance scores")
        print("5. Test individual MCP tools")
        
        print("\n🔧 MCP TOOLS AVAILABLE:")
        print("• search_articles - Semantic search with vector visibility")
        print("• ask_research_question - AI-powered Q&A with sources")
        print("• get_database_stats - Database metrics and health")
        print("• get_article_by_doi - Retrieve specific articles")
        print("• compare_embeddings - Vector similarity analysis")
        
    else:
        print("❌ Deployment failed. Check the error messages above.")

if __name__ == "__main__":
    main()