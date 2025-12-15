#!/bin/bash
# AWS Deployment Script for NEJM Research Assistant

set -e

echo "🚀 Deploying NEJM Research Assistant to AWS"
echo "============================================"

# Configuration
FUNCTION_NAME="nejm-research-assistant"
ROLE_NAME="nejm-research-lambda-role"
API_NAME="nejm-research-api"
REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "📋 Configuration:"
echo "  Function: $FUNCTION_NAME"
echo "  Role: $ROLE_NAME"
echo "  API: $API_NAME"
echo "  Region: $REGION"
echo "  Account: $ACCOUNT_ID"
echo ""

# Step 1: Create IAM Role
echo "🔐 Creating IAM role..."
if ! aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://aws-configs/lambda-trust-policy.json
    
    # Attach basic execution policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    # Create and attach custom policy for AWS services
    cat > custom-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "secretsmanager:GetSecretValue",
                "ssm:GetParameter",
                "s3:GetObject",
                "s3:PutObject",
                "es:ESHttpPost",
                "es:ESHttpGet"
            ],
            "Resource": "*"
        }
    ]
}
EOF
    
    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name nejm-research-policy \
        --policy-document file://custom-policy.json
    
    rm custom-policy.json
    echo "✅ IAM role created"
else
    echo "✅ IAM role already exists"
fi

# Step 2: Create deployment package
echo "📦 Creating deployment package..."
rm -rf lambda-deployment
mkdir lambda-deployment
cd lambda-deployment

# Copy application files
cp ../*.py .
cp ../requirements-aws.txt requirements.txt

# Install dependencies
pip install -r requirements.txt -t . --quiet

# Create deployment package
zip -r ../nejm-research-lambda.zip . -q
cd ..
rm -rf lambda-deployment

echo "✅ Deployment package created"

# Step 3: Create or update Lambda function
echo "🔧 Deploying Lambda function..."
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

if aws lambda get-function --function-name $FUNCTION_NAME >/dev/null 2>&1; then
    # Update existing function
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://nejm-research-lambda.zip >/dev/null
    
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout 300 \
        --memory-size 1024 \
        --environment Variables="{AWS_REGION=$REGION}" >/dev/null
    
    echo "✅ Lambda function updated"
else
    # Create new function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.12 \
        --role $ROLE_ARN \
        --handler aws_config.lambda_handler \
        --zip-file fileb://nejm-research-lambda.zip \
        --timeout 300 \
        --memory-size 1024 \
        --environment Variables="{AWS_REGION=$REGION}" >/dev/null
    
    echo "✅ Lambda function created"
fi

# Step 4: Test Lambda function
echo "🧪 Testing Lambda function..."
cat > test-event.json << EOF
{
    "query": "What are the latest developments in AI for clinical documentation?",
    "limit": 5
}
EOF

aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload file://test-event.json \
    response.json >/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Lambda function test successful"
    echo "📄 Response preview:"
    head -c 200 response.json
    echo "..."
else
    echo "❌ Lambda function test failed"
    cat response.json
fi

rm test-event.json response.json

# Step 5: Create API Gateway (optional)
echo "🌐 Setting up API Gateway..."
if ! aws apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text | grep -q .; then
    API_ID=$(aws apigateway create-rest-api \
        --name $API_NAME \
        --description "NEJM Research Assistant API" \
        --query 'id' --output text)
    
    echo "✅ API Gateway created: $API_ID"
    echo "🔗 Configure API Gateway manually in the AWS Console"
    echo "   https://console.aws.amazon.com/apigateway/home?region=$REGION#/apis/$API_ID"
else
    echo "✅ API Gateway already exists"
fi

# Cleanup
rm -f nejm-research-lambda.zip

echo ""
echo "🎉 Deployment complete!"
echo "============================================"
echo "📋 Next Steps:"
echo "1. Configure OpenSearch domain"
echo "2. Set up Secrets Manager with NEJM credentials"
echo "3. Configure API Gateway endpoints"
echo "4. Set up CloudWatch monitoring"
echo ""
echo "📖 See AWS_ARCHITECTURE_RECOMMENDATIONS.md for detailed setup"
echo "🔗 Lambda Console: https://console.aws.amazon.com/lambda/home?region=$REGION#/functions/$FUNCTION_NAME"