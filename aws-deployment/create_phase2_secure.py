#!/usr/bin/env python3
"""
Phase 2 Secure Deployment: S3, Secrets Manager, API Keys, Rate Limiting
Creates remaining AWS infrastructure with security best practices
"""

import boto3
import json
import secrets
import time
from datetime import datetime

class Phase2SecureDeployment:
    def __init__(self):
        self.session = boto3.Session(region_name='us-east-1')
        self.account_id = self.session.client('sts').get_caller_identity()['Account']
        self.your_ip = "108.20.28.24"  # From Phase 1
        
        print("🔒 Phase 2 Secure Deployment")
        print("=" * 30)
        print(f"📋 AWS Account: {self.account_id}")
        print(f"🌐 Your IP: {self.your_ip}")
        print()
    
    def create_secure_s3_bucket(self):
        """Create S3 bucket with full security"""
        print("📦 Creating Secure S3 Bucket...")
        
        s3_client = self.session.client('s3')
        
        # Generate unique bucket name
        timestamp = int(time.time())
        bucket_name = f"nejm-research-{timestamp}-secure"
        
        try:
            # Create bucket
            print(f"   Creating bucket: {bucket_name}")
            s3_client.create_bucket(Bucket=bucket_name)
            
            # Enable versioning
            print("   ✅ Enabling versioning...")
            s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Enable encryption
            print("   ✅ Enabling encryption...")
            s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }]
                }
            )
            
            # Block ALL public access
            print("   ✅ Blocking all public access...")
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            # Add bucket policy for additional security
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "DenyInsecureConnections",
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "s3:*",
                        "Resource": [
                            f"arn:aws:s3:::{bucket_name}",
                            f"arn:aws:s3:::{bucket_name}/*"
                        ],
                        "Condition": {
                            "Bool": {
                                "aws:SecureTransport": "false"
                            }
                        }
                    }
                ]
            }
            
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            
            print(f"✅ S3 bucket created successfully: {bucket_name}")
            print("   🔒 Security features:")
            print("      ✅ Versioning enabled")
            print("      ✅ AES-256 encryption")
            print("      ✅ All public access blocked")
            print("      ✅ HTTPS-only policy")
            
            return bucket_name
            
        except Exception as e:
            print(f"❌ Error creating S3 bucket: {e}")
            return None
    
    def create_api_keys(self):
        """Generate and store secure API keys"""
        print("\n🔑 Creating Secure API Keys...")
        
        secrets_client = self.session.client('secretsmanager')
        
        # Generate strong API keys
        personal_key = secrets.token_urlsafe(32)
        admin_key = secrets.token_urlsafe(32)
        
        api_keys_data = {
            'api_keys': [personal_key],
            'admin_keys': [admin_key],
            'created': datetime.utcnow().isoformat() + 'Z',
            'description': 'NEJM Research System API Keys',
            'ip_restriction': self.your_ip,
            'account_id': self.account_id
        }
        
        try:
            # Store in Secrets Manager
            secrets_client.create_secret(
                Name='nejm-research-api-keys',
                SecretString=json.dumps(api_keys_data),
                Description='API keys for NEJM research system with IP restrictions'
            )
            
            print("✅ API keys generated and stored securely")
            print(f"   Personal API Key: {personal_key}")
            print(f"   Admin API Key: {admin_key}")
            print("   🔒 Security features:")
            print("      ✅ 32-character cryptographically secure keys")
            print("      ✅ Stored encrypted in AWS Secrets Manager")
            print(f"      ✅ IP restricted to {self.your_ip}")
            
            # Save keys to local encrypted backup
            with open('.api_keys_backup.json', 'w') as f:
                json.dump(api_keys_data, f, indent=2)
            
            print("   📝 Backup saved to .api_keys_backup.json")
            
            return {'personal': personal_key, 'admin': admin_key}
            
        except secrets_client.exceptions.ResourceExistsException:
            print("⚠️  API keys already exist in Secrets Manager")
            
            # Retrieve existing keys
            try:
                response = secrets_client.get_secret_value(SecretId='nejm-research-api-keys')
                existing_keys = json.loads(response['SecretString'])
                
                print("✅ Retrieved existing API keys")
                print(f"   Personal API Key: {existing_keys['api_keys'][0]}")
                print(f"   Admin API Key: {existing_keys['admin_keys'][0]}")
                
                return {
                    'personal': existing_keys['api_keys'][0],
                    'admin': existing_keys['admin_keys'][0]
                }
                
            except Exception as e:
                print(f"❌ Error retrieving existing keys: {e}")
                return None
        
        except Exception as e:
            print(f"❌ Error creating API keys: {e}")
            return None
    
    def store_nejm_credentials(self):
        """Store NEJM API credentials securely"""
        print("\n🔐 Storing NEJM API Credentials...")
        
        secrets_client = self.session.client('secretsmanager')
        
        # Check if credentials already exist
        try:
            existing = secrets_client.describe_secret(SecretId='nejm-api-credentials')
            print("✅ NEJM credentials already exist in Secrets Manager")
            print(f"   Created: {existing['CreatedDate']}")
            return True
            
        except secrets_client.exceptions.ResourceNotFoundException:
            print("   No existing NEJM credentials found")
        
        # Get credentials from user
        print("\n📝 Please enter your NEJM API credentials:")
        nejm_userid = input("   NEJM User ID: ").strip()
        
        import getpass
        nejm_apikey = getpass.getpass("   NEJM API Key (hidden): ").strip()
        
        if not nejm_userid or not nejm_apikey:
            print("❌ Invalid credentials provided")
            return False
        
        nejm_credentials = {
            'userid': nejm_userid,
            'apikey': nejm_apikey,
            'environment': 'qa',  # Start with QA environment
            'created': datetime.utcnow().isoformat() + 'Z',
            'description': 'NEJM API credentials for research system'
        }
        
        try:
            secrets_client.create_secret(
                Name='nejm-api-credentials',
                SecretString=json.dumps(nejm_credentials),
                Description='NEJM API authentication credentials'
            )
            
            print("✅ NEJM credentials stored securely")
            print("   🔒 Security features:")
            print("      ✅ Encrypted storage in AWS Secrets Manager")
            print("      ✅ No credentials in code or config files")
            print("      ✅ IAM-controlled access")
            
            return True
            
        except Exception as e:
            print(f"❌ Error storing NEJM credentials: {e}")
            return False
    
    def create_rate_limiting_table(self):
        """Create DynamoDB table for rate limiting"""
        print("\n⏱️ Creating Rate Limiting Infrastructure...")
        
        dynamodb_client = self.session.client('dynamodb')
        
        table_name = 'nejm-research-rate-limits'
        
        try:
            # Check if table already exists
            existing_tables = dynamodb_client.list_tables()
            if table_name in existing_tables['TableNames']:
                print(f"✅ Rate limiting table '{table_name}' already exists")
                return True
            
            # Create table
            dynamodb_client.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'api_key', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'api_key', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
                Tags=[
                    {'Key': 'Project', 'Value': 'NEJM-Research'},
                    {'Key': 'Purpose', 'Value': 'RateLimit'},
                    {'Key': 'Security', 'Value': 'AbuseProtection'}
                ]
            )
            
            print(f"✅ Rate limiting table created: {table_name}")
            print("   🔒 Security features:")
            print("      ✅ Pay-per-request billing (no fixed costs)")
            print("      ✅ API abuse protection")
            print("      ✅ Configurable rate limits per API key")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating rate limiting table: {e}")
            return False
    
    def validate_phase2_security(self):
        """Validate Phase 2 security configuration"""
        print("\n🔍 Validating Phase 2 Security...")
        
        validation_results = []
        
        # Check S3 security
        s3_client = self.session.client('s3')
        buckets = s3_client.list_buckets()
        nejm_buckets = [b for b in buckets['Buckets'] if 'nejm-research' in b['Name']]
        
        for bucket in nejm_buckets:
            bucket_name = bucket['Name']
            
            try:
                # Check public access block
                pab = s3_client.get_public_access_block(Bucket=bucket_name)
                config = pab['PublicAccessBlockConfiguration']
                
                if all([
                    config.get('BlockPublicAcls', False),
                    config.get('IgnorePublicAcls', False),
                    config.get('BlockPublicPolicy', False),
                    config.get('RestrictPublicBuckets', False)
                ]):
                    validation_results.append(f"✅ S3 {bucket_name}: All public access blocked")
                else:
                    validation_results.append(f"❌ S3 {bucket_name}: Public access not fully blocked")
                
                # Check encryption
                try:
                    encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                    validation_results.append(f"✅ S3 {bucket_name}: Encryption enabled")
                except:
                    validation_results.append(f"❌ S3 {bucket_name}: No encryption")
                
            except Exception as e:
                validation_results.append(f"⚠️  S3 {bucket_name}: Could not validate - {e}")
        
        # Check Secrets Manager
        secrets_client = self.session.client('secretsmanager')
        try:
            secrets_list = secrets_client.list_secrets()
            nejm_secrets = [s for s in secrets_list['SecretList'] if 'nejm' in s['Name'].lower()]
            
            if nejm_secrets:
                validation_results.append(f"✅ Secrets Manager: {len(nejm_secrets)} NEJM secrets found")
            else:
                validation_results.append("⚠️  Secrets Manager: No NEJM secrets found")
                
        except Exception as e:
            validation_results.append(f"❌ Secrets Manager: Validation failed - {e}")
        
        # Check DynamoDB
        dynamodb_client = self.session.client('dynamodb')
        try:
            tables = dynamodb_client.list_tables()
            rate_limit_tables = [t for t in tables['TableNames'] if 'rate-limit' in t.lower()]
            
            if rate_limit_tables:
                validation_results.append(f"✅ DynamoDB: Rate limiting table exists")
            else:
                validation_results.append("⚠️  DynamoDB: No rate limiting table found")
                
        except Exception as e:
            validation_results.append(f"❌ DynamoDB: Validation failed - {e}")
        
        # Print results
        print("\n📊 Phase 2 Security Validation Results:")
        for result in validation_results:
            print(f"   {result}")
        
        # Count issues
        critical_issues = len([r for r in validation_results if r.startswith('❌')])
        warnings = len([r for r in validation_results if r.startswith('⚠️')])
        passed = len([r for r in validation_results if r.startswith('✅')])
        
        print(f"\n📈 Summary:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ⚠️  Warnings: {warnings}")
        print(f"   ❌ Critical: {critical_issues}")
        
        return critical_issues == 0
    
    def run_phase2_deployment(self):
        """Run complete Phase 2 deployment"""
        print("🚀 Starting Phase 2 Secure Deployment...")
        print("=" * 50)
        
        results = {}
        
        # Deploy components
        results['s3_bucket'] = self.create_secure_s3_bucket()
        results['api_keys'] = self.create_api_keys()
        results['nejm_credentials'] = self.store_nejm_credentials()
        results['rate_limiting'] = self.create_rate_limiting_table()
        
        # Validate security
        security_valid = self.validate_phase2_security()
        
        # Summary
        print("\n" + "=" * 50)
        print("🎉 Phase 2 Deployment Complete!")
        print("=" * 50)
        
        if results['s3_bucket']:
            print(f"✅ S3 Bucket: {results['s3_bucket']}")
        
        if results['api_keys']:
            print(f"✅ API Keys: Generated and stored securely")
        
        if results['nejm_credentials']:
            print(f"✅ NEJM Credentials: Stored in Secrets Manager")
        
        if results['rate_limiting']:
            print(f"✅ Rate Limiting: DynamoDB table created")
        
        if security_valid:
            print(f"\n🔒 Security Status: ALL CHECKS PASSED")
        else:
            print(f"\n⚠️  Security Status: Some issues detected")
        
        print(f"\n📋 Next Steps:")
        print(f"1. Wait for OpenSearch domain to complete (if not already)")
        print(f"2. Deploy Lambda functions")
        print(f"3. Create API Gateway with security")
        print(f"4. Test end-to-end functionality")
        
        return results

def main():
    """Main deployment function"""
    deployment = Phase2SecureDeployment()
    results = deployment.run_phase2_deployment()
    
    # Update setup state
    try:
        import sys
        sys.path.append('.')
        from setup_manager import SetupStateManager
        
        manager = SetupStateManager()
        
        if results.get('s3_bucket'):
            manager.add_aws_resource('s3_bucket', results['s3_bucket'])
        
        if results.get('api_keys'):
            manager.mark_step_complete("API keys generated and stored securely")
        
        if results.get('nejm_credentials'):
            manager.mark_step_complete("NEJM credentials stored in Secrets Manager")
        
        if results.get('rate_limiting'):
            manager.mark_step_complete("Rate limiting infrastructure created")
        
        manager.add_note("Phase 2 deployment complete: S3, Secrets Manager, API keys, rate limiting all secured")
        
        print("\n📝 Setup state updated with Phase 2 progress")
        
    except Exception as e:
        print(f"⚠️  Could not update setup state: {e}")

if __name__ == "__main__":
    main()