# 🔒 AWS Security Strategy for NEJM Research System

## 🚨 Current Security Risks & Mitigation

### **Risk Assessment: Public Internet Exposure**

**Current Setup Risk Level**: 🔴 **HIGH** - Without proper security, your system could be:
- Publicly accessible to anyone on the internet
- Vulnerable to unauthorized access to medical literature
- Exposed to potential data breaches or misuse
- Subject to unexpected AWS costs from abuse

---

## 🛡️ Multi-Layer Security Strategy

### **Layer 1: Network Security (VPC Isolation)**

#### **Private VPC Architecture**
```
┌─────────────────────────────────────────────────────────┐
│                    Private VPC                          │
│  ┌─────────────────┐    ┌─────────────────┐            │
│  │  Private Subnet │    │  Private Subnet │            │
│  │                 │    │                 │            │
│  │  ┌───────────┐  │    │  ┌───────────┐  │            │
│  │  │OpenSearch │  │    │  │  Lambda   │  │            │
│  │  │ (Private) │  │    │  │(Private)  │  │            │
│  │  └───────────┘  │    │  └───────────┘  │            │
│  └─────────────────┘    └─────────────────┘            │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │              Public Subnet                          ││
│  │  ┌─────────────┐    ┌─────────────┐                ││
│  │  │     NAT     │    │   Bastion   │                ││
│  │  │   Gateway   │    │    Host     │                ││
│  │  └─────────────┘    └─────────────┘                ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                              │
                    ┌─────────────────┐
                    │  Internet       │
                    │  Gateway        │
                    │  (Controlled)   │
                    └─────────────────┘
```

#### **Implementation**:
```bash
# Create private VPC
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=nejm-research-vpc}]'

# Create private subnets (no direct internet access)
aws ec2 create-subnet \
    --vpc-id vpc-xxxxx \
    --cidr-block 10.0.1.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=nejm-private-1a}]'
```

### **Layer 2: API Gateway Security**

#### **Option A: Private API Gateway (Recommended)**
```yaml
# Only accessible from within VPC or via VPN
Type: AWS::ApiGateway::RestApi
Properties:
  Name: nejm-research-private-api
  Policy:
    Version: '2012-10-17'
    Statement:
      - Effect: Allow
        Principal: '*'
        Action: execute-api:Invoke
        Resource: '*'
        Condition:
          StringEquals:
            'aws:sourceVpce': 'vpce-xxxxx'  # VPC Endpoint only
```

#### **Option B: Public API with Strong Authentication**
```yaml
# Public but heavily secured
Type: AWS::ApiGateway::RestApi
Properties:
  Name: nejm-research-secure-api
  Policy:
    Version: '2012-10-17'
    Statement:
      - Effect: Allow
        Principal: '*'
        Action: execute-api:Invoke
        Resource: '*'
        Condition:
          IpAddress:
            'aws:sourceIp': 
              - 'YOUR.HOME.IP.ADDRESS/32'  # Your home IP only
              - 'YOUR.OFFICE.IP.ADDRESS/32'  # Your office IP only
```

### **Layer 3: Authentication & Authorization**

#### **API Key Authentication**
```python
# Lambda function with API key validation
import boto3
import json

def lambda_handler(event, context):
    # Validate API key
    api_key = event.get('headers', {}).get('x-api-key')
    
    if not api_key or not validate_api_key(api_key):
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    # Rate limiting
    if check_rate_limit(api_key):
        return {
            'statusCode': 429,
            'body': json.dumps({'error': 'Rate limit exceeded'})
        }
    
    # Process request
    return process_research_query(event)

def validate_api_key(api_key):
    """Validate API key against Secrets Manager"""
    secrets_client = boto3.client('secretsmanager')
    try:
        response = secrets_client.get_secret_value(
            SecretId='nejm-research-api-keys'
        )
        valid_keys = json.loads(response['SecretString'])['api_keys']
        return api_key in valid_keys
    except:
        return False
```

