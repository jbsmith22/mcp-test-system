# On-Premises Deployment Files

This folder contains all files for running the NEJM Research Assistant locally on your own infrastructure.

## Key Files

### Core Applications
- `ai_research_assistant.py` - Command-line research assistant
- `web_interface.py` - Local web dashboard (Flask)
- `semantic_search.py` - Core search functionality
- `nejm_search_cli.py` - Command-line search interface

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

## Prerequisites

- Docker (for Qdrant and Ollama)
- Python 3.8+
- 8GB+ RAM recommended
- NEJM API credentials