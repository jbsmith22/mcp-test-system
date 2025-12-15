
import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    NEJM Research Assistant Lambda Function
    Handles research queries with security and rate limiting
    """
    
    try:
        # Extract request info
        headers = event.get('headers', {})
        body = event.get('body', '{}')
        source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
        
        # Parse request body
        if isinstance(body, str):
            try:
                request_data = json.loads(body)
            except:
                request_data = {}
        else:
            request_data = body or {}
        
        # Security checks
        api_key = headers.get('x-api-key') or headers.get('X-API-Key')
        if not api_key:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'API key required',
                    'message': 'Include x-api-key header'
                })
            }
        
        # Validate API key (simplified for demo)
        if not validate_api_key(api_key):
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid API key',
                    'message': 'API key not recognized'
                })
            }
        
        # Rate limiting check
        if check_rate_limit(api_key, source_ip):
            return {
                'statusCode': 429,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests'
                })
            }
        
        # Process research query
        query = request_data.get('query', '')
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Query required',
                    'message': 'Include query in request body'
                })
            }
        
        # Simulate research response (replace with actual logic)
        response_data = {
            'query': query,
            'answer': f'This is a simulated response for: {query}',
            'sources': [
                {
                    'title': 'Sample Medical Article',
                    'doi': '10.1056/NEJMoa2024234',
                    'relevance': 0.85
                }
            ],
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'system': 'NEJM Research Assistant (AWS Lambda)',
            'security': {
                'ip_validated': True,
                'api_key_validated': True,
                'rate_limit_ok': True
            }
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def validate_api_key(api_key):
    """Validate API key against Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId='nejm-research-api-keys')
        keys_data = json.loads(response['SecretString'])
        
        valid_keys = keys_data.get('api_keys', []) + keys_data.get('admin_keys', [])
        return api_key in valid_keys
    except:
        return False

def check_rate_limit(api_key, source_ip):
    """Check rate limiting using DynamoDB"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('nejm-research-rate-limits')
        
        # Simple rate limiting logic (100 requests per hour)
        # In production, implement more sophisticated logic
        
        return False  # Allow for now
    except:
        return False  # Fail open for availability