#### **Cognito User Pool (Advanced Option)**
```bash
# Create user pool for authenticated access
aws cognito-idp create-user-pool \
    --pool-name nejm-research-users \
    --policies '{
        "PasswordPolicy": {
            "MinimumLength": 12,
            "RequireUppercase": true,
            "RequireLowercase": true,
            "RequireNumbers": true,
            "RequireSymbols": true
        }
    }'
```

### **Layer 4: Data Protection**

#### **Encryption Configuration**
```python
# OpenSearch with encryption
{
    "DomainName": "nejm-research",
    "EncryptionAtRestOptions": {
        "Enabled": True
    },
    "NodeToNodeEncryptionOptions": {
        "Enabled": True
    },
    "DomainEndpointOptions": {
        "EnforceHTTPS": True,
        "TLSSecurityPolicy": "Policy-Min-TLS-1-2-2019-07"
    }
}

# S3 with encryption
{
    "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
            "SSEAlgorithm": "aws:kms",
            "KMSMasterKeyID": "arn:aws:kms:us-east-1:account:key/key-id"
        },
        "BucketKeyEnabled": True
    }]
}
```

---

## 🎯 Recommended Security Implementation

### **Phase 1: Secure Foundation (Start Here)**

#### **1. IP Restriction (Immediate Protection)**
```bash
# Create API Gateway with IP restrictions
cat > api-gateway-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "execute-api:Invoke",
            "Resource": "*",
            "Condition": {
                "IpAddress": {
                    "aws:sourceIp": [
                        "YOUR_HOME_IP/32",
                        "YOUR_OFFICE_IP/32"
                    ]
                }
            }
        }
    ]
}
EOF
```

#### **2. API Key Generation**
```python
# Generate secure API keys
import secrets
import json
import boto3

def create_api_keys():
    """Create secure API keys for the system"""
    
    # Generate strong API keys
    personal_key = secrets.token_urlsafe(32)
    admin_key = secrets.token_urlsafe(32)
    
    api_keys = {
        "api_keys": [personal_key],
        "admin_keys": [admin_key],
        "created": "2024-12-14",
        "description": "NEJM Research System API Keys"
    }
    
    # Store in Secrets Manager
    secrets_client = boto3.client('secretsmanager')
    secrets_client.create_secret(
        Name='nejm-research-api-keys',
        SecretString=json.dumps(api_keys),
        Description='API keys for NEJM research system'
    )
    
    print(f"Personal API Key: {personal_key}")
    print(f"Admin API Key: {admin_key}")
    print("Keys stored securely in AWS Secrets Manager")

if __name__ == "__main__":
    create_api_keys()
```

#### **3. Rate Limiting**
```python
# DynamoDB table for rate limiting
import boto3
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('nejm-research-rate-limits')
    
    def check_rate_limit(self, api_key, limit=100, window_minutes=60):
        """Check if API key has exceeded rate limit"""
        
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        try:
            response = self.table.get_item(Key={'api_key': api_key})
            
            if 'Item' not in response:
                # First request
                self.table.put_item(Item={
                    'api_key': api_key,
                    'requests': 1,
                    'window_start': window_start.isoformat(),
                    'last_request': now.isoformat()
                })
                return False
            
            item = response['Item']
            requests = item['requests']
            
            # Check if we're in the same window
            item_window_start = datetime.fromisoformat(item['window_start'])
            
            if now - item_window_start > timedelta(minutes=window_minutes):
                # New window
                self.table.put_item(Item={
                    'api_key': api_key,
                    'requests': 1,
                    'window_start': now.isoformat(),
                    'last_request': now.isoformat()
                })
                return False
            
            # Same window - check limit
            if requests >= limit:
                return True  # Rate limited
            
            # Increment counter
            self.table.update_item(
                Key={'api_key': api_key},
                UpdateExpression='SET requests = requests + :inc, last_request = :now',
                ExpressionAttributeValues={':inc': 1, ':now': now.isoformat()}
            )
            
            return False
            
        except Exception as e:
            print(f"Rate limit check failed: {e}")
            return False  # Fail open for availability
```

