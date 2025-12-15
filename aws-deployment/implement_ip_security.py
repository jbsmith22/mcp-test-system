#!/usr/bin/env python3
"""
Implement IP-based security for the NEJM Research Assistant
"""

import boto3
import json
import requests

def get_current_ip():
    """Get the current public IP address"""
    try:
        response = requests.get('https://ipinfo.io/ip', timeout=10)
        return response.text.strip()
    except:
        try:
            response = requests.get('https://api.ipify.org', timeout=10)
            return response.text.strip()
        except:
            return None

def create_s3_ip_policy(bucket_name, allowed_ips):
    """Create S3 bucket policy with IP restrictions"""
    
    # Convert single IP to list
    if isinstance(allowed_ips, str):
        allowed_ips = [allowed_ips]
    
    # Add /32 CIDR notation for single IPs
    ip_conditions = []
    for ip in allowed_ips:
        if '/' not in ip:
            ip_conditions.append(f"{ip}/32")
        else:
            ip_conditions.append(ip)
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "IPRestriction",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
                "Condition": {
                    "NotIpAddress": {
                        "aws:SourceIp": ip_conditions
                    }
                }
            },
            {
                "Sid": "AllowAuthorizedIPs",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
                "Condition": {
                    "IpAddress": {
                        "aws:SourceIp": ip_conditions
                    }
                }
            }
        ]
    }
    
    return policy

