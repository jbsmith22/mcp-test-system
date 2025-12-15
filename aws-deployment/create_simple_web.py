#!/usr/bin/env python3
"""
Simple Web Interface Deployment
Creates S3 static website with bucket policy for IP restrictions
"""

import boto3
import json
import time
import os

def create_simple_web_interface():
    """Create simple S3 website with IP restrictions"""
    
    print("🌐 Simple Web Interface Deployment")
    print("=" * 40)
    
    session = boto3.Session(region_name='us-east-1')
    s3_client = session.client('s3')
    account_id = session.client('sts').get_caller_identity()['Account']
    your_ip = "108.20.28.24"
    api_url = "https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research"
    api_key = "YOUR_API_KEY_HERE"
    
    # Create unique bucket name
    timestamp = int(time.time())
    bucket_name = f"nejm-research-web-{timestamp}"
    
    print(f"📦 Creating S3 bucket: {bucket_name}")
    
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
        
        # Create bucket policy with IP restrictions
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {
                        "IpAddress": {
                            "aws:sourceIp": [f"{your_ip}/32"]
                        }
                    }
                }
            ]
        }
        
        # Apply bucket policy
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        # Disable public access block for website hosting
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        
        print("✅ S3 bucket configured for website hosting")
        
        # Create and upload HTML files
        create_and_upload_files(s3_client, bucket_name, api_url, api_key, your_ip)
        
        # Get website URL
        website_url = f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"
        
        print(f"\n🎉 Web Interface Deployed Successfully!")
        print(f"=" * 50)
        print(f"✅ S3 Bucket: {bucket_name}")
        print(f"✅ Website URL: {website_url}")
        print(f"🔒 IP Restricted to: {your_ip}")
        print(f"🔗 Connected to API: {api_url}")
        
        print(f"\n🧪 Test Your Website:")
        print(f"1. Visit: {website_url}")
        print(f"2. Try a research query")
        print(f"3. Verify security (should work from your IP only)")
        
        return {
            'bucket_name': bucket_name,
            'website_url': website_url
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def create_and_upload_files(s3_client, bucket_name, api_url, api_key, your_ip):
    """Create and upload web interface files"""
    
    print("📝 Creating and uploading web files...")
    
    # Simple HTML dashboard
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEJM Research Assistant - AWS Deployment</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1000px;
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
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .security-badge {{
            background: #27ae60;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-top: 15px;
            display: inline-block;
        }}
        .main-content {{ padding: 40px; }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .status-card {{
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        .status-icon {{ font-size: 2em; margin-bottom: 10px; }}
        .status-title {{ font-weight: bold; margin-bottom: 5px; }}
        .status-value {{ color: #27ae60; font-weight: bold; }}
        .search-section {{ margin-bottom: 30px; }}
        .search-box {{
            width: 100%;
            padding: 15px;
            font-size: 1.1em;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 15px;
            box-sizing: border-box;
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
        .search-btn:hover {{ transform: translateY(-2px); }}
        .search-btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
        .results {{ margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; display: none; }}
        .result-item {{ background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; }}
        .error {{ background: #e74c3c; color: white; padding: 15px; border-radius: 8px; margin-top: 15px; display: none; }}
        .loading {{ text-align: center; padding: 20px; }}
        .spinner {{
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 NEJM Research Assistant</h1>
            <p>Secure AWS Deployment - AI-Powered Medical Literature Search</p>
            <div class="security-badge">🔒 Secure • IP-Restricted • Encrypted</div>
        </div>
        
        <div class="main-content">
            <div class="status-grid">
                <div class="status-card">
                    <div class="status-icon">🔒</div>
                    <div class="status-title">Security</div>
                    <div class="status-value">Protected</div>
                </div>
                <div class="status-card">
                    <div class="status-icon">🌐</div>
                    <div class="status-title">API Status</div>
                    <div class="status-value" id="api-status">Checking...</div>
                </div>
                <div class="status-card">
                    <div class="status-icon">📊</div>
                    <div class="status-title">Your IP</div>
                    <div class="status-value">{your_ip}</div>
                </div>
                <div class="status-card">
                    <div class="status-icon">⚡</div>
                    <div class="status-title">Response Time</div>
                    <div class="status-value" id="response-time">-</div>
                </div>
            </div>
            
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
                
                <div id="error-message" class="error"></div>
            </div>
            
            <div id="results-section" class="results">
                <h3>📋 Research Results</h3>
                <div id="results-content"></div>
            </div>
        </div>
    </div>

    <script>
        const API_URL = '{api_url}';
        const API_KEY = '{api_key}';
        
        // Check API status on load
        window.addEventListener('load', checkApiStatus);
        
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
                }}
            }} catch (error) {{
                statusElement.textContent = 'Offline';
                statusElement.style.color = '#e74c3c';
            }}
        }}
        
        async function performSearch() {{
            const query = document.getElementById('search-query').value.trim();
            const searchBtn = document.getElementById('search-btn');
            const resultsSection = document.getElementById('results-section');
            const resultsContent = document.getElementById('results-content');
            const errorMessage = document.getElementById('error-message');
            
            if (!query) {{
                showError('Please enter a research question.');
                return;
            }}
            
            searchBtn.disabled = true;
            searchBtn.textContent = '🔍 Searching...';
            errorMessage.style.display = 'none';
            resultsSection.style.display = 'block';
            
            resultsContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>Analyzing medical literature...</p></div>';
            
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
                    <h4>📊 Query Analysis</h4>
                    <p><strong>Query:</strong> ${{data.query}}</p>
                    <p><strong>Response Time:</strong> ${{responseTime}}ms</p>
                    <p><strong>System:</strong> ${{data.system || 'NEJM Research Assistant'}}</p>
                </div>
                
                <div class="result-item">
                    <h4>🧠 AI Response</h4>
                    <p>${{data.answer}}</p>
                </div>
            `;
            
            if (data.sources && data.sources.length > 0) {{
                html += '<div class="result-item"><h4>📚 Sources</h4>';
                data.sources.forEach((source, index) => {{
                    html += `<p><strong>${{index + 1}}.</strong> ${{source.title}} (DOI: ${{source.doi}}, Relevance: ${{(source.relevance * 100).toFixed(1)}}%)</p>`;
                }});
                html += '</div>';
            }}
            
            if (data.security) {{
                html += `
                    <div class="result-item">
                        <h4>🔒 Security Status</h4>
                        <p>IP Validated: ${{data.security.ip_validated ? '✅' : '❌'}}</p>
                        <p>API Key Validated: ${{data.security.api_key_validated ? '✅' : '❌'}}</p>
                        <p>Rate Limit OK: ${{data.security.rate_limit_ok ? '✅' : '❌'}}</p>
                    </div>
                `;
            }}
            
            resultsContent.innerHTML = html;
            document.getElementById('response-time').textContent = responseTime + 'ms';
        }}
        
        function showError(message) {{
            const errorElement = document.getElementById('error-message');
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }}
        
        // Enter key to search
        document.getElementById('search-query').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                performSearch();
            }}
        }});
    </script>
</body>
</html>'''
    
    # Upload HTML file
    s3_client.put_object(
        Bucket=bucket_name,
        Key='index.html',
        Body=html_content.encode('utf-8'),
        ContentType='text/html'
    )
    
    # Create error page
    error_html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Access Denied - NEJM Research</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #e74c3c; color: white; }}
        .container {{ max-width: 500px; margin: 0 auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Access Denied</h1>
        <p>This NEJM Research System is IP-restricted.</p>
        <p><strong>Authorized IP:</strong> {your_ip}</p>
        <p>Access is only allowed from the authorized IP address.</p>
    </div>
</body>
</html>'''
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key='error.html',
        Body=error_html.encode('utf-8'),
        ContentType='text/html'
    )
    
    print("✅ Uploaded web interface files")

if __name__ == "__main__":
    result = create_simple_web_interface()
    
    if result:
        # Update setup state
        try:
            import sys
            sys.path.append('.')
            from setup_manager import SetupStateManager
            
            manager = SetupStateManager()
            manager.mark_step_complete("Web interface deployed to S3")
            manager.add_note(f"Web dashboard available at: {result['website_url']}")
            
            print("\n📝 Setup state updated")
            
        except Exception as e:
            print(f"⚠️  Could not update setup state: {e}")