### **Phase 2: Network Isolation (Enhanced Security)**

#### **VPC Endpoint for Private Access**
```bash
# Create VPC endpoint for API Gateway
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-xxxxx \
    --service-name com.amazonaws.us-east-1.execute-api \
    --vpc-endpoint-type Interface \
    --subnet-ids subnet-xxxxx \
    --security-group-ids sg-xxxxx \
    --policy-document file://vpc-endpoint-policy.json
```

### **Phase 3: Advanced Authentication (Production Ready)**

#### **Cognito Integration**
```python
# Cognito JWT validation
import jwt
import requests
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        try:
            # Remove 'Bearer ' prefix
            token = token.replace('Bearer ', '')
            
            # Validate JWT token
            decoded = jwt.decode(
                token,
                get_cognito_public_key(),
                algorithms=['RS256'],
                audience='your-cognito-client-id'
            )
            
            # Add user info to request context
            request.user = decoded
            
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
```

---

## 🔍 Security Monitoring & Alerting

### **CloudWatch Alarms**
```bash
# Alert on unusual API activity
aws cloudwatch put-metric-alarm \
    --alarm-name "NEJM-Research-High-API-Usage" \
    --alarm-description "Alert on high API usage" \
    --metric-name Count \
    --namespace AWS/ApiGateway \
    --statistic Sum \
    --period 300 \
    --threshold 1000 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=ApiName,Value=nejm-research-api \
    --evaluation-periods 1

# Alert on failed authentication attempts
aws cloudwatch put-metric-alarm \
    --alarm-name "NEJM-Research-Auth-Failures" \
    --alarm-description "Alert on authentication failures" \
    --metric-name 4XXError \
    --namespace AWS/ApiGateway \
    --statistic Sum \
    --period 300 \
    --threshold 50 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1
```

### **CloudTrail Logging**
```json
{
    "TrailName": "nejm-research-audit-trail",
    "S3BucketName": "nejm-research-audit-logs",
    "IncludeGlobalServiceEvents": true,
    "IsLogging": true,
    "EnableLogFileValidation": true,
    "EventSelectors": [
        {
            "ReadWriteType": "All",
            "IncludeManagementEvents": true,
            "DataResources": [
                {
                    "Type": "AWS::S3::Object",
                    "Values": ["arn:aws:s3:::nejm-research-*/*"]
                }
            ]
        }
    ]
}
```

---

## 🎯 **Immediate Action Plan**

### **Step 1: Get Your Public IP**
```bash
# Find your current public IP
curl -s https://checkip.amazonaws.com/
# or
curl -s https://ipinfo.io/ip
```

### **Step 2: Implement IP Restrictions First**
```bash
# This should be your FIRST security step
# Replace YOUR_IP_HERE with the IP from step 1
export YOUR_PUBLIC_IP=$(curl -s https://checkip.amazonaws.com/)
echo "Your public IP: $YOUR_PUBLIC_IP"
```

### **Step 3: Create Secure API Keys**
```bash
# Generate and store API keys before deployment
python3 create_api_keys.py
```

### **Step 4: Deploy with Security**
```bash
# Deploy with security configurations
./deploy-aws-secure.sh
```

---

## ⚠️ **Security Checklist Before Deployment**

- [ ] **IP Restrictions**: API Gateway limited to your IP addresses
- [ ] **API Keys**: Generated and stored in Secrets Manager
- [ ] **Rate Limiting**: DynamoDB table created for rate limiting
- [ ] **Encryption**: All data encrypted at rest and in transit
- [ ] **Monitoring**: CloudWatch alarms configured
- [ ] **Audit Logging**: CloudTrail enabled
- [ ] **Network Security**: VPC with private subnets (optional but recommended)
- [ ] **Access Review**: No public read access to S3 buckets
- [ ] **Secrets**: No hardcoded credentials in code

**🚨 CRITICAL**: Never deploy without at least IP restrictions and API key authentication!

---

This security strategy ensures your NEJM research system remains private and secure while providing you with flexible access options.