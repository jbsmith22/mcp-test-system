# 🌐 AWS MCP-Compatible API Guide

Your NEJM Research Assistant is now a **fully web-accessible MCP server** running on AWS!

## 🎯 What You Have

A complete RAG system accessible via HTTPS from anywhere:
- **412 articles** indexed in OpenSearch
- **Full vector visibility** with embeddings and similarity scores
- **AI-powered Q&A** with Claude 3.5 Sonnet
- **No local infrastructure needed** - everything runs on AWS

## 🔗 API Endpoint

```
https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research
```

## 🛠️ Available Tools

### 1. Search Articles
Search with full vector visibility:

```bash
curl -X POST https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_articles",
    "query": "AI in clinical documentation",
    "limit": 5,
    "threshold": 0.5
  }'
```

**Returns:**
- Query embedding (1536-dim Titan vector)
- Article results with relevance scores
- Vector norms and previews
- Full transparency into search process

### 2. Ask Research Question
AI-powered Q&A with source attribution:

```bash
curl -X POST https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "ask_research_question",
    "question": "What are the latest developments in AI for clinical documentation?",
    "limit": 10
  }'
```

**Returns:**
- AI-generated answer from Claude 3.5 Sonnet
- Source articles with relevance scores
- Query embedding information

### 3. Get Database Stats
Check database health and article counts:

```bash
curl -X POST https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_database_stats"}'
```

**Returns:**
```json
{
  "total_articles": 412,
  "sources": {},
  "index_name": "nejm-articles",
  "status": "healthy"
}
```

### 4. Get Article by DOI
Retrieve specific article:

```bash
curl -X POST https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_article_by_doi",
    "doi": "10.1056/AIoa2400659"
  }'
```

### 5. Compare Embeddings
Compare vector similarity between texts:

```bash
curl -X POST https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "compare_embeddings",
    "text1": "artificial intelligence",
    "text2": "machine learning"
  }'
```

## 📊 Vector Visibility

Every response includes full vector information:

```json
{
  "query": {
    "text": "AI clinical documentation",
    "embedding": {
      "model": "amazon.titan-embed-text-v1",
      "dimension": 1536,
      "vector_norm": 23.33,
      "vector_preview": [0.478, 0.347, 0.582, ...]
    }
  },
  "results": [
    {
      "title": "Article Title",
      "relevance_score": 2827.97,
      "doi": "10.1056/...",
      "abstract": "..."
    }
  ]
}
```

## 🔒 Security

- **IP Allowlist**: Currently configured for your IPs
- **CORS Enabled**: Accessible from web browsers
- **AWS IAM**: Lambda has proper permissions for OpenSearch and Bedrock

**Current Authorized IPs:**
- 108.20.28.24
- 216.120.168.254
- 163.252.34.182

## 🚀 Use from Anywhere

### Python
```python
import requests

response = requests.post(
    'https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research',
    json={
        'tool': 'search_articles',
        'query': 'diabetes treatment',
        'limit': 5
    }
)

print(response.json())
```

### JavaScript
```javascript
fetch('https://lwi6jeeczi.execute-api.us-east-1.amazonaws.com/prod/research', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    tool: 'search_articles',
    query: 'diabetes treatment',
    limit: 5
  })
})
.then(r => r.json())
.then(data => console.log(data));
```

### From Kiro
You can now connect Kiro to this API endpoint to use all the tools!

## 💰 Current Costs

- **OpenSearch**: ~$45/month
- **Lambda**: ~$2/month
- **Bedrock**: ~$3/month (pay per use)
- **Total**: ~$50/month

## 📈 Performance

- **Search Response**: 1-3 seconds
- **AI Q&A**: 3-8 seconds (includes Claude generation)
- **Database Stats**: <1 second
- **Concurrent Requests**: Supported

## 🎯 What's Next

1. **Connect from Kiro**: Use this API as your MCP backend
2. **Build Applications**: Any app can now use this RAG system
3. **Scale Up**: Add more articles (currently 412, can handle 50K+)
4. **Add Features**: Ingestion, article management, etc.

---

**Your NEJM Research Assistant is now a complete, web-accessible MCP server running on AWS!** 🎉
