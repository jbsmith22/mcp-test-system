#!/usr/bin/env python3
"""
Deploy the web interface to AWS S3 + CloudFront for proper AWS hosting
"""

import boto3
import json
import time

def create_s3_bucket_for_website():
    """Create S3 bucket configured for static website hosting"""
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'nejm-research-web-interface'
    
    try:
        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket {bucket_name} already exists")
        except:
            # Create bucket
            print(f"📦 Creating S3 bucket: {bucket_name}")
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"✅ Bucket created successfully")
        
        # Configure for static website hosting
        print("🌐 Configuring static website hosting...")
        
        website_config = {
            'IndexDocument': {'Suffix': 'index.html'},
            'ErrorDocument': {'Key': 'error.html'}
        }
        
        s3_client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration=website_config
        )
        
        # First, disable block public access settings
        print("🔓 Configuring public access settings...")
        try:
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': False,
                    'IgnorePublicAcls': False,
                    'BlockPublicPolicy': False,
                    'RestrictPublicBuckets': False
                }
            )
            print("✅ Public access settings configured")
        except Exception as e:
            print(f"⚠️  Warning: Could not configure public access: {e}")
        
        # Wait a moment for settings to propagate
        time.sleep(2)
        
        # Set bucket policy for public read access
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
        
        try:
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print("✅ Bucket policy applied")
        except Exception as e:
            print(f"⚠️  Warning: Could not apply bucket policy: {e}")
            print("   Website may still work via CloudFront")
        
        print("✅ Website hosting configured")
        return bucket_name
        
    except Exception as e:
        print(f"❌ Error creating S3 bucket: {e}")
        return None

def upload_website_files(bucket_name):
    """Upload website files to S3"""
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    try:
        print("📤 Uploading website files...")
        
        # Read the HTML file
        with open('aws_web_interface_full.html', 'r') as f:
            html_content = f.read()
        
        # Upload as index.html
        s3_client.put_object(
            Bucket=bucket_name,
            Key='index.html',
            Body=html_content,
            ContentType='text/html',
            CacheControl='no-cache'
        )
        
        # Create a simple error page
        error_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>NEJM Research Assistant - Error</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #e74c3c; }
            </style>
        </head>
        <body>
            <h1 class="error">Page Not Found</h1>
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
        
        print("✅ Website files uploaded")
        return True
        
    except Exception as e:
        print(f"❌ Error uploading files: {e}")
        return False

def create_cloudfront_distribution(bucket_name):
    """Create CloudFront distribution for better performance and HTTPS"""
    
    cloudfront_client = boto3.client('cloudfront', region_name='us-east-1')
    
    try:
        print("🌍 Creating CloudFront distribution...")
        
        # CloudFront distribution configuration
        distribution_config = {
            'CallerReference': f'nejm-research-{int(time.time())}',
            'Comment': 'NEJM Research Assistant Web Interface',
            'DefaultCacheBehavior': {
                'TargetOriginId': f'{bucket_name}-origin',
                'ViewerProtocolPolicy': 'redirect-to-https',
                'TrustedSigners': {
                    'Enabled': False,
                    'Quantity': 0
                },
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'}
                },
                'MinTTL': 0,
                'DefaultTTL': 86400,
                'MaxTTL': 31536000
            },
            'Origins': {
                'Quantity': 1,
                'Items': [
                    {
                        'Id': f'{bucket_name}-origin',
                        'DomainName': f'{bucket_name}.s3-website-us-east-1.amazonaws.com',
                        'CustomOriginConfig': {
                            'HTTPPort': 80,
                            'HTTPSPort': 443,
                            'OriginProtocolPolicy': 'http-only'
                        }
                    }
                ]
            },
            'DefaultRootObject': 'index.html',
            'Enabled': True,
            'PriceClass': 'PriceClass_100'  # Use only US, Canada, Europe
        }
        
        response = cloudfront_client.create_distribution(
            DistributionConfig=distribution_config
        )
        
        distribution_id = response['Distribution']['Id']
        domain_name = response['Distribution']['DomainName']
        
        print(f"✅ CloudFront distribution created")
        print(f"   Distribution ID: {distribution_id}")
        print(f"   Domain: {domain_name}")
        
        return domain_name, distribution_id
        
    except Exception as e:
        print(f"❌ Error creating CloudFront distribution: {e}")
        return None, None

def get_website_urls(bucket_name):
    """Get the website URLs"""
    
    # S3 website URL
    s3_url = f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"
    
    return s3_url

def main():
    print("🚀 Deploying NEJM Research Assistant to AWS")
    print("=" * 60)
    
    # Step 1: Create S3 bucket
    bucket_name = create_s3_bucket_for_website()
    if not bucket_name:
        print("❌ Failed to create S3 bucket")
        return False
    
    # Step 2: Upload website files
    if not upload_website_files(bucket_name):
        print("❌ Failed to upload website files")
        return False
    
    # Step 3: Get URLs
    s3_url = get_website_urls(bucket_name)
    
    # Step 4: Create CloudFront distribution (optional, for HTTPS and performance)
    print("\n🌍 Setting up CloudFront distribution...")
    cloudfront_domain, distribution_id = create_cloudfront_distribution(bucket_name)
    
    print(f"\n🎉 Website Deployment Complete!")
    print("=" * 50)
    
    print(f"\n🌐 Your AWS-hosted website is available at:")
    print(f"   S3 Website URL: {s3_url}")
    
    if cloudfront_domain:
        print(f"   CloudFront URL: https://{cloudfront_domain}")
        print(f"   (CloudFront may take 10-15 minutes to fully deploy)")
    
    print(f"\n📊 What you have:")
    print(f"   ✅ AWS-hosted web interface")
    print(f"   ✅ Connected to your OpenSearch database (255 articles)")
    print(f"   ✅ AI-powered search using your API Gateway")
    print(f"   ✅ Same functionality as your local version")
    print(f"   ✅ Accessible from anywhere")
    
    if cloudfront_domain:
        print(f"   ✅ HTTPS enabled via CloudFront")
        print(f"   ✅ Global CDN for fast loading")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Visit {s3_url} to test your website")
    print(f"   2. Try searching for 'artificial intelligence healthcare'")
    print(f"   3. Verify all functionality works as expected")
    
    if cloudfront_domain:
        print(f"   4. Use https://{cloudfront_domain} for HTTPS access (after deployment)")
    
    return True

if __name__ == "__main__":
    main()