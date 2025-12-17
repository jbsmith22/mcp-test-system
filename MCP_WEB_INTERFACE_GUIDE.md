# NEJM Research Assistant - MCP Web Interface Guide

## 🌐 Live Website
**URL:** http://nejm-mcp-research-web.s3-website-us-east-1.amazonaws.com

## 🎯 What You Can Do

Your NEJM Research Assistant is now a fully functional MCP-powered web application that you can access from anywhere. Here's what it offers:

### 1. **Medical Literature Search**
- Enter any medical research question in natural language
- Get semantic search results with relevance scores
- View vector embedding information for transparency
- See 412 NEJM articles with full abstracts

### 2. **AI-Powered Research Q&A**
- Switch to "AI Research Q&A" mode
- Get comprehensive answers from Claude 3.5 Sonnet
- Answers are based on your indexed articles
- See which sources support each point

### 3. **Real-Time Database Stats**
- Live article count and database metrics
- Source breakdown (NEJM, NEJM AI, Evidence, Catalyst)
- System health monitoring
- Vector dimension information (1536-dim Titan embeddings)

### 4. **MCP Tool Testing**
- Test individual MCP tools directly from the interface
- View raw JSON responses
- Debug and explore the MCP server capabilities

### 5. **🔍 Debug & Learning Mode** ⭐ NEW!
- **Step-by-step query visualization** - See exactly what happens during each MCP call
- **Vector embedding deep dive** - Understand how text becomes 1536-dimensional vectors
- **Timing and performance metrics** - Monitor response times and processing steps
- **Raw data inspection** - View actual JSON requests and responses
- **Ingestion process simulation** - Learn how articles are processed and stored
- **Interactive embedding comparison** - Compare similarity between any two texts

## 🔧 MCP Tools Available

Your web interface uses these MCP tools via HTTP API:

### `search_articles`
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_articles",
    "arguments": {
      "query": "diabetes treatment",
      "max_results": 10
    }
  }
}
```

### `ask_research_question`
```json
{
  "method": "tools/call",
  "params": {
    "name": "ask_research_question",
    "arguments": {
      "question": "What are the latest treatments for diabetes?",
      "max_sources": 5
    }
  }
}
```

### `get_database_stats`
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_database_stats",
    "arguments": {}
  }
}
```

### `get_article_by_doi`
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_article_by_doi",
    "arguments": {
      "doi": "10.1056/NEJMc2515117"
    }
  }
}
```

### `compare_embeddings`
```json
{
  "method": "tools/call",
  "params": {
    "name": "compare_embeddings",
    "arguments": {
      "text1": "diabetes treatment",
      "text2": "glucose management"
    }
  }
}
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │───▶│   S3 Website    │───▶│  API Gateway    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenSearch    │◀───│ Lambda Function │◀───│   MCP Server    │
│   (412 articles)│    │  (MCP Handler)  │    │   (HTTP API)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Bedrock Claude  │
                       │ + Titan Embed   │
                       └─────────────────┘
```

## 🧪 Testing Examples

### Example 1: Search for Diabetes Articles
1. Visit the website
2. Enter: "What are the latest diabetes treatments?"
3. Select "Article Search" mode
4. Click "Search Literature"
5. View results with vector information

### Example 2: AI Research Question
1. Switch to "AI Research Q&A" mode
2. Enter: "How effective is AI in diabetes management?"
3. Get AI-generated answer with source citations
4. See which articles support the conclusions

### Example 3: Test MCP Tools
1. Click "Test Search" in the sidebar
2. View raw MCP tool response
3. See vector embeddings and relevance scores
4. Test other tools like "Get Stats" and "Compare Vectors"

### Example 4: 🔍 Debug Mode Learning ⭐ NEW!
1. Click "Debug Mode" in the sidebar
2. Enter a research question: "diabetes treatment mechanisms"
3. Click "Debug Query" to see the step-by-step process:
   - **Step 1:** MCP request formatting
   - **Step 2:** AWS Lambda communication
   - **Step 3:** Response parsing
   - **Step 4:** Tool result processing (with vector details)
   - **Step 5:** Result formatting for display
4. Switch to "Vector Embeddings" tab
5. Compare two texts to see similarity calculation
6. View the "Article Ingestion" tab to understand how articles are processed

### Example 5: Learning Vector Embeddings
1. Go to Debug Mode → Vector Embeddings tab
2. Enter two related terms: "diabetes" and "glucose"
3. Click "Compare Embeddings"
4. See the 1536-dimensional vectors, similarity score, and vector norms
5. Try different combinations to understand semantic similarity

## 📊 Current Database Status

- **Total Articles:** 412 NEJM articles
- **Sources:** NEJM, NEJM AI, Evidence, Catalyst
- **Vector Model:** Amazon Titan (1536 dimensions)
- **AI Model:** Claude 3.5 Sonnet
- **Search:** Hybrid text + semantic search
- **Cost:** ~$52/month

## 🔒 Security

- **Access:** Currently open for testing
- **IP Allowlist:** 3 authorized IPs (can be expanded)
- **CORS:** Enabled for web access
- **Authentication:** None (public research tool)

## 🚀 What Makes This Special

1. **True MCP Server:** Your system is now a proper MCP server accessible via HTTP
2. **Vector Visibility:** See the actual embeddings and similarity scores
3. **Web Accessible:** No local setup required - works from any browser
4. **Real-time:** Live database stats and health monitoring
5. **AI Integration:** Claude 3.5 Sonnet provides research answers
6. **Scalable:** AWS infrastructure handles multiple users
7. **🔍 Educational Debug Mode:** Learn exactly how MCP servers work with step-by-step visualization
8. **Vector Learning:** Understand embeddings, similarity, and semantic search in real-time
9. **Process Transparency:** See every step from query to result with timing and metrics

## 🎯 Next Steps

You now have a complete MCP-powered research assistant that:
- ✅ Runs entirely on AWS (no local dependencies)
- ✅ Provides web access from anywhere
- ✅ Exposes MCP tools via HTTP API
- ✅ Shows vector embeddings and AI reasoning
- ✅ Handles 412 medical articles with semantic search
- ✅ Integrates Claude 3.5 for research Q&A

The system is ready for production use and can be expanded with additional MCP tools or connected to other MCP clients like Kiro!