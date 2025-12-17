# 🚀 NEJM Research Assistant MCP Server Setup

This guide will help you set up the NEJM Research Assistant as an MCP (Model Context Protocol) server, making it accessible from Kiro and other MCP clients with full vector visibility.

## 🎯 What You Get

The MCP server exposes these tools:

1. **search_articles** - Semantic search with full vector visibility
   - Query embeddings (768-dimensional vectors)
   - Article embeddings and similarity scores
   - Relevance weights and rankings
   
2. **get_database_stats** - Database statistics and health info

3. **get_article_by_doi** - Retrieve specific articles with all chunks and vectors

4. **compare_embeddings** - Compare vector embeddings between two texts

## 📋 Prerequisites

- **Qdrant** running on `http://127.0.0.1:6333`
- **Ollama** running on `http://127.0.0.1:11434` with `nomic-embed-text` model
- **Python 3.8+**
- **Articles ingested** into Qdrant collection `articles_ollama`

## 🔧 Installation

### Step 1: Install MCP Dependencies

```bash
cd on-prem
pip install -r requirements-mcp.txt
```

### Step 2: Test the MCP Server

```bash
# Make sure Qdrant and Ollama are running
docker ps  # Should show qdrant and ollama containers

# Test the MCP server directly
python mcp_server.py
```

The server should start and wait for input. Press `Ctrl+C` to stop.

### Step 3: Configure Kiro to Use the MCP Server

#### Option A: Workspace Configuration (Recommended)

Create or edit `.kiro/settings/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "nejm-research": {
      "command": "python",
      "args": [
        "/absolute/path/to/nejm-research-assistant/on-prem/mcp_server.py"
      ],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "OLLAMA_URL": "http://127.0.0.1:11434"
      },
      "disabled": false,
      "autoApprove": [
        "search_articles",
        "get_database_stats"
      ]
    }
  }
}
```

**Important:** Replace `/absolute/path/to/nejm-research-assistant` with your actual path!

#### Option B: User-Level Configuration (Global)

Edit `~/.kiro/settings/mcp.json` with the same configuration.

### Step 4: Restart Kiro or Reconnect MCP Server

- **In Kiro**: Open the MCP Server view in the Kiro feature panel
- Click "Reconnect" next to the `nejm-research` server
- Or restart Kiro completely

### Step 5: Verify It's Working

In Kiro, you should now see the NEJM Research tools available. Try:

```
Search for articles about "AI in clinical documentation" using the NEJM research assistant
```

## 🎨 Usage Examples

### Basic Search with Vector Visibility

```
Use the nejm-research server to search for "diabetes treatment machine learning" 
and show me the embedding vectors
```

### Compare Embeddings

```
Compare the embeddings between "artificial intelligence" and "machine learning" 
using the NEJM research assistant
```

### Get Database Statistics

```
Show me the NEJM database statistics
```

### Retrieve Specific Article

```
Get the article with DOI "10.1056/NEJMoa2345678" with all its vectors
```

## 🔍 Vector Visibility Features

### Query Embeddings
Every search shows:
- **Model used**: nomic-embed-text
- **Vector dimension**: 768
- **Vector norm**: Magnitude of the embedding
- **Vector preview**: First 10 dimensions
- **Full vector**: Available with `show_vectors: true`

### Article Embeddings
For each result:
- **Relevance score**: Percentage match (0-100%)
- **Vector dimension**: 768
- **Vector norm**: Embedding magnitude
- **Vector preview**: First 10 dimensions
- **Similarity calculation**: Cosine similarity between query and article

### Embedding Comparison
Compare any two texts:
- Side-by-side vector information
- Cosine similarity score
- Interpretation (very similar, related, different)

## 🛠 Troubleshooting

### MCP Server Not Showing in Kiro

1. Check the path in `mcp.json` is absolute and correct
2. Verify Python can run the script: `python on-prem/mcp_server.py`
3. Check Kiro logs for MCP connection errors
4. Try reconnecting from the MCP Server view

### "Connection Refused" Errors

1. Ensure Qdrant is running: `curl http://127.0.0.1:6333/healthz`
2. Ensure Ollama is running: `curl http://127.0.0.1:11434/api/tags`
3. Check Docker containers: `docker ps`

### No Results from Search

1. Verify articles are ingested: `python list_all_articles.py`
2. Check collection exists in Qdrant
3. Try lowering the threshold parameter

### Slow Response Times

1. Embedding generation takes ~1-2 seconds
2. Search typically takes ~1-3 seconds
3. First query may be slower (model loading)

## 📊 Performance

- **Embedding Generation**: ~1-2 seconds per query
- **Vector Search**: ~1-3 seconds for 10 results
- **Memory Usage**: ~500MB (Ollama model loaded)
- **Concurrent Requests**: Supported (async implementation)

## 🔒 Security Notes

- MCP server runs locally only (no network exposure)
- Communicates with local Qdrant and Ollama instances
- No external API calls except to local services
- All data stays on your machine

## 🎯 Advanced Configuration

### Custom Qdrant/Ollama URLs

Edit the `env` section in `mcp.json`:

```json
"env": {
  "QDRANT_URL": "http://custom-host:6333",
  "OLLAMA_URL": "http://custom-host:11434"
}
```

### Auto-Approve Tools

Add tool names to `autoApprove` to skip confirmation prompts:

```json
"autoApprove": [
  "search_articles",
  "get_database_stats",
  "get_article_by_doi",
  "compare_embeddings"
]
```

### Disable the Server

Set `"disabled": true` in `mcp.json` to temporarily disable without removing the configuration.

## 📚 Next Steps

1. **Ingest More Articles**: Use `automated_ingestion.py` to add more NEJM articles
2. **Explore Vectors**: Use `compare_embeddings` to understand semantic relationships
3. **Build Workflows**: Create Kiro hooks that automatically search NEJM when you ask medical questions
4. **Monitor Performance**: Check vector norms and similarity scores to tune search quality

## 🤝 Integration with Existing Tools

The MCP server works alongside your existing Python scripts:
- `ai_research_assistant.py` - Still works independently
- `web_interface.py` - Still provides local web UI
- `semantic_search.py` - Still available for CLI use

The MCP server is an additional interface, not a replacement!

---

**Questions?** Check the main README.md or the docs/ folder for more information.
