# NEJM Research Assistant

A comprehensive AI-powered medical literature search and analysis system that integrates with the New England Journal of Medicine (NEJM) API to provide intelligent research capabilities. Available in both cloud (AWS) and on-premises deployments.

## 🎯 Current Status (December 2025)

### AWS Cloud Deployment ✅ FULLY OPERATIONAL
- **🌐 Live Website**: http://nejm-mcp-research-web.s3-website-us-east-1.amazonaws.com
- **🔗 MCP API**: https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research
- **📊 Database**: 436+ NEJM articles with full-content vectorization and AI embeddings
- **🔍 AI Search**: Claude 3.5 Sonnet integration for intelligent literature analysis
- **📥 Real NEJM API Integration**: Live ingestion with smart offset strategy and duplicate prevention
- **🎛️ User Controls**: Journal selection and article count controls in web interface
- **💰 Cost Monitoring**: Optimized AWS costs with efficient resource usage

### On-Premises Deployment ✅ AVAILABLE
- **🏠 Local Setup**: Complete Docker-based stack with Qdrant + Ollama
- **🔒 Privacy**: All data and processing stays on your infrastructure
- **💰 Cost**: Free after initial setup (uses local compute resources)
- **🛠 Customizable**: Full control over models, data, and configurations

## 🚀 Key Features

### AI-Powered Research
- **Intelligent Search**: Uses Claude 3.5 Sonnet for comprehensive medical literature analysis
- **Semantic Understanding**: Vector embeddings enable conceptual search beyond keywords
- **Source Integration**: Direct citations with DOI links and author information
- **Real-time Analysis**: Instant AI-generated summaries with evidence-based responses

### Advanced Ingestion System
- **Real NEJM API Integration**: Direct connection to NEJM's production API with full authentication
- **Smart Offset Strategy**: Calculates database offset to find new articles efficiently
- **Guaranteed Article Count**: Searches until requested number of unique articles found
- **Multi-Source Support**: NEJM Main, NEJM AI, Catalyst, Evidence, Clinician journals
- **Full Content Processing**: Complete article text (up to 8,000 chars) with JATS XML parsing
- **Duplicate Prevention**: DOI-based filtering prevents re-ingestion of existing articles
- **User-Controlled Parameters**: Web interface dropdowns for journal selection and article count

### Comprehensive Web Interface
- **📊 Live Statistics**: Real-time database metrics with source breakdowns
- **🔧 System Health**: API, OpenSearch, and AI model status monitoring  
- **🔒 Security Dashboard**: IP access control and authorization status
- **💰 Cost Tracking**: AWS service costs and monthly estimates
- **📥 Article Management**: Interactive ingestion with progress tracking
- **📚 Quick Actions**: One-click stats refresh and API testing

### Enterprise AWS Architecture
- **OpenSearch Domain**: Scalable search with vector embeddings (436+ articles indexed)
- **Lambda Functions**: MCP-compatible serverless API with real NEJM integration
- **API Gateway**: RESTful endpoints with CORS and IP-based security
- **S3 Static Hosting**: Fast website delivery with user-friendly controls
- **Bedrock Integration**: Amazon Titan embeddings (1536 dims) and Claude 3.5 Sonnet
- **Secrets Manager**: Secure NEJM API credential storage and rotation
- **MCP Protocol**: Model Context Protocol compatibility for AI assistant integration

### On-Premises Architecture
- **Qdrant Vector Database**: Local vector storage with semantic search capabilities
- **Ollama AI Models**: Local embedding (nomic-embed-text) and chat (llama3.2) models
- **Flask Web Interface**: Local web dashboard with real-time monitoring
- **Docker Services**: Containerized deployment for easy management
- **Local File Storage**: All data remains on your infrastructure
- **Direct API Integration**: Secure NEJM API access without cloud dependencies

## 📈 Data Sources & Coverage

