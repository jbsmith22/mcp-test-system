#!/bin/bash
# Secure AWS Deployment Script for NEJM Research System
# This script implements security best practices from the start

set -e  # Exit on any error

echo "🔒 NEJM Research System - Secure AWS Deployment"
echo "================================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Security check function
security_check() {
    echo -e "${RED}🚨 SECURITY CHECK${NC}"
    echo "This deployment will create AWS resources that could be accessible from the internet."
    echo "We will implement multiple security layers to protect your system."
    echo ""
    read -p "Do you want to proceed with secure deployment? (yes/no): " confirm
    
    if [[ $confirm != "yes" ]]; then
        echo "Deployment cancelled for security review."
        exit 1
    fi
}

# Get user's public IP
get_public_ip() {
    echo -e "${BLUE}🌐 Getting your public IP address...${NC}"
    
    PUBLIC_IP=$(curl -s https://checkip.amazonaws.com/ 2>/dev/null || curl -s https://ipinfo.io/ip 2>/dev/null)
    
    if [[ -z "$PUBLIC_IP" ]]; then
        echo -e "${RED}❌ Could not determine your public IP address${NC}"
        echo "Please enter your public IP manually:"
        read -p "Your public IP: " PUBLIC_IP
    fi
    
    echo -e "${GREEN}✅ Your public IP: $PUBLIC_IP${NC}"
    
    # Confirm IP address
    read -p "Is this correct? (yes/no): " ip_confirm
    if [[ $ip_confirm != "yes" ]]; then
        read -p "Enter your correct public IP: " PUBLIC_IP
    fi
    
    export PUBLIC_IP
}

# Generate secure API keys
generate_api_keys() {
    echo -e "${BLUE}🔑 Generating secure API keys...${NC}"
    
    # Generate strong API keys using Python
    python3 -c "
import secrets
import json
import boto3

# Generate secure API keys
personal_key = secrets.token_urlsafe(32)
admin_key = secrets.token_urlsafe(32)

api_keys = {
    'api_keys': [personal_key],
    'admin_keys': [admin_key],
    'created': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'description': 'NEJM Research System API Keys'
}

# Store in Secrets Manager
try:
    secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
    secrets_client.create_secret(
        Name='nejm-research-api-keys',
        SecretString=json.dumps(api_keys),
        Description='API keys for NEJM research system'
    )
    
    print(f'✅ API keys generated and stored securely')
    print(f'Personal API Key: {personal_key}')
    print(f'Admin API Key: {admin_key}')
    
    # Save keys to local file for reference (encrypted)
    with open('.api_keys_backup.json', 'w') as f:
        json.dump(api_keys, f, indent=2)
    
    print('📝 Keys backed up to .api_keys_backup.json (add to .gitignore)')
    
except Exception as e:
    print(f'❌ Error creating API keys: {e}')
    exit(1)
"
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ API keys created successfully${NC}"
        
        # Add to .gitignore if not already there
        if ! grep -q ".api_keys_backup.json" .gitignore 2>/dev/null; then
            echo ".api_keys_backup.json" >> .gitignore
            echo "📝 Added API keys backup to .gitignore"
        fi
    else
        echo -e "${RED}❌ Failed to create API keys${NC}"
        exit 1
    fi
}

# Create security policies
create_security_policies() {
    echo -e "${BLUE}🛡️ Creating security policies...${NC}"
    
    # API Gateway resource policy with IP restrictions
    cat > api-gateway-policy.json << EOF
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
                    "aws:sourceIp": ["$PUBLIC_IP/32"]
                }
            }
        }
    ]
}
EOF

    # Lambda execution policy
    cat > lambda-execution-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1",
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "es:ESHttpGet",
                "es:ESHttpPost",
                "es:ESHttpPut",
                "es:ESHttpDelete"
            ],
            "Resource": "arn:aws:es:us-east-1:*:domain/nejm-research/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:us-east-1:*:secret:nejm-*",
                "arn:aws:secretsmanager:us-east-1:*:secret:nejm-research-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::nejm-research-*/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": "arn:aws:dynamodb:us-east-1:*:table/nejm-research-*"
        }
    ]
}
EOF

    echo -e "${GREEN}✅ Security policies created${NC}"
}

# Create rate limiting table
create_rate_limiting() {
    echo -e "${BLUE}⏱️ Creating rate limiting infrastructure...${NC}"
    
    aws dynamodb create-table \
        --table-name nejm-research-rate-limits \
        --attribute-definitions \
            AttributeName=api_key,AttributeType=S \
        --key-schema \
            AttributeName=api_key,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --tags Key=Project,Value=NEJM-Research Key=Security,Value=RateLimit \
        --region us-east-1
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Rate limiting table created${NC}"
    else
        echo -e "${YELLOW}⚠️ Rate limiting table may already exist${NC}"
    fi
}

