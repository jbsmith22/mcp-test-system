# NEJM API Integration

Automated pipeline to fetch articles from NEJM's OneSearch API and ingest them into your Qdrant semantic search database.

## 🏗️ Architecture

```
NEJM API → Python Client → Article Content → Qdrant Database
                ↓
        Ollama Embeddings (nomic-embed-text)
```

## 📁 Files Created

- `nejm_api_client.py` - Main API client for fetching and ingesting articles
- `automated_ingestion.py` - Scheduled automation script  
- `test_nejm_api.py` - Test connectivity and show examples
- `setup_nejm_integration.py` - Verify dependencies and services
- `nejm_openapi_spec.json` - API specification reference

## 🚀 Quick Start

1. **Verify Setup**
   ```bash
   python setup_nejm_integration.py
   ```

2. **Get API Key** (Contact NEJM for access)

3. **Test Connection (QA Environment)**
   ```bash
   python nejm_api_client.py --api-key YOUR_KEY --dry-run --limit 3
   ```

4. **Start Ingesting**
   ```bash
   python nejm_api_client.py --api-key YOUR_KEY --limit 10
   ```

## 📖 Usage Examples

### Manual Ingestion
```bash
# Ingest 10 recent NEJM articles (QA environment - default)
python nejm_api_client.py --api-key YOUR_KEY --limit 10

# Use production environment
python nejm_api_client.py --api-key YOUR_KEY --environment production --limit 10

# Ingest from different journals
python nejm_api_client.py --api-key YOUR_KEY --context catalyst --limit 5
python nejm_api_client.py --api-key YOUR_KEY --context evidence --limit 5
```

### Automated Ingestion
```bash
# Set API key as environment variable
export NEJM_API_KEY='your-api-key-here'

# Run automated ingestion (QA environment - default)
python automated_ingestion.py

# Use production environment
export NEJM_ENVIRONMENT='production'
python automated_ingestion.py

# Schedule daily ingestion (crontab)
0 6 * * * cd /path/to/project && python automated_ingestion.py
```

## 🎯 Available Contexts

- `nejm` - New England Journal of Medicine
- `catalyst` - NEJM Catalyst  
- `evidence` - NEJM Evidence
- `clinician` - NEJM Journal Watch
- `nejm-ai` - NEJM AI

## 🔧 How It Works

1. **Fetch Articles**: Uses NEJM's `/v1/simple` endpoint to get recent articles
2. **Get Full Content**: Retrieves complete article text via `/v1/content` endpoint  
3. **Process Text**: Extracts readable content from JSON/XML response
4. **Create Embeddings**: Uses your existing Ollama setup (nomic-embed-text)
5. **Store in Qdrant**: Leverages your existing ingestion script

## 📊 Monitoring

The automated script creates:
- `nejm_ingestion.log` - Detailed logs
- `ingestion_stats.json` - Success rates and history

## 🔍 Troubleshooting

**API Key Issues**
```bash
# Test API connectivity
python test_nejm_api.py
```

**Service Issues** 
```bash
# Check Qdrant
curl http://127.0.0.1:6333/healthz

# Check Ollama  
curl http://127.0.0.1:11434/api/tags
```

**Ingestion Issues**
```bash
# Check your existing ingestion script
python /Users/jsmith/Ingest.py --help
```

## 🔗 Integration Points

This integrates seamlessly with your existing setup:
- Uses your Qdrant collection: `articles_ollama`
- Uses your Ollama embeddings: `nomic-embed-text` 
- Uses your ingestion script: `/Users/jsmith/Ingest.py`
- Maintains your metadata schema and indexing

The articles will appear in your existing semantic search with source `nejm-api-{context}`.