### Current Database (297 Articles)
- **NEJM Journal**: 100 articles (core medical research)
- **NEJM AI**: 150 articles (AI in healthcare)
- **NEJM Catalyst**: 18 articles (healthcare innovation)
- **NEJM Evidence**: 9 articles (clinical trials)
- **Other Sources**: 20 articles (various NEJM publications)

### Ingestion Capabilities
- **Historical Range**: 1812 - Present (213+ years of medical literature)
- **Batch Sizes**: 10, 25, 50, or 100 articles per ingestion
- **Smart Discovery**: Automatically finds new articles across multiple pages
- **Quality Control**: Full-text extraction with abstract and metadata validation

## 🛠 Technical Implementation

### AWS Cloud Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │────│   API Gateway    │────│ Lambda Function │
│  (S3+CloudFront)│    │ (lwi6jeeczi)     │    │ (nejm-research) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ NEJM OneSearch  │    │   OpenSearch     │    │ Amazon Bedrock  │
│      API        │    │   (297 docs)     │    │ (Claude + Titan)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### On-Premises Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Flask Web UI    │────│ AI Research      │────│ Semantic Search │
│ (localhost:8080)│    │ Assistant        │    │ Engine          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ NEJM OneSearch  │    │ Qdrant Vector    │    │ Ollama Models   │
│      API        │    │ Database         │    │ (Local AI)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Security & Access Control
- **IP Restrictions**: Configurable allowlist for authorized access
- **API Authentication**: NEJM credentials via AWS Secrets Manager  
- **Resource Policies**: API Gateway and Lambda execution controls
- **CORS Configuration**: Proper cross-origin request handling

### Monitoring & Observability
- **CloudWatch Logs**: Comprehensive logging for all components
- **Real-time Metrics**: API response times and error rates
- **Cost Tracking**: Service-level cost breakdown and projections
- **Health Checks**: Automated system status validation

## 🚀 Complete Setup Instructions

Choose your deployment option and follow the detailed step-by-step instructions:

---

## 🌩️ Option 1: AWS Cloud Deployment

### Prerequisites
- **AWS Account** with AdministratorAccess permissions
- **AWS CLI** installed and configured
- **Python 3.8+** with pip
- **NEJM API credentials** (userid and API key)

### Step 1: AWS CLI Setup
```bash
# Install AWS CLI (if not already installed)
# macOS
brew install awscli

# Windows
# Download from: https://aws.amazon.com/cli/

# Configure AWS CLI
aws configure
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region name: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

### Step 2: Clone and Setup Repository
```bash
# Clone repository
git clone <repository-url>
cd nejm-research-assistant

# Install Python dependencies
pip install -r requirements-aws.txt

# Verify Python version (3.8+ required)
python --version
```

### Step 3: Configure NEJM API Credentials
```bash
# Option A: Environment Variable (Recommended)
export NEJM_API_KEY='your-userid|your-api-key'

# Option B: Secure Config File
cd on-prem
python config_manager.py --set-key 'your-userid|your-api-key' --environment qa

# Test credentials
python ../testing/simple_nejm_test.py
```

### Step 4: Deploy AWS Infrastructure
```bash
# Navigate to AWS deployment folder
cd aws-deployment

# Deploy complete infrastructure (takes 10-15 minutes)
python deploy_aws_website.py

# Deploy Lambda dependencies
python deploy_lambda_layer.py

# Update Lambda function with latest code
python fix_lambda_quickly.py
```

### Step 5: Configure Security (Optional but Recommended)
```bash
# Set up IP-based access control
python implement_ip_security.py

# Enable CORS for web access
python enable_cors.py

# Test security configuration
python ../testing/test_security_lockdown.py
```

### Step 6: Migrate Initial Data
```bash
# Migrate articles from local database (if you have one)
python migrate_all_articles.py

# OR populate with fresh NEJM articles
python populate_aws_test.py --count 50
```

### Step 7: Test Deployment
```bash
# Test API functionality
cd ../testing
python test_stats_api.py

# Test ingestion
python test_ingestion_api.py