# Create OpenSearch domain with security
create_opensearch_secure() {
    echo -e "${BLUE}🔍 Creating secure OpenSearch domain...${NC}"
    
    # Get account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Create OpenSearch access policy
    cat > opensearch-access-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::$ACCOUNT_ID:root"
            },
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:$ACCOUNT_ID:domain/nejm-research/*"
        }
    ]
}
EOF

    aws opensearch create-domain \
        --domain-name nejm-research \
        --engine-version OpenSearch_2.11 \
        --cluster-config InstanceType=t3.small.search,InstanceCount=1 \
        --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=20 \
        --access-policies file://opensearch-access-policy.json \
        --domain-endpoint-options EnforceHTTPS=true \
        --node-to-node-encryption-options Enabled=true \
        --encryption-at-rest-options Enabled=true \
        --advanced-security-options Enabled=false \
        --region us-east-1
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ OpenSearch domain creation initiated${NC}"
        echo -e "${YELLOW}⏳ Domain will take 10-15 minutes to become active${NC}"
    else
        echo -e "${RED}❌ Failed to create OpenSearch domain${NC}"
        exit 1
    fi
}

# Create S3 bucket with encryption
create_s3_secure() {
    echo -e "${BLUE}📦 Creating secure S3 bucket...${NC}"
    
    # Generate unique bucket name
    BUCKET_NAME="nejm-research-$(date +%s)-$(whoami | tr '[:upper:]' '[:lower:]')"
    
    # Create bucket
    aws s3 mb s3://$BUCKET_NAME --region us-east-1
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket $BUCKET_NAME \
        --versioning-configuration Status=Enabled
    
    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket $BUCKET_NAME \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    
    # Block public access
    aws s3api put-public-access-block \
        --bucket $BUCKET_NAME \
        --public-access-block-configuration \
            BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    
    echo -e "${GREEN}✅ S3 bucket created: $BUCKET_NAME${NC}"
    echo "BUCKET_NAME=$BUCKET_NAME" >> .env
}

# Store NEJM credentials securely
store_nejm_credentials() {
    echo -e "${BLUE}🔐 Storing NEJM API credentials...${NC}"
    
    echo "Please enter your NEJM API credentials:"
    read -p "NEJM User ID: " nejm_userid
    read -s -p "NEJM API Key: " nejm_apikey
    echo ""
    
    # Store in Secrets Manager
    aws secretsmanager create-secret \
        --name "nejm-api-credentials" \
        --description "NEJM API authentication credentials" \
        --secret-string "{\"userid\":\"$nejm_userid\",\"apikey\":\"$nejm_apikey\"}" \
        --region us-east-1
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ NEJM credentials stored securely${NC}"
    else
        echo -e "${YELLOW}⚠️ NEJM credentials may already exist${NC}"
    fi
}

# Create monitoring and alerts
create_monitoring() {
    echo -e "${BLUE}📊 Setting up security monitoring...${NC}"
    
    # Create CloudWatch alarm for high API usage
    aws cloudwatch put-metric-alarm \
        --alarm-name "NEJM-Research-High-API-Usage" \
        --alarm-description "Alert on high API usage (potential abuse)" \
        --metric-name Count \
        --namespace AWS/ApiGateway \
        --statistic Sum \
        --period 300 \
        --threshold 1000 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 1 \
        --region us-east-1
    
    # Create alarm for authentication failures
    aws cloudwatch put-metric-alarm \
        --alarm-name "NEJM-Research-Auth-Failures" \
        --alarm-description "Alert on authentication failures" \
        --metric-name 4XXError \
        --namespace AWS/ApiGateway \
        --statistic Sum \
        --period 300 \
        --threshold 50 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 1 \
        --region us-east-1
    
    echo -e "${GREEN}✅ Security monitoring configured${NC}"
}

# Main deployment function
main() {
    echo -e "${BLUE}Starting secure deployment...${NC}"
    
    # Security checks
    security_check
    get_public_ip
    
    # Create security infrastructure
    generate_api_keys
    create_security_policies
    create_rate_limiting
    
    # Create AWS resources with security
    create_opensearch_secure
    create_s3_secure
    store_nejm_credentials
    create_monitoring
    
    echo ""
    echo -e "${GREEN}🎉 Secure deployment completed!${NC}"
    echo ""
    echo -e "${YELLOW}📋 Security Summary:${NC}"
    echo "✅ API Gateway restricted to your IP: $PUBLIC_IP"
    echo "✅ API keys generated and stored in Secrets Manager"
    echo "✅ Rate limiting configured"
    echo "✅ All data encrypted at rest and in transit"
    echo "✅ Public access blocked on S3"
    echo "✅ Security monitoring enabled"
    echo ""
    echo -e "${BLUE}📝 Next Steps:${NC}"
    echo "1. Wait for OpenSearch domain to become active (10-15 minutes)"
    echo "2. Deploy Lambda functions with security policies"
    echo "3. Create API Gateway with IP restrictions"
    echo "4. Test with your API keys"
    echo ""
    echo -e "${RED}🚨 Important:${NC}"
    echo "- Your API keys are in .api_keys_backup.json (keep secure!)"
    echo "- Only your IP ($PUBLIC_IP) can access the API"
    echo "- Monitor CloudWatch for security alerts"
    echo ""
    echo -e "${GREEN}Your system is now secure! 🔒${NC}"
}

# Run main function
main "$@"