# On-Premises Deployment Files

This folder contains all files for running the NEJM Research Assistant locally on your own infrastructure.

## Key Files

### Core Applications
- `ai_research_assistant.py` - Command-line research assistant
- `web_interface.py` - Local web dashboard (Flask)
- `semantic_search.py` - Core search functionality
- `nejm_search_cli.py` - Command-line search interface
- **`mcp_server.py`** - 🆕 MCP server with full vector visibility

### Setup & Configuration
- `setup_wizard.py` - Initial setup and configuration
- `config_manager.py` - Configuration management
- `automated_ingestion.py` - Article ingestion system
- `nejm_api_client.py` - NEJM API integration

### Utilities
- `list_all_articles.py` - Database article listing
- `clean_article_retriever.py` - Clean article content retrieval
- `content_sources_explorer.py` - Explore available content sources

### Web Templates
- `templates/` - HTML templates for web interface

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Start Qdrant: `docker run -d -p 6333:6333 qdrant/qdrant`
3. Start Ollama: `docker run -d -p 11434:11434 ollama/ollama`
4. Pull models: `ollama pull nomic-embed-text && ollama pull llama3.2`
5. Run setup: `python setup_wizard.py`
6. Start web interface: `python web_interface.py`
7. Access at: http://localhost:8080

## 🚀 MCP Server (NEW!)

The NEJM Research Assistant is now available as an MCP server! This exposes the semantic search system to Kiro and other MCP clients with **full vector visibility**.

### Quick MCP Setup

```bash
# Install MCP dependencies
pip install -r requirements-mcp.txt

# Configure in Kiro (edit .kiro/settings/mcp.json)
# See MCP_SERVER_SETUP.md for detailed instructions

# Use from Kiro
"Search NEJM for articles about AI in healthcare and show me the embedding vectors"
```

**Features:**
- 🔍 Semantic search with vector embeddings visible
- 📊 Similarity scores and relevance weights
- 🔬 Compare embeddings between texts
- 📈 Database statistics and health monitoring

**See `MCP_SERVER_SETUP.md` for complete setup instructions!**

## Prerequisites

- Docker (for Qdrant and Ollama)
- Python 3.8+
- 8GB+ RAM recommended
- NEJM API credentials
- For MCP: `pip install -r requirements-mcp.txt`