# Test NEJM API access
python test_nejm_api_access.py
```

### Step 8: Access Your Deployment
- **Web Interface**: http://nejm-research-web-interface.s3-website-us-east-1.amazonaws.com
- **HTTPS Version**: https://d2u3y79uc809ee.cloudfront.net
- **API Endpoint**: https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research

---

## 🏠 Option 2: On-Premises Deployment

### Prerequisites
- **Docker** and Docker Compose installed
- **Python 3.8+** with pip
- **8GB+ RAM** recommended for AI models
- **NEJM API credentials** (userid and API key)

### Step 1: Install Docker
```bash
# macOS
brew install docker docker-compose

# Windows
# Download Docker Desktop from: https://www.docker.com/products/docker-desktop

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install docker.io docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Step 2: Clone and Setup Repository
```bash
# Clone repository
git clone <repository-url>
cd nejm-research-assistant

# Install Python dependencies
pip install -r requirements-web.txt

# Verify Python version
python --version
```

### Step 3: Start Core Services
```bash
# Start Qdrant vector database
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# Start Ollama AI service
docker run -d --name ollama -p 11434:11434 ollama/ollama

# Verify services are running
curl http://127.0.0.1:6333/healthz
curl http://127.0.0.1:11434/api/tags

# Check Docker containers
docker ps
```

### Step 4: Install AI Models
```bash
# Pull embedding model (required for semantic search)
docker exec ollama ollama pull nomic-embed-text

# Pull chat model (required for AI assistant)
docker exec ollama ollama pull llama3.2

# Verify models are installed
docker exec ollama ollama list
```

### Step 5: Configure NEJM API Access
```bash
# Navigate to on-prem folder
cd on-prem

# Option A: Interactive setup wizard
python setup_wizard.py

# Option B: Manual configuration
python config_manager.py --set-key 'your-userid|your-api-key' --environment qa

# Test NEJM API connection
python nejm_api_client.py --dry-run --limit 3
```

### Step 6: Initialize Database and Ingest Articles
```bash
# Create vector database collection
python semantic_search.py --init

# Ingest initial articles from NEJM
python automated_ingestion.py --source nejm-ai --count 25

# Verify articles were ingested
python list_all_articles.py
```

### Step 7: Start Web Interface
```bash
# Start Flask web server
python web_interface.py

# The server will start on http://localhost:8080
# You should see: "Running on http://127.0.0.1:8080"
```

### Step 8: Test Your Setup
```bash
# In a new terminal, test the AI research assistant
cd on-prem
python ai_research_assistant.py "What are the latest AI developments in healthcare?"

# Test semantic search
python semantic_search.py

# Test CLI search
python nejm_search_cli.py --query "machine learning" --limit 5
```

### Step 9: Access Your Local System
- **Web Interface**: http://localhost:8080
- **Database Stats**: Available in web interface
- **Direct API**: Qdrant at http://localhost:6333
- **AI Models**: Ollama at http://localhost:11434

---

## 🔧 Advanced Configuration

### NEJM API Environments
```bash
# QA Environment (default, recommended for testing)
python config_manager.py --set-key 'your-key' --environment qa

# Production Environment (requires production API key)
python config_manager.py --set-key 'your-prod-key' --environment production

# List configured environments
python config_manager.py --list
```

### Database Management
```bash
# On-Premises: Qdrant Management
cd on-prem

# View all articles
python list_all_articles.py

# Search articles
python semantic_search.py

# Clean article retrieval
python clean_article_retriever.py --doi "10.1056/NEJMoa2345678"

# AWS: OpenSearch Management
cd aws-deployment

# View database statistics
python debug_api_gateway.py

# Direct OpenSearch operations
python direct_opensearch_insert.py --test
```

### Monitoring and Maintenance
```bash
# On-Premises Monitoring
# Check service health
curl http://127.0.0.1:6333/healthz  # Qdrant
curl http://127.0.0.1:11434/api/tags  # Ollama

# View Docker logs
docker logs qdrant
docker logs ollama

# AWS Monitoring
# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/nejm"

# Check API Gateway metrics
cd aws-deployment
python debug_api_gateway.py
```

