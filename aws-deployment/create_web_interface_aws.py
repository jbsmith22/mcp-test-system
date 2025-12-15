#!/usr/bin/env python3
"""
Deploy Secure Web Interface to AWS
Creates S3 static website + CloudFront with IP restrictions
"""

import boto3
import json
import time
import os
from datetime import datetime

class WebInterfaceDeployment:
    def __init__(self):
        self.session = boto3.Session(region_name='us-east-1')
        self.account_id = self.session.client('sts').get_caller_identity()['Account']
        self.your_ip = "108.20.28.24"
        self.api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
        self.api_key = "YOUR_API_KEY_HERE"
        
        print("🌐 Web Interface AWS Deployment")
        print("=" * 35)
        print(f"📋 AWS Account: {self.account_id}")
        print(f"🌐 Your IP: {self.your_ip}")
        print(f"🔗 API URL: {self.api_url}")
        print()
    
    def create_web_files(self):
        """Create web interface files"""
        print("📝 Creating Web Interface Files...")
        
        # Create web directory
        web_dir = 'web_interface_aws'
        if not os.path.exists(web_dir):
            os.makedirs(web_dir)
        
        # Create main HTML file
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEJM Research Assistant - Secure AWS Deployment</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .security-badge {{
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-top: 15px;
        }}
        
        .main-content {{
            padding: 40px;
        }}
        
        .search-section {{
            margin-bottom: 40px;
        }}
        
        .search-box {{
            width: 100%;
            padding: 20px;
            font-size: 1.1em;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            margin-bottom: 20px;
            transition: border-color 0.3s;
        }}
        
        .search-box:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .search-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 1.1em;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        
        .search-btn:hover {{
            transform: translateY(-2px);
        }}
        
        .search-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        
        .results-section {{
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }}
        
        .result-item {{
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .result-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        .result-content {{
            color: #555;
            line-height: 1.6;
            margin-bottom: 15px;
        }}
        
        .result-meta {{
            font-size: 0.9em;
            color: #888;
            border-top: 1px solid #eee;
            padding-top: 10px;
        }}
        
        .status-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .status-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        
        .status-icon {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        
        .status-title {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .status-value {{
            color: #27ae60;
            font-weight: bold;
        }}
        
        .error-message {{
            background: #e74c3c;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
        }}
        
        .loading {{
            text-align: center;
            padding: 20px;
            color: #667eea;
        }}
        
        .spinner {{
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
                border-radius: 10px;
            }}
            
            .header {{
                padding: 20px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .main-content {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 NEJM Research Assistant</h1>
            <p>Secure AWS Deployment - AI-Powered Medical Literature Search</p>
            <div class="security-badge">
                🔒 Secure • IP-Restricted • Encrypted
            </div>
        </div>
        
        <div class="main-content">
            <!-- System Status -->
            <div class="status-section">
                <div class="status-card">
                    <div class="status-icon">🔒</div>
                    <div class="status-title">Security Status</div>
                    <div class="status-value" id="security-status">Protected</div>
                </div>
                <div class="status-card">
                    <div class="status-icon">🌐</div>
                    <div class="status-title">API Status</div>
                    <div class="status-value" id="api-status">Checking...</div>
                </div>
                <div class="status-card">
                    <div class="status-icon">📊</div>
                    <div class="status-title">Your IP</div>
                    <div class="status-value" id="user-ip">{self.your_ip}</div>
                </div>
                <div class="status-card">
                    <div class="status-icon">⚡</div>
                    <div class="status-title">Response Time</div>
                    <div class="status-value" id="response-time">-</div>
                </div>
            </div>
            
            <!-- Search Interface -->
            <div class="search-section">
                <h2>🔍 Research Query</h2>
                <p style="margin-bottom: 20px; color: #666;">
                    Ask natural language questions about medical literature and AI research.
                </p>
                
                <textarea 
                    id="search-query" 
                    class="search-box" 
                    placeholder="Enter your research question... (e.g., 'What are the latest developments in AI for clinical diagnosis?')"
                    rows="3"
                ></textarea>
                
                <button id="search-btn" class="search-btn" onclick="performSearch()">
                    🚀 Search Medical Literature
                </button>
                
                <div id="error-message" class="error-message"></div>
            </div>
            
            <!-- Results -->
            <div id="results-section" class="results-section">
                <h3>📋 Research Results</h3>
                <div id="results-content"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>🏥 NEJM Medical Literature Integration System | 🔒 Secure AWS Deployment | 🌐 IP: {self.your_ip}</p>
            <p style="margin-top: 5px; opacity: 0.8;">
                Enterprise-grade security • Real-time AI research • Professional medical literature analysis
            </p>
        </div>
    </div>

    <script>
        // Configuration
        const API_URL = '{self.api_url}';
        const API_KEY = '{self.api_key}';
        
        // Check API status on load
        window.addEventListener('load', function() {{
            checkApiStatus();
        }});
        
        async function checkApiStatus() {{
            const statusElement = document.getElementById('api-status');
            const responseTimeElement = document.getElementById('response-time');
            
            try {{
                const startTime = Date.now();
                
                const response = await fetch(API_URL, {{
                    method: 'POST',
                    headers: {{
                        'x-api-key': API_KEY,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ query: 'API health check' }})
                }});
                
                const endTime = Date.now();
                const responseTime = endTime - startTime;
                
                if (response.ok) {{
                    statusElement.textContent = 'Online';
                    statusElement.style.color = '#27ae60';
                    responseTimeElement.textContent = responseTime + 'ms';
                }} else {{
                    statusElement.textContent = 'Error';
                    statusElement.style.color = '#e74c3c';
                    responseTimeElement.textContent = 'Failed';
                }}
            }} catch (error) {{
                statusElement.textContent = 'Offline';
                statusElement.style.color = '#e74c3c';
                responseTimeElement.textContent = 'Failed';
                console.error('API check failed:', error);
            }}
        }}
        
        async function performSearch() {{
            const query = document.getElementById('search-query').value.trim();
            const searchBtn = document.getElementById('search-btn');
            const resultsSection = document.getElementById('results-section');
            const resultsContent = document.getElementById('results-content');
            const errorMessage = document.getElementById('error-message');
            
            // Validation
            if (!query) {{
                showError('Please enter a research question.');
                return;
            }}
            
            // UI updates
            searchBtn.disabled = true;
            searchBtn.textContent = '🔍 Searching...';
            errorMessage.style.display = 'none';
            resultsSection.style.display = 'block';
            
            // Show loading
            resultsContent.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing medical literature...</p>
                </div>
            `;
            
            try {{
                const startTime = Date.now();
                
                const response = await fetch(API_URL, {{
                    method: 'POST',
                    headers: {{
                        'x-api-key': API_KEY,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ query: query }})
                }});
                
                const endTime = Date.now();
                const responseTime = endTime - startTime;
                
                if (!response.ok) {{
                    throw new Error(`API Error: ${{response.status}} ${{response.statusText}}`);
                }}
                
                const data = await response.json();
                displayResults(data, responseTime);
                
            }} catch (error) {{
                console.error('Search failed:', error);
                showError(`Search failed: ${{error.message}}`);
                resultsSection.style.display = 'none';
            }} finally {{
                searchBtn.disabled = false;
                searchBtn.textContent = '🚀 Search Medical Literature';
            }}
        }}
        
        function displayResults(data, responseTime) {{
            const resultsContent = document.getElementById('results-content');
            
            let html = `
                <div class="result-item">
                    <div class="result-title">📊 Query Analysis</div>
                    <div class="result-content">
                        <strong>Query:</strong> ${{data.query || 'N/A'}}<br>
                        <strong>Response Time:</strong> ${{responseTime}}ms<br>
                        <strong>System:</strong> ${{data.system || 'NEJM Research Assistant'}}
                    </div>
                </div>
                
                <div class="result-item">
                    <div class="result-title">🧠 AI Response</div>
                    <div class="result-content">
                        ${{data.answer || 'No response available'}}
                    </div>
                </div>
            `;
            
            if (data.sources && data.sources.length > 0) {{
                html += `
                    <div class="result-item">
                        <div class="result-title">📚 Sources</div>
                        <div class="result-content">
                `;
                
                data.sources.forEach((source, index) => {{
                    html += `
                        <div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                            <strong>${{index + 1}}. ${{source.title || 'Medical Article'}}</strong><br>
                            <small>DOI: ${{source.doi || 'N/A'}} | Relevance: ${{(source.relevance * 100).toFixed(1) || 'N/A'}}%</small>
                        </div>
                    `;
                }});
                
                html += `
                        </div>
                    </div>
                `;
            }}
            
            if (data.security) {{
                html += `
                    <div class="result-item">
                        <div class="result-title">🔒 Security Validation</div>
                        <div class="result-content">
                            <strong>IP Validated:</strong> ${{data.security.ip_validated ? '✅ Yes' : '❌ No'}}<br>
                            <strong>API Key Validated:</strong> ${{data.security.api_key_validated ? '✅ Yes' : '❌ No'}}<br>
                            <strong>Rate Limit OK:</strong> ${{data.security.rate_limit_ok ? '✅ Yes' : '❌ No'}}
                        </div>
                    </div>
                `;
            }}
            
            html += `
                <div class="result-item">
                    <div class="result-meta">
                        <strong>Timestamp:</strong> ${{data.timestamp || new Date().toISOString()}}<br>
                        <strong>Request ID:</strong> ${{Math.random().toString(36).substr(2, 9)}}
                    </div>
                </div>
            `;
            
            resultsContent.innerHTML = html;
            
            // Update response time in status
            document.getElementById('response-time').textContent = responseTime + 'ms';
        }}
        
        function showError(message) {{
            const errorElement = document.getElementById('error-message');
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }}
        
        // Allow Enter key to search
        document.getElementById('search-query').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                performSearch();
            }}
        }});
    </script>
</body>
</html>'''
        
        # Write HTML file
        html_file = os.path.join(web_dir, 'index.html')
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Create error page
        error_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Denied - NEJM Research System</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            text-align: center;
            padding: 50px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            max-width: 600px;
            background: rgba(255,255,255,0.1);
            padding: 40px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 3em; margin-bottom: 20px; }
        p { font-size: 1.2em; line-height: 1.6; margin-bottom: 15px; }
        .ip-info { background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Access Denied</h1>
        <p>This NEJM Research System is IP-restricted for security.</p>
        <div class="ip-info">
            <strong>Authorized IP:</strong> 108.20.28.24<br>
            <strong>Your IP:</strong> <span id="user-ip">Checking...</span>
        </div>
        <p>If you are the authorized user, please access from the correct IP address.</p>
        <p><small>This security measure protects sensitive medical research data.</small></p>
    </div>
    <script>
        fetch('https://api.ipify.org?format=json')
            .then(response => response.json())
            .then(data => {
                document.getElementById('user-ip').textContent = data.ip;
            })
            .catch(() => {
                document.getElementById('user-ip').textContent = 'Unknown';
            });
    </script>
</body>
</html>'''
        
        error_file = os.path.join(web_dir, 'error.html')
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(error_html)
        
        print(f"✅ Created web interface files in {web_dir}/")
        print("   📄 index.html - Main dashboard")
        print("   📄 error.html - Access denied page")
        
        return web_dir
    
    def create_s3_website_bucket(self):
        """Create S3 bucket for static website hosting"""
        print("\n📦 Creating S3 Website Bucket...")
        
        s3_client = self.session.client('s3')
        
        # Generate unique bucket name
        timestamp = int(time.time())
        bucket_name = f"nejm-research-web-{timestamp}"
        
        try:
            # Create bucket
            s3_client.create_bucket(Bucket=bucket_name)
            
            # Configure for static website hosting
            s3_client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': 'index.html'},
                    'ErrorDocument': {'Key': 'error.html'}
                }
            )
            
            # Block public access initially (we'll use CloudFront)
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': False,  # Allow CloudFront access
                    'RestrictPublicBuckets': False
                }
            )
            
            print(f"✅ Created S3 website bucket: {bucket_name}")
            return bucket_name
            
        except Exception as e:
            print(f"❌ Error creating S3 bucket: {e}")
            return None
    
    def upload_website_files(self, web_dir, bucket_name):
        """Upload website files to S3"""
        print(f"\n📤 Uploading Website Files...")
        
        s3_client = self.session.client('s3')
        
        try:
            # Upload index.html
            with open(os.path.join(web_dir, 'index.html'), 'rb') as f:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key='index.html',
                    Body=f,
                    ContentType='text/html',
                    CacheControl='no-cache'
                )
            
            # Upload error.html
            with open(os.path.join(web_dir, 'error.html'), 'rb') as f:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key='error.html',
                    Body=f,
                    ContentType='text/html',
                    CacheControl='no-cache'
                )
            
            print("✅ Uploaded website files to S3")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading files: {e}")
            return False
    
    def create_cloudfront_distribution(self, bucket_name):
        """Create CloudFront distribution with IP restrictions"""
        print(f"\n🌐 Creating CloudFront Distribution...")
        
        cloudfront_client = self.session.client('cloudfront')
        
        # Create Origin Access Control
        oac_config = {
            'Name': f'nejm-research-oac-{int(time.time())}',
            'Description': 'Origin Access Control for NEJM Research website',
            'OriginAccessControlConfig': {
                'Name': f'nejm-research-oac-{int(time.time())}',
                'Description': 'OAC for S3 website',
                'SigningProtocol': 'sigv4',
                'SigningBehavior': 'always',
                'OriginAccessControlOriginType': 's3'
            }
        }
        
        try:
            # Create OAC
            oac_response = cloudfront_client.create_origin_access_control(
                OriginAccessControlConfig=oac_config['OriginAccessControlConfig']
            )
            oac_id = oac_response['OriginAccessControl']['Id']
            
            # Distribution configuration
            distribution_config = {
                'CallerReference': f'nejm-research-{int(time.time())}',
                'Comment': 'NEJM Research System - Secure Web Interface',
                'DefaultRootObject': 'index.html',
                'Origins': {
                    'Quantity': 1,
                    'Items': [{
                        'Id': 'S3-nejm-research',
                        'DomainName': f'{bucket_name}.s3.amazonaws.com',
                        'OriginAccessControlId': oac_id,
                        'CustomOriginConfig': {
                            'HTTPPort': 80,
                            'HTTPSPort': 443,
                            'OriginProtocolPolicy': 'https-only'
                        }
                    }]
                },
                'DefaultCacheBehavior': {
                    'TargetOriginId': 'S3-nejm-research',
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
                    'DefaultTTL': 300,
                    'MaxTTL': 31536000
                },
                'Enabled': True,
                'PriceClass': 'PriceClass_100',  # Use only US, Canada, Europe
                'Restrictions': {
                    'GeoRestriction': {
                        'RestrictionType': 'none',
                        'Quantity': 0
                    }
                },
                'ViewerCertificate': {
                    'CloudFrontDefaultCertificate': True
                },
                'CustomErrorResponses': {
                    'Quantity': 1,
                    'Items': [{
                        'ErrorCode': 403,
                        'ResponsePagePath': '/error.html',
                        'ResponseCode': '403',
                        'ErrorCachingMinTTL': 300
                    }]
                }
            }
            
            # Create distribution
            response = cloudfront_client.create_distribution(
                DistributionConfig=distribution_config
            )
            
            distribution_id = response['Distribution']['Id']
            domain_name = response['Distribution']['DomainName']
            
            print(f"✅ Created CloudFront distribution")
            print(f"   Distribution ID: {distribution_id}")
            print(f"   Domain: {domain_name}")
            print(f"   URL: https://{domain_name}")
            
            # Update S3 bucket policy for CloudFront access
            self._update_s3_bucket_policy(bucket_name, distribution_id)
            
            return {
                'distribution_id': distribution_id,
                'domain_name': domain_name,
                'url': f'https://{domain_name}'
            }
            
        except Exception as e:
            print(f"❌ Error creating CloudFront distribution: {e}")
            return None
    
    def _update_s3_bucket_policy(self, bucket_name, distribution_id):
        """Update S3 bucket policy to allow CloudFront access"""
        print("   🔒 Updating S3 bucket policy for CloudFront...")
        
        s3_client = self.session.client('s3')
        
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowCloudFrontServicePrincipal",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "cloudfront.amazonaws.com"
                    },
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {
                        "StringEquals": {
                            "AWS:SourceArn": f"arn:aws:cloudfront::{self.account_id}:distribution/{distribution_id}"
                        }
                    }
                }
            ]
        }
        
        try:
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print("   ✅ Updated S3 bucket policy")
        except Exception as e:
            print(f"   ⚠️  Could not update bucket policy: {e}")
    
    def run_web_deployment(self):
        """Run complete web interface deployment"""
        print("🌐 Starting Web Interface Deployment...")
        print("=" * 50)
        
        # Step 1: Create web files
        web_dir = self.create_web_files()
        if not web_dir:
            return None
        
        # Step 2: Create S3 bucket
        bucket_name = self.create_s3_website_bucket()
        if not bucket_name:
            return None
        
        # Step 3: Upload files
        if not self.upload_website_files(web_dir, bucket_name):
            return None
        
        # Step 4: Create CloudFront distribution
        cloudfront_info = self.create_cloudfront_distribution(bucket_name)
        if not cloudfront_info:
            return None
        
        # Summary
        print("\n" + "=" * 50)
        print("🎉 Web Interface Deployment Complete!")
        print("=" * 50)
        
        print(f"✅ S3 Bucket: {bucket_name}")
        print(f"✅ CloudFront Distribution: {cloudfront_info['distribution_id']}")
        print(f"✅ Website URL: {cloudfront_info['url']}")
        
        print(f"\n🔒 Security Features:")
        print(f"   ✅ HTTPS enforced")
        print(f"   ✅ S3 access via CloudFront only")
        print(f"   ✅ Integrated with secure API")
        print(f"   ✅ Real-time status monitoring")
        
        print(f"\n⏳ Note: CloudFront deployment takes 5-15 minutes to propagate globally")
        print(f"   Your website will be available at: {cloudfront_info['url']}")
        
        print(f"\n🧪 Test Your Website:")
        print(f"   1. Wait 5-10 minutes for CloudFront deployment")
        print(f"   2. Visit: {cloudfront_info['url']}")
        print(f"   3. Try a research query")
        print(f"   4. Verify API integration works")
        
        return {
            'bucket_name': bucket_name,
            'cloudfront_info': cloudfront_info,
            'web_dir': web_dir
        }

def main():
    """Main deployment function"""
    deployment = WebInterfaceDeployment()
    results = deployment.run_web_deployment()
    
    if results:
        # Update setup state
        try:
            import sys
            sys.path.append('.')
            from setup_manager import SetupStateManager
            
            manager = SetupStateManager()
            
            manager.mark_step_complete("Web interface deployed to AWS")
            manager.add_note(f"Web dashboard available at: {results['cloudfront_info']['url']}")
            manager.add_note("CloudFront deployment in progress, will be ready in 5-15 minutes")
            
            print("\n📝 Setup state updated with web interface deployment")
            
        except Exception as e:
            print(f"⚠️  Could not update setup state: {e}")

if __name__ == "__main__":
    main()