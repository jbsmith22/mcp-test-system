#!/usr/bin/env python3
"""
AWS Configuration and Service Integration
Provides AWS service clients and configuration management for cloud deployment
"""

import boto3
import json
import os
from botocore.exceptions import ClientError
from typing import List, Dict, Optional

class AWSConfig:
    """AWS service configuration and client management"""
    
    def __init__(self, region: str = None):
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        
        # Initialize AWS clients
        self.secrets_client = boto3.client('secretsmanager', region_name=self.region)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.region)
        self.opensearch_client = boto3.client('opensearchserverless', region_name=self.region)
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.ssm_client = boto3.client('ssm', region_name=self.region)
        
        # Configuration
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.s3_bucket = os.environ.get('S3_BUCKET')
        
    def get_nejm_credentials(self) -> str:
        """Retrieve NEJM API credentials from AWS Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(
                SecretId='nejm-api-credentials'
            )
            credentials = json.loads(response['SecretString'])
            return f"{credentials['userid']}|{credentials['apikey']}"
        except ClientError as e:
            raise Exception(f"Could not retrieve NEJM credentials: {e}")
    
    def get_parameter(self, parameter_name: str) -> str:
        """Get configuration parameter from Systems Manager"""
        try:
            response = self.ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            return response['Parameter']['Value']
        except ClientError as e:
            raise Exception(f"Could not retrieve parameter {parameter_name}: {e}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get text embedding using Amazon Bedrock Titan model"""
        try:
            response = self.bedrock_client.invoke_model(
                modelId='amazon.titan-embed-text-v1',
                body=json.dumps({
                    "inputText": text
                })
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
            
        except ClientError as e:
            raise Exception(f"Could not get embedding from Bedrock: {e}")
    
    def generate_answer(self, prompt: str, model: str = 'anthropic.claude-3-sonnet-20240229-v1:0') -> str:
        """Generate answer using Amazon Bedrock language model"""
        try:
            if 'claude' in model:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            elif 'llama' in model:
                body = {
                    "prompt": prompt,
                    "max_gen_len": 4000,
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            else:
                raise ValueError(f"Unsupported model: {model}")
            
            response = self.bedrock_client.invoke_model(
                modelId=model,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            if 'claude' in model:
                return response_body['content'][0]['text']
            elif 'llama' in model:
                return response_body['generation']
            
        except ClientError as e:
            raise Exception(f"Could not generate answer from Bedrock: {e}")
    
    def search_opensearch(self, query_vector: List[float], limit: int = 10, threshold: float = 0.4) -> List[Dict]:
        """Search OpenSearch using vector similarity"""
        import requests
        from requests.auth import HTTPBasicAuth
        
        if not self.opensearch_endpoint:
            raise Exception("OpenSearch endpoint not configured")
        
        # OpenSearch k-NN search query
        search_body = {
            "size": limit,
            "query": {
                "knn": {
                    "vector_field": {
                        "vector": query_vector,
                        "k": limit
                    }
                }
            },
            "_source": True,
            "min_score": threshold
        }
        
        try:
            # Use AWS Signature V4 for authentication in production
            response = requests.post(
                f"{self.opensearch_endpoint}/articles/_search",
                json=search_body,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            results = response.json()
            return results.get('hits', {}).get('hits', [])
            
        except Exception as e:
            raise Exception(f"OpenSearch query failed: {e}")
    
    def store_article(self, article_id: str, content: str, metadata: Dict) -> str:
        """Store article content in S3"""
        if not self.s3_bucket:
            raise Exception("S3 bucket not configured")
        
        try:
            key = f"articles/{article_id}.json"
            
            article_data = {
                "content": content,
                "metadata": metadata,
                "timestamp": json.dumps(metadata.get('timestamp'), default=str)
            }
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json.dumps(article_data),
                ContentType='application/json'
            )
            
            return f"s3://{self.s3_bucket}/{key}"
            
        except ClientError as e:
            raise Exception(f"Could not store article in S3: {e}")
    
    def get_article(self, article_id: str) -> Optional[Dict]:
        """Retrieve article content from S3"""
        if not self.s3_bucket:
            raise Exception("S3 bucket not configured")
        
        try:
            key = f"articles/{article_id}.json"
            
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=key
            )
            
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise Exception(f"Could not retrieve article from S3: {e}")

class AWSResearchAssistant:
    """AWS-enabled version of the Research Assistant"""
    
    def __init__(self):
        self.aws_config = AWSConfig()
    
    def ask_question(self, query: str, limit: int = 10, threshold: float = 0.4) -> Dict:
        """Ask a research question using AWS services"""
        
        # Get embedding using Bedrock
        query_embedding = self.aws_config.get_embedding(query)
        
        # Search using OpenSearch
        search_results = self.aws_config.search_opensearch(
            query_vector=query_embedding,
            limit=limit,
            threshold=threshold
        )
        
        if not search_results:
            return {
                "query": query,
                "answer": "No relevant information found.",
                "sources": [],
                "timestamp": json.dumps(None, default=str)
            }
        
        # Prepare context for answer generation
        context_parts = []
        for result in search_results:
            source = result['_source']
            context_parts.append(f"Source: {source.get('title', 'Unknown')}\nContent: {source.get('content', '')}")
        
        context = "\n\n".join(context_parts)
        
        # Generate answer using Bedrock
        prompt = f"""Based on the following medical research sources, provide a comprehensive answer to the question: {query}

Research Sources:
{context}

Please provide a clear, well-structured answer based on the evidence provided."""
        
        answer = self.aws_config.generate_answer(prompt)
        
        return {
            "query": query,
            "answer": answer,
            "sources": search_results,
            "timestamp": json.dumps(None, default=str)
        }

def lambda_handler(event, context):
    """AWS Lambda handler for the research assistant"""
    try:
        # Parse request
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        query = body.get('query')
        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Query parameter required'})
            }
        
        # Initialize assistant
        assistant = AWSResearchAssistant()
        
        # Process query
        result = assistant.ask_question(
            query=query,
            limit=body.get('limit', 10),
            threshold=body.get('threshold', 0.4)
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

if __name__ == "__main__":
    # Test locally
    assistant = AWSResearchAssistant()
    result = assistant.ask_question("What are the latest developments in AI for clinical documentation?")
    print(json.dumps(result, indent=2))