---

## 🚨 Troubleshooting

### Common Issues

#### Docker Services Not Starting
```bash
# Check Docker is running
docker info

# Restart services
docker restart qdrant ollama

# Check port conflicts
lsof -i :6333  # Qdrant port
lsof -i :11434  # Ollama port
```

#### NEJM API Connection Issues
```bash
# Test credentials manually
curl -H "apiuser: your-userid" -H "apikey: your-key" \
  "https://onesearch-api.nejmgroup-qa.org/api/v1/simple?context=nejm&objectType=nejm-article&pageLength=1"

# Check configuration
cd on-prem
python config_manager.py --list
```

#### AWS Deployment Issues
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify permissions
aws iam get-user

# Check service status
cd aws-deployment
python debug_api_gateway.py
```

#### Model Loading Issues
```bash
# Re-pull models
docker exec ollama ollama pull nomic-embed-text
docker exec ollama ollama pull llama3.2

# Check available models
docker exec ollama ollama list

# Check Ollama logs
docker logs ollama
```

### Getting Help
- Check the `docs/` folder for detailed documentation
- Review `testing/` folder for diagnostic scripts
- Check Docker container logs for service issues
- Verify API credentials and network connectivity

### Usage Examples

#### AWS Web Interface
1. Visit: http://nejm-research-web-interface.s3-website-us-east-1.amazonaws.com
2. Enter medical research question
3. Review AI analysis and source articles
4. Use ingestion tile to add new articles
5. Monitor system health and costs

#### On-Premises Web Interface
1. Start services: `docker run -d -p 6333:6333 qdrant/qdrant && docker run -d -p 11434:11434 ollama/ollama`
2. Launch web interface: `cd on-prem && python web_interface.py`
3. Visit: http://localhost:8080
4. Enter research questions and review AI-generated answers
5. Monitor local database statistics and health

#### Command Line Usage (On-Premises)
```bash
# Ask a research question
cd on-prem
python ai_research_assistant.py "What are the latest treatments for diabetes?"

# Search for specific articles
python nejm_search_cli.py --query "machine learning" --limit 5

# List all articles in database
python list_all_articles.py

# Ingest new articles
python automated_ingestion.py --source nejm --count 50
```

#### AWS API Integration
```python
import requests

# Search for articles
response = requests.post(
    'https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research',
    json={
        'query': 'diabetes treatment machine learning',
        'max_results': 10
    }
)

# Get database statistics  
stats = requests.post(
    'https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research',
    json={'type': 'statistics'}
)

# Ingest new articles
ingestion = requests.post(
    'https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research',
    json={
        'type': 'ingestion',
        'source': 'nejm',
        'count': 25
    }
)
```

## 📊 Performance & Costs

### Current Metrics
- **Search Response Time**: ~2-5 seconds for AI analysis
- **Ingestion Speed**: ~10-15 articles per minute
- **Database Size**: 297 articles (~30MB indexed content)
- **Monthly AWS Costs**: ~$52 (OpenSearch $45, Bedrock $3, Other $4)

### Scalability Targets
- **Target Database Size**: 50,000 articles (historical NEJM archive)
- **Projected Monthly Cost**: ~$75-100 at full scale
- **Search Performance**: Sub-3 second response times maintained
- **Concurrent Users**: Designed for 10+ simultaneous researchers

## 📁 Project Structure

```
nejm-research-assistant/
├── aws-deployment/          # AWS cloud deployment files
│   ├── deploy_aws_website.py
│   ├── fix_lambda_quickly.py
│   ├── aws_web_interface_full.html
│   └── ...
├── on-prem/                 # On-premises deployment files
│   ├── ai_research_assistant.py
│   ├── web_interface.py
│   ├── semantic_search.py
│   ├── templates/
│   └── ...
├── testing/                 # Test scripts and sample data
│   ├── test_*.py
│   ├── simple_*.py
│   └── ...
├── archived/                # Legacy/unused files
└── docs/                    # Documentation files
```

## 🔧 Development & Maintenance

### AWS Scripts
- `aws-deployment/fix_lambda_quickly.py` - Update Lambda function with latest features
- `aws-deployment/add_missing_tiles.py` - Deploy updated web interface
- `testing/test_ingestion_api.py` - Validate ingestion functionality
- `aws-deployment/debug_api_gateway.py` - Troubleshoot API connectivity

### On-Premises Scripts
- `on-prem/ai_research_assistant.py` - Command-line research assistant
- `on-prem/web_interface.py` - Local web dashboard
- `on-prem/semantic_search.py` - Core search functionality
- `on-prem/setup_wizard.py` - Initial setup and configuration

### Monitoring Commands

#### AWS Cloud Monitoring
```bash
# Check system health
cd aws-deployment
python debug_api_gateway.py

