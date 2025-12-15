# AWS Deployment Files

This folder contains all files related to the AWS cloud deployment of the NEJM Research Assistant.

## Key Files

### Deployment Scripts
- `deploy_aws_website.py` - Main deployment script for web interface
- `deploy_lambda_layer.py` - Deploy Lambda dependencies
- `fix_lambda_quickly.py` - Update Lambda function code

### Web Interface
- `aws_web_interface_full.html` - Complete web interface
- `add_missing_tiles.py` - Add new features to web interface

### Infrastructure Management
- `debug_api_gateway.py` - Troubleshoot API Gateway issues
- `enable_cors.py` - Configure CORS settings
- `implement_ip_security.py` - Set up IP-based access control

### Migration & Data
- `migrate_all_articles.py` - Migrate articles from local to AWS
- `direct_opensearch_insert.py` - Direct OpenSearch operations

## Usage

1. Ensure AWS CLI is configured with appropriate permissions
2. Run deployment scripts from this directory
3. Monitor logs and test functionality with debug scripts

## Prerequisites

- AWS CLI configured
- Python 3.8+
- Required permissions for OpenSearch, Lambda, API Gateway, S3