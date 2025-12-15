# 🔍 Semantic Search Usage Guide

You now have multiple powerful ways to search your medical literature database:

## 🧠 AI Research Assistant (RECOMMENDED)
**Best for**: Comprehensive research questions with detailed answers

```bash
# Interactive Q&A
python ai_research_assistant.py

# Direct questions
python ai_research_assistant.py "What are the latest developments in AI for clinical documentation?"

# Adjust search parameters
python ai_research_assistant.py "AI bias in healthcare" --limit 15 --threshold 0.3

# Save complete response
python ai_research_assistant.py "sepsis detection AI" --save "research_response.txt"
```

**Features:**
- Natural language answers synthesized from multiple sources
- Detailed source attribution with relevance scores
- Complete transparency about which chunks informed the answer
- Save full responses with citations for later reference
- Adjustable search parameters for precision vs. recall

**Example session:**
```
🧠 AI Research Assistant
Question: What are the latest developments in AI for clinical documentation?

🎯 ANSWER
Based on the research sources, generative AI is increasingly being used for clinical documentation...
[Comprehensive answer with evidence]

📊 SOURCE BREAKDOWN
📄 SOURCE 1: A rapid quality assurance process... (78.7% relevance)
📄 SOURCE 2: Using DAX Copilot did not make clinicians... (77.4% relevance)
[Detailed breakdown of all sources used]
```

## 🎯 Quick Search (Command Line)
**Best for**: Fast, single queries

```bash
# Basic search
python quick_search.py "AI scribes clinical documentation"

# Get more results
python quick_search.py "machine learning cardiology" --limit 10

# Verbose output with previews
python quick_search.py "diagnostic accuracy" --verbose
```

## 🗣️ Interactive Search (Conversational)
**Best for**: Exploratory research, multiple queries

```bash
python semantic_search.py
```

**Features:**
- Natural language questions
- Follow-up options for detailed views
- Full text retrieval with `[number]f`
- Advanced options: `--chunks`, `--limit N`, `--threshold X`

**Example session:**
```
🤔 Your question: AI scribes for clinical documentation
📚 Found 5 relevant articles...

💡 Options: [number] for details, [number]f for full text, or Enter to continue: 1f
📚 Fetching full text for: This randomized, pragmatic trial...
[Full article text displayed]
💾 Save this article to file? (y/N): y
✅ Article saved to: article_10_1056_AIoa2501000.txt
```

## 📄 Full Text Search (Complete Articles)
**Best for**: Getting complete article content

```bash
# Get full text of most relevant article
python full_text_search.py "AI scribes clinical documentation"

# Just show summary (no full text)
python full_text_search.py "machine learning diagnosis" --summary

# Save to file
python full_text_search.py "clinical decision support" --save "article.txt"
```

## ✨ Smart Clean Article Search (RECOMMENDED)
**Best for**: Clean, readable articles from original NEJM sources

```bash
# Get clean, formatted article (much better than messy text!)
python smart_article_search.py "AI scribes clinical documentation"

# Just show summary
python smart_article_search.py "machine learning diagnosis" --summary

# Save clean article
python smart_article_search.py "clinical decision support" --save "clean_article.txt"
```

**Why use this?** 
- ✅ Clean, properly formatted text from NEJM API
- ✅ Structured sections (Abstract, Methods, Results, etc.)
- ✅ No messy XML tags or chunking artifacts
- ✅ Professional formatting perfect for reading

## 🎨 Search Tips

### Natural Language Queries
✅ **Good queries:**
- "AI scribes for clinical documentation"
- "machine learning in cardiology diagnosis"
- "artificial intelligence diagnostic accuracy"
- "clinical decision support systems"
- "ambient AI physician burnout"

❌ **Less effective:**
- Single words: "AI", "cardiology"
- Very broad: "medicine", "healthcare"

### Advanced Options
```bash
# Interactive search with options
🤔 Your question: AI in radiology --limit 10 --chunks
🤔 Your question: diagnostic AI --threshold 0.7
```

### Relevance Scores
- **80%+**: Highly relevant, exact topic match
- **60-80%**: Very relevant, related concepts
- **40-60%**: Moderately relevant, broader topic
- **Below 40%**: May be tangentially related

## 📊 What's in Your Database

**Current Content (1,920+ chunks):**
- **NEJM**: Primary medical research, clinical trials
- **NEJM AI**: AI applications in medicine (50 recent articles)
- **Catalyst**: Healthcare delivery innovation
- **Evidence**: Evidence-based medicine reviews

**Content Types:**
- Original research articles
- Clinical trials
- Review articles
- Case studies
- Editorial content
- AI methodology papers

## 🚀 Example Searches

### AI & Technology
```bash
python quick_search.py "artificial intelligence diagnostic accuracy"
python quick_search.py "machine learning clinical decision support"
python quick_search.py "ambient AI scribes physician workflow"
```

### Clinical Topics
```bash
python quick_search.py "cardiac surgery outcomes"
python quick_search.py "clinical trial methodology"
python quick_search.py "evidence-based medicine"
```

### Healthcare Innovation
```bash
python quick_search.py "healthcare delivery transformation"
python quick_search.py "physician burnout solutions"
python quick_search.py "clinical workflow optimization"
```

## 🔧 Troubleshooting

**No results found?**
- Try broader terms
- Lower threshold: `--threshold 0.3`
- Check spelling

**Low relevance scores?**
- Refine your query
- Use more specific medical terms
- Try related concepts

**Connection errors?**
- Ensure Qdrant is running: `curl http://127.0.0.1:6333/healthz`
- Ensure Ollama is running: `curl http://127.0.0.1:11434/api/tags`

Your semantic search system is now ready to help you explore the latest medical literature with natural language queries!