# View Lambda logs
aws logs get-log-events --log-group-name "/aws/lambda/nejm-research-assistant"

# Test API endpoints
curl -X POST https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research \
  -H "Content-Type: application/json" \
  -d '{"type": "statistics"}'

# Check OpenSearch cluster health
aws opensearch describe-domain --domain-name nejm-research

# Monitor costs
aws ce get-cost-and-usage --time-period Start=2025-12-01,End=2025-12-31 \
  --granularity MONTHLY --metrics BlendedCost
```

#### On-Premises Monitoring
```bash
# Check service health
curl http://127.0.0.1:6333/healthz  # Qdrant
curl http://127.0.0.1:11434/api/tags  # Ollama

# View Docker container status
docker ps
docker stats

# Check database statistics
cd on-prem
python list_all_articles.py --stats

# Monitor system resources
htop  # or top on systems without htop
df -h  # disk usage
free -h  # memory usage
```

### Maintenance Tasks

#### Regular Maintenance (Weekly)
```bash
# Update article database
cd on-prem
python automated_ingestion.py --source nejm --count 25

# AWS: Trigger ingestion via web interface or API
curl -X POST https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research \
  -H "Content-Type: application/json" \
  -d '{"type": "ingestion", "source": "nejm", "count": 25}'

# Check for duplicate articles
python list_all_articles.py --duplicates

# Backup configuration (on-premises)
cp ~/.nejm_api/config.json ~/.nejm_api/config.json.backup
```

#### System Updates
```bash
# Update Docker images (on-premises)
docker pull qdrant/qdrant:latest
docker pull ollama/ollama:latest

# Update AI models
docker exec ollama ollama pull nomic-embed-text
docker exec ollama ollama pull llama3.2

# Update Python dependencies
pip install -r requirements-web.txt --upgrade  # On-premises
pip install -r requirements-aws.txt --upgrade  # AWS

# Update AWS Lambda functions
cd aws-deployment
python fix_lambda_quickly.py
```

## 🔧 Development & Maintenance

## 📝 Documentation

### Setup Guides
- `docs/AWS_DEPLOYMENT_SUCCESS.md` - Complete AWS infrastructure setup guide
- `docs/SECURITY_IMPLEMENTATION_SUCCESS.md` - Security configuration details
- `docs/NEJM_API_ACCESS_SUCCESS.md` - API integration documentation
- `API_KEY_SETUP.md` - NEJM API credential configuration

### Project Status
- `docs/PROJECT_STATUS_COMPREHENSIVE.md` - Detailed project status tracking
- `docs/SESSION_SUMMARY_DEC15_2024.md` - Latest development session summary
- `docs/FINAL_DEPLOYMENT_SUMMARY.md` - Complete deployment overview

### Usage Guides
- `docs/SEARCH_USAGE_GUIDE.md` - Search functionality documentation
- `docs/NEJM_CONTENT_SOURCES.md` - Available content sources and coverage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Last Updated**: December 15, 2025  
**System Status**: ✅ Fully Operational  
**Database Count**: 297 articles and growing