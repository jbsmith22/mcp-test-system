#!/usr/bin/env python3
"""
Security Validation Script for NEJM Research System
Checks all security configurations and identifies potential vulnerabilities
"""

import boto3
import json
import requests
from typing import Dict, List, Tuple
from datetime import datetime

class SecurityValidator:
    def __init__(self):
        self.session = boto3.Session(region_name='us-east-1')
        self.results = []
        
    def log_result(self, check: str, status: str, message: str, severity: str = "INFO"):
        """Log security check result"""
        self.results.append({
            'timestamp': datetime.utcnow().isoformat(),
            'check': check,
            'status': status,
            'message': message,
            'severity': severity
        })
        
        # Color coding for output
        colors = {
            'PASS': '\033[92m✅',
            'FAIL': '\033[91m❌',
            'WARN': '\033[93m⚠️',
            'INFO': '\033[94mℹ️'
        }
        
        color = colors.get(status, '\033[0m')
        print(f"{color} {check}: {message}\033[0m")
    
    def check_api_gateway_security(self):
        """Check API Gateway security configuration"""
        print("\n🔍 Checking API Gateway Security...")
        
        try:
            client = self.session.client('apigateway')
            apis = client.get_rest_apis()
            
            nejm_apis = [api for api in apis['items'] if 'nejm' in api['name'].lower()]
            
            if not nejm_apis:
                self.log_result("API Gateway", "INFO", "No NEJM APIs found yet", "INFO")
                return
            
            for api in nejm_apis:
                api_id = api['id']
                
                # Check resource policy
                try:
                    policy = client.get_rest_api(restApiId=api_id).get('policy')
                    if policy:
                        policy_doc = json.loads(policy)
                        
                        # Check for IP restrictions
                        has_ip_restriction = False
                        for statement in policy_doc.get('Statement', []):
                            condition = statement.get('Condition', {})
                            if 'IpAddress' in condition or 'aws:sourceIp' in condition.get('IpAddress', {}):
                                has_ip_restriction = True
                                break
                        
                        if has_ip_restriction:
                            self.log_result("API IP Restriction", "PASS", f"API {api['name']} has IP restrictions")
                        else:
                            self.log_result("API IP Restriction", "FAIL", f"API {api['name']} lacks IP restrictions", "HIGH")
                    else:
                        self.log_result("API Resource Policy", "FAIL", f"API {api['name']} has no resource policy", "HIGH")
                
                except Exception as e:
                    self.log_result("API Gateway Check", "WARN", f"Could not check API policy: {e}")
        
        except Exception as e:
            self.log_result("API Gateway", "FAIL", f"Could not access API Gateway: {e}", "HIGH")
    
    def check_opensearch_security(self):
        """Check OpenSearch security configuration"""
        print("\n🔍 Checking OpenSearch Security...")
        
        try:
            client = self.session.client('opensearch')
            domains = client.list_domain_names()
            
            nejm_domains = [d for d in domains['DomainNames'] if 'nejm' in d['DomainName'].lower()]
            
            if not nejm_domains:
                self.log_result("OpenSearch", "INFO", "No NEJM OpenSearch domains found yet", "INFO")
                return
            
            for domain in nejm_domains:
                domain_name = domain['DomainName']
                
                try:
                    domain_config = client.describe_domain(DomainName=domain_name)
                    config = domain_config['DomainStatus']
                    
                    # Check encryption at rest
                    encryption_at_rest = config.get('EncryptionAtRestOptions', {}).get('Enabled', False)
                    if encryption_at_rest:
                        self.log_result("OpenSearch Encryption", "PASS", f"Domain {domain_name} has encryption at rest")
                    else:
                        self.log_result("OpenSearch Encryption", "FAIL", f"Domain {domain_name} lacks encryption at rest", "MEDIUM")
                    
                    # Check node-to-node encryption
                    node_encryption = config.get('NodeToNodeEncryptionOptions', {}).get('Enabled', False)
                    if node_encryption:
                        self.log_result("OpenSearch Node Encryption", "PASS", f"Domain {domain_name} has node-to-node encryption")
                    else:
                        self.log_result("OpenSearch Node Encryption", "FAIL", f"Domain {domain_name} lacks node-to-node encryption", "MEDIUM")
                    
                    # Check HTTPS enforcement
                    https_required = config.get('DomainEndpointOptions', {}).get('EnforceHTTPS', False)
                    if https_required:
                        self.log_result("OpenSearch HTTPS", "PASS", f"Domain {domain_name} enforces HTTPS")
                    else:
                        self.log_result("OpenSearch HTTPS", "FAIL", f"Domain {domain_name} does not enforce HTTPS", "HIGH")
                    
                    # Check access policy
                    access_policies = config.get('AccessPolicies')
                    if access_policies:
                        policy = json.loads(access_policies)
                        
                        # Check for overly permissive policies
                        for statement in policy.get('Statement', []):
                            principal = statement.get('Principal', {})
                            if principal == '*' or principal.get('AWS') == '*':
                                resource = statement.get('Resource', '')
                                if not any(condition in statement.get('Condition', {}) for condition in ['IpAddress', 'aws:sourceIp']):
                                    self.log_result("OpenSearch Access Policy", "FAIL", f"Domain {domain_name} has overly permissive access policy", "HIGH")
                                else:
                                    self.log_result("OpenSearch Access Policy", "PASS", f"Domain {domain_name} has conditional access restrictions")
                    
                except Exception as e:
                    self.log_result("OpenSearch Domain Check", "WARN", f"Could not check domain {domain_name}: {e}")
        
        except Exception as e:
            self.log_result("OpenSearch", "FAIL", f"Could not access OpenSearch: {e}", "HIGH")
    
    def check_s3_security(self):
        """Check S3 bucket security"""
        print("\n🔍 Checking S3 Security...")
        
        try:
            client = self.session.client('s3')
            buckets = client.list_buckets()
            
            nejm_buckets = [b for b in buckets['Buckets'] if 'nejm' in b['Name'].lower()]
            
            if not nejm_buckets:
                self.log_result("S3 Buckets", "INFO", "No NEJM S3 buckets found yet", "INFO")
                return
            
            for bucket in nejm_buckets:
                bucket_name = bucket['Name']
                
                try:
                    # Check public access block
                    try:
                        pab = client.get_public_access_block(Bucket=bucket_name)
                        config = pab['PublicAccessBlockConfiguration']
                        
                        if all([
                            config.get('BlockPublicAcls', False),
                            config.get('IgnorePublicAcls', False),
                            config.get('BlockPublicPolicy', False),
                            config.get('RestrictPublicBuckets', False)
                        ]):
                            self.log_result("S3 Public Access", "PASS", f"Bucket {bucket_name} blocks all public access")
                        else:
                            self.log_result("S3 Public Access", "FAIL", f"Bucket {bucket_name} allows some public access", "HIGH")
                    
                    except client.exceptions.NoSuchPublicAccessBlockConfiguration:
                        self.log_result("S3 Public Access", "FAIL", f"Bucket {bucket_name} has no public access block configuration", "HIGH")
                    
                    # Check encryption
                    try:
                        encryption = client.get_bucket_encryption(Bucket=bucket_name)
                        rules = encryption['ServerSideEncryptionConfiguration']['Rules']
                        
                        if rules:
                            self.log_result("S3 Encryption", "PASS", f"Bucket {bucket_name} has server-side encryption")
                        else:
                            self.log_result("S3 Encryption", "FAIL", f"Bucket {bucket_name} lacks encryption", "MEDIUM")
                    
                    except client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                        self.log_result("S3 Encryption", "FAIL", f"Bucket {bucket_name} has no encryption configuration", "MEDIUM")
                    
                    # Check versioning
                    versioning = client.get_bucket_versioning(Bucket=bucket_name)
                    if versioning.get('Status') == 'Enabled':
                        self.log_result("S3 Versioning", "PASS", f"Bucket {bucket_name} has versioning enabled")
                    else:
                        self.log_result("S3 Versioning", "WARN", f"Bucket {bucket_name} does not have versioning enabled")
                
                except Exception as e:
                    self.log_result("S3 Bucket Check", "WARN", f"Could not check bucket {bucket_name}: {e}")
        
        except Exception as e:
            self.log_result("S3", "FAIL", f"Could not access S3: {e}", "HIGH")
    
    def check_secrets_manager(self):
        """Check Secrets Manager configuration"""
        print("\n🔍 Checking Secrets Manager...")
        
        try:
            client = self.session.client('secretsmanager')
            secrets = client.list_secrets()
            
            nejm_secrets = [s for s in secrets['SecretList'] if 'nejm' in s['Name'].lower()]
            
            if not nejm_secrets:
                self.log_result("Secrets Manager", "WARN", "No NEJM secrets found - credentials may not be stored securely")
                return
            
            for secret in nejm_secrets:
                secret_name = secret['Name']
                
                # Check if secret is encrypted
                kms_key = secret.get('KmsKeyId')
                if kms_key:
                    self.log_result("Secret Encryption", "PASS", f"Secret {secret_name} is encrypted with KMS")
                else:
                    self.log_result("Secret Encryption", "PASS", f"Secret {secret_name} uses default encryption")
                
                # Check rotation
                rotation_enabled = secret.get('RotationEnabled', False)
                if rotation_enabled:
                    self.log_result("Secret Rotation", "PASS", f"Secret {secret_name} has rotation enabled")
                else:
                    self.log_result("Secret Rotation", "INFO", f"Secret {secret_name} does not have rotation (manual rotation recommended)")
        
        except Exception as e:
            self.log_result("Secrets Manager", "FAIL", f"Could not access Secrets Manager: {e}", "HIGH")
    
    def check_lambda_security(self):
        """Check Lambda function security"""
        print("\n🔍 Checking Lambda Security...")
        
        try:
            client = self.session.client('lambda')
            functions = client.list_functions()
            
            nejm_functions = [f for f in functions['Functions'] if 'nejm' in f['FunctionName'].lower()]
            
            if not nejm_functions:
                self.log_result("Lambda Functions", "INFO", "No NEJM Lambda functions found yet", "INFO")
                return
            
            for function in nejm_functions:
                function_name = function['FunctionName']
                
                # Check environment variables for secrets
                env_vars = function.get('Environment', {}).get('Variables', {})
                
                sensitive_patterns = ['key', 'secret', 'password', 'token', 'credential']
                for var_name, var_value in env_vars.items():
                    if any(pattern in var_name.lower() for pattern in sensitive_patterns):
                        if var_value and not var_value.startswith('arn:aws:secretsmanager'):
                            self.log_result("Lambda Environment", "FAIL", f"Function {function_name} may have hardcoded secrets in environment variables", "HIGH")
                        else:
                            self.log_result("Lambda Environment", "PASS", f"Function {function_name} uses proper secret management")
                
                # Check VPC configuration
                vpc_config = function.get('VpcConfig')
                if vpc_config and vpc_config.get('SubnetIds'):
                    self.log_result("Lambda VPC", "PASS", f"Function {function_name} is deployed in VPC")
                else:
                    self.log_result("Lambda VPC", "INFO", f"Function {function_name} is not in VPC (consider for enhanced security)")
        
        except Exception as e:
            self.log_result("Lambda", "FAIL", f"Could not access Lambda: {e}", "HIGH")
    
    def check_public_ip(self):
        """Check current public IP"""
        print("\n🔍 Checking Public IP...")
        
        try:
            response = requests.get('https://checkip.amazonaws.com/', timeout=5)
            current_ip = response.text.strip()
            
            self.log_result("Public IP", "INFO", f"Your current public IP: {current_ip}")
            
            # Note: In a real deployment, you'd compare this against configured IP restrictions
            
        except Exception as e:
            self.log_result("Public IP Check", "WARN", f"Could not determine public IP: {e}")
    
    def generate_report(self):
        """Generate security report"""
        print("\n" + "="*60)
        print("🔒 SECURITY VALIDATION REPORT")
        print("="*60)
        
        # Count results by status
        counts = {'PASS': 0, 'FAIL': 0, 'WARN': 0, 'INFO': 0}
        high_severity = 0
        
        for result in self.results:
            counts[result['status']] += 1
            if result['severity'] == 'HIGH':
                high_severity += 1
        
        print(f"\n📊 Summary:")
        print(f"✅ Passed: {counts['PASS']}")
        print(f"❌ Failed: {counts['FAIL']}")
        print(f"⚠️  Warnings: {counts['WARN']}")
        print(f"ℹ️  Info: {counts['INFO']}")
        print(f"🚨 High Severity Issues: {high_severity}")
        
        if high_severity > 0:
            print(f"\n🚨 CRITICAL: {high_severity} high-severity security issues found!")
            print("Please address these before deploying to production.")
        elif counts['FAIL'] > 0:
            print(f"\n⚠️  WARNING: {counts['FAIL']} security issues found.")
            print("Consider addressing these for better security.")
        else:
            print(f"\n🎉 EXCELLENT: No critical security issues found!")
        
        # Save detailed report
        report_file = f"security_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'summary': counts,
                'high_severity_count': high_severity,
                'results': self.results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return high_severity == 0 and counts['FAIL'] == 0

def main():
    """Run security validation"""
    print("🔒 NEJM Research System - Security Validation")
    print("=" * 50)
    
    validator = SecurityValidator()
    
    # Run all security checks
    validator.check_public_ip()
    validator.check_api_gateway_security()
    validator.check_opensearch_security()
    validator.check_s3_security()
    validator.check_secrets_manager()
    validator.check_lambda_security()
    
    # Generate report
    is_secure = validator.generate_report()
    
    if is_secure:
        print("\n🔒 Your system appears to be securely configured!")
        return 0
    else:
        print("\n⚠️  Security issues detected. Please review and address.")
        return 1

if __name__ == "__main__":
    exit(main())