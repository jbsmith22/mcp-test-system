# Testing Files

This folder contains test scripts, sample data, and validation tools for both AWS and on-premises deployments.

## Test Scripts

### AWS Testing
- `test_stats_api.py` - Test AWS API statistics endpoint
- `test_ingestion_api.py` - Test AWS article ingestion
- `test_nejm_api_access.py` - Validate NEJM API connectivity
- `test_opensearch_direct.py` - Direct OpenSearch testing

### General Testing
- `simple_nejm_test.py` - Basic NEJM API functionality test
- `quick_test.py` - Quick system validation
- `demo_searches.py` - Demonstration search queries

### Sample Data
- `nejm_article_sample.json` - Sample article data
- `nejm_content_sample.txt` - Sample article content
- `nejm_sample_qa.json` - Sample Q&A data
- `security_report_*.json` - Security validation reports

### Utilities
- `compare_environments.py` - Compare local vs AWS environments
- `security_demo.py` - Security feature demonstration

## Usage

Run tests from the project root directory:

```bash
# Test AWS deployment
cd testing
python test_stats_api.py

# Test on-premises setup
python simple_nejm_test.py

# Run comprehensive tests
python quick_test.py
```

## Prerequisites

- Configured environment (AWS or on-premises)
- Valid NEJM API credentials
- Network connectivity to required services