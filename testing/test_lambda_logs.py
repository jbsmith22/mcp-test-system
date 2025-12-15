#!/usr/bin/env python3
"""
Check Lambda function logs to debug the timeout issue
"""

import boto3
import json
from datetime import datetime, timedelta

def get_lambda_logs():
    """Get recent Lambda function logs"""
    
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    # Lambda function creates log group automatically
    log_group_name = '/aws/lambda/nejm-research-assistant'
    
    try:
        # Get log streams from the last hour
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        print(f"🔍 Checking Lambda logs from {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')}")
        
        # Get log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        print(f"📋 Found {len(streams_response['logStreams'])} recent log streams")
        
        # Get events from the most recent stream
        if streams_response['logStreams']:
            latest_stream = streams_response['logStreams'][0]
            stream_name = latest_stream['logStreamName']
            
            print(f"📖 Reading from stream: {stream_name}")
            
            events_response = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=stream_name,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000)
            )
            
            events = events_response['events']
            print(f"📝 Found {len(events)} log events")
            
            # Show recent events
            for event in events[-10:]:  # Last 10 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"   {timestamp.strftime('%H:%M:%S')} | {message}")
            
            return True
        else:
            print("❌ No recent log streams found")
            return False
            
    except Exception as e:
        print(f"❌ Error reading logs: {e}")
        return False

def invoke_lambda_with_timeout():
    """Invoke Lambda with a shorter timeout to see what happens"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    test_payload = {
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/json",
            "x-api-key": "YOUR_API_KEY_HERE"
        },
        "body": json.dumps({
            "query": "test query",
            "limit": 1
        })
    }
    
    try:
        print(f"\n🧪 Invoking Lambda function...")
        
        response = lambda_client.invoke(
            FunctionName='nejm-research-assistant',
            Payload=json.dumps(test_payload),
            InvocationType='RequestResponse'  # Synchronous
        )
        
        print(f"📊 Lambda response:")
        print(f"   Status Code: {response['StatusCode']}")
        
        if 'FunctionError' in response:
            print(f"   Error Type: {response['FunctionError']}")
        
        # Read the payload
        payload = response['Payload'].read()
        
        if payload:
            try:
                result = json.loads(payload)
                print(f"   Response: {json.dumps(result, indent=2)[:500]}...")
            except:
                print(f"   Raw Response: {payload[:500]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda invocation failed: {e}")
        return False

def main():
    print("🔍 Lambda Function Debugging")
    print("=" * 40)
    
    # Step 1: Check logs
    get_lambda_logs()
    
    # Step 2: Direct invocation
    invoke_lambda_with_timeout()

if __name__ == "__main__":
    main()