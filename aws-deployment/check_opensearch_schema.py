#!/usr/bin/env python3
"""Check OpenSearch index schema"""

import boto3
import requests
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# Configuration
OPENSEARCH_ENDPOINT = "https://search-nejm-research-krqqohfnmi6ekrkzyoshht4goy.us-east-1.es.amazonaws.com"
INDEX_NAME = "nejm-articles"

# Get credentials
session = boto3.Session()
credentials = session.get_credentials()

# Get index mapping
url = f"{OPENSEARCH_ENDPOINT}/{INDEX_NAME}/_mapping"
request = AWSRequest(method='GET', url=url)
SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)

response = requests.get(url, headers=dict(request.headers))
print("Index Mapping:")
print(json.dumps(response.json(), indent=2))

# Get a sample document
url = f"{OPENSEARCH_ENDPOINT}/{INDEX_NAME}/_search"
search_body = {"size": 1}
request = AWSRequest(method='POST', url=url, data=json.dumps(search_body))
request.headers['Content-Type'] = 'application/json'
SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)

response = requests.post(url, headers=dict(request.headers), data=json.dumps(search_body))
print("\nSample Document:")
print(json.dumps(response.json(), indent=2))