def create_api_gateway_ip_policy(api_id, allowed_ips):
    """Create API Gateway resource policy with IP restrictions"""
    
    # Convert single IP to list
    if isinstance(allowed_ips, str):
        allowed_ips = [allowed_ips]
    
    # Add /32 CIDR notation for single IPs
    ip_conditions = []
    for ip in allowed_ips:
        if '/' not in ip:
            ip_conditions.append(f"{ip}/32")
        else:
            ip_conditions.append(ip)
    
    # Get account ID
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": f"arn:aws:execute-api:us-east-1:{account_id}:{api_id}/*",
                "Condition": {
                    "IpAddress": {
                        "aws:SourceIp": ip_conditions
                    }
                }
            }
        ]
    }
    
    return policy

def apply_s3_security(bucket_name, allowed_ips):
    """Apply IP security to S3 bucket"""
    
    s3_client = boto3.client('s3')
    
    try:
        print(f"🔒 Applying IP security to S3 bucket: {bucket_name}")
        
        # Create and apply bucket policy
        policy = create_s3_ip_policy(bucket_name, allowed_ips)
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(policy, indent=2)
        )
        
        print(f"✅ S3 bucket policy applied")
        print(f"   Allowed IPs: {', '.join(allowed_ips)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying S3 security: {e}")
        return False

def apply_api_gateway_security(api_id, allowed_ips):
    """Apply IP security to API Gateway"""
    
    apigateway_client = boto3.client('apigateway')
    
    try:
        print(f"🔒 Applying IP security to API Gateway: {api_id}")
        
        # Create and apply resource policy
        policy = create_api_gateway_ip_policy(api_id, allowed_ips)
        
        apigateway_client.update_rest_api(
            restApiId=api_id,
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/policy',
                    'value': json.dumps(policy)
                }
            ]
        )
        
        # Deploy the changes
        apigateway_client.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Apply IP security restrictions'
        )
        
        print(f"✅ API Gateway resource policy applied")
        print(f"   Allowed IPs: {', '.join(allowed_ips)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying API Gateway security: {e}")
        return False

def update_lambda_ip_validation(function_name, allowed_ips):
    """Update Lambda function with IP validation"""
    
    lambda_client = boto3.client('lambda')
    
    try:
        print(f"🔒 Updating Lambda IP validation: {function_name}")
        
        # Get current environment variables
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        # Update IP allowlist
        env_vars['ALLOWED_IPS'] = ','.join(allowed_ips)
        env_vars['IP_RESTRICTION'] = 'true'
        
        # Update function configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': env_vars}
        )
        
        print(f"✅ Lambda IP validation updated")
        print(f"   Allowed IPs: {', '.join(allowed_ips)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda IP validation: {e}")
        return False

def get_security_status():
    """Get current security configuration status"""
    
    try:
        # Check S3 bucket policy
        s3_client = boto3.client('s3')
        bucket_name = 'nejm-research-web-interface'
        
        try:
            policy_response = s3_client.get_bucket_policy(Bucket=bucket_name)
            s3_policy = json.loads(policy_response['Policy'])
            s3_secured = True
            
            # Extract allowed IPs from policy
            s3_ips = []
            for statement in s3_policy.get('Statement', []):
                if 'Condition' in statement and 'IpAddress' in statement['Condition']:
                    ips = statement['Condition']['IpAddress'].get('aws:SourceIp', [])
                    if isinstance(ips, list):
                        s3_ips.extend(ips)
                    else:
                        s3_ips.append(ips)
                elif 'Condition' in statement and 'NotIpAddress' in statement['Condition']:
                    # This is a deny policy, so we need to infer allowed IPs differently
                    continue
            
        except:
            s3_secured = False
            s3_ips = []
        
        # Check API Gateway policy
        apigateway_client = boto3.client('apigateway')
        api_id = 'lwi6jeeczi'
        
        try:
            api_response = apigateway_client.get_rest_api(restApiId=api_id)
            api_policy = api_response.get('policy')
            
            if api_policy:
                # Handle double-escaped JSON from AWS API
                if isinstance(api_policy, str) and '\\' in api_policy:
                    # First decode the JSON string
                    try:
                        api_policy_obj = json.loads(api_policy)
                    except json.JSONDecodeError:
                        # If that fails, try manual cleanup
                        clean_policy = api_policy.replace('\\"', '"').replace('\\/', '/')
                        api_policy_obj = json.loads(clean_policy)
                else:
                    api_policy_obj = json.loads(api_policy) if isinstance(api_policy, str) else api_policy
                api_secured = True
                
                # Extract allowed IPs
                api_ips = []
                for statement in api_policy_obj.get('Statement', []):
                    if 'Condition' in statement and 'IpAddress' in statement['Condition']:
                        source_ips = statement['Condition']['IpAddress'].get('aws:SourceIp', [])
                        if isinstance(source_ips, list):
                            api_ips.extend(source_ips)
                        else:
                            api_ips.append(source_ips)
            else:
                api_secured = False
                api_ips = []
                
        except:
            api_secured = False
            api_ips = []
        
        # Check Lambda configuration
        lambda_client = boto3.client('lambda')
        function_name = 'nejm-research-assistant'
        
        try:
            lambda_response = lambda_client.get_function_configuration(FunctionName=function_name)
            env_vars = lambda_response.get('Environment', {}).get('Variables', {})
            
            lambda_secured = env_vars.get('IP_RESTRICTION', 'false').lower() == 'true'
            lambda_ips = env_vars.get('ALLOWED_IPS', '').split(',') if env_vars.get('ALLOWED_IPS') else []
            
        except:
            lambda_secured = False
            lambda_ips = []
        
        return {
            's3': {
                'secured': s3_secured,
                'ips': [ip.replace('/32', '') for ip in s3_ips]
            },
            'api_gateway': {
                'secured': api_secured,
                'ips': [ip.replace('/32', '') for ip in api_ips]
            },
            'lambda': {
                'secured': lambda_secured,
                'ips': [ip.strip() for ip in lambda_ips if ip.strip()]
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting security status: {e}")
        return None

def main():
    print("🔐 NEJM Research Assistant - IP Security Implementation")
    print("=" * 60)
    
    # Get current IP
    current_ip = get_current_ip()
    if not current_ip:
        print("❌ Could not determine current IP address")
        return False
    
    print(f"📍 Current IP Address: {current_ip}")
    
    # Configuration
    bucket_name = 'nejm-research-web-interface'
    api_id = 'lwi6jeeczi'
    function_name = 'nejm-research-assistant'
    allowed_ips = [current_ip]  # Start with current IP
    
    print(f"\n🎯 Implementing security for:")
    print(f"   S3 Bucket: {bucket_name}")
    print(f"   API Gateway: {api_id}")
    print(f"   Lambda Function: {function_name}")
    print(f"   Allowed IPs: {', '.join(allowed_ips)}")
    
    # Apply security measures
    success_count = 0
    
    # 1. Secure S3 bucket
    if apply_s3_security(bucket_name, allowed_ips):
        success_count += 1
    
    # 2. Secure API Gateway
    if apply_api_gateway_security(api_id, allowed_ips):
        success_count += 1
    
    # 3. Update Lambda validation
    if update_lambda_ip_validation(function_name, allowed_ips):
        success_count += 1
    
    print(f"\n📊 Security Implementation Results:")
    print(f"   ✅ Successfully secured: {success_count}/3 services")
    
    if success_count == 3:
        print(f"\n🎉 Security implementation complete!")
        print(f"🔒 Your NEJM Research Assistant is now secured to IP: {current_ip}")
        print(f"🌐 Website: http://nejm-research-web-interface.s3-website-us-east-1.amazonaws.com")
        print(f"⚠️  Only accessible from your current IP address")
        
        # Show security status
        print(f"\n🔍 Current Security Status:")
        status = get_security_status()
        if status:
            for service, config in status.items():
                secured_status = "🔒 SECURED" if config['secured'] else "🔓 OPEN"
                print(f"   {service.upper()}: {secured_status}")
                if config['ips']:
                    print(f"      Allowed IPs: {', '.join(config['ips'])}")
        
        return True
    else:
        print(f"\n⚠️  Partial security implementation - some services may still be open")
        return False

if __name__ == "__main__":
    main()