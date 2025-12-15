# 📚 NEJM API Content Sources Guide

## Available Content Sources

The NEJM API provides access to multiple medical journals and publications through different **contexts**. Each context represents a specific journal or publication with its own focus area.

### 🏥 Primary Contexts

#### 1. **NEJM** (`nejm`)
- **Full Name**: New England Journal of Medicine
- **Focus**: Primary medical research, clinical trials, original research articles
- **Content Types**: Research articles, case studies, editorials, correspondence
- **Update Frequency**: Weekly
- **Sample DOI**: `10.1056/NEJMc2514311`
- **Usage**: `--context nejm`

#### 2. **Catalyst** (`catalyst`) 
- **Full Name**: NEJM Catalyst
- **Focus**: Healthcare delivery innovation, health system transformation
- **Content Types**: Innovation articles, case studies, best practices
- **Update Frequency**: Regular
- **Sample DOI**: `10.1056/CAT.25.0310`
- **Usage**: `--context catalyst`

#### 3. **Evidence** (`evidence`)
- **Full Name**: NEJM Evidence
- **Focus**: Evidence-based medicine, systematic reviews, clinical evidence
- **Content Types**: Evidence reviews, clinical trial analyses, methodology papers
- **Update Frequency**: Regular
- **Sample DOI**: `10.1056/EVIDoa2500045`
- **Usage**: `--context evidence`

#### 4. **Clinician** (`clinician`)
- **Full Name**: NEJM Journal Watch
- **Focus**: Clinical practice updates, journal summaries for practicing physicians
- **Content Types**: Practice updates, journal summaries, clinical alerts
- **Update Frequency**: Regular
- **Sample DOI**: `10.1056/CLINeNA59587`
- **Usage**: `--context clinician`

#### 5. **NEJM AI** (`nejm-ai`)
- **Full Name**: NEJM AI
- **Focus**: Artificial intelligence applications in medicine
- **Content Types**: AI research, machine learning studies, digital health
- **Update Frequency**: Regular
- **Sample DOI**: `10.1056/AIp2501185`
- **Usage**: `--context nejm-ai`

#### 6. **Federated** (`federated`)
- **Full Name**: Cross-Journal Search
- **Focus**: Search across multiple journals simultaneously
- **Content Types**: All article types from all journals
- **Usage**: `--context federated`

## 📊 Content Statistics (as of December 2025)

| Context | Articles Available | Latest Update | Primary Focus |
|---------|-------------------|---------------|---------------|
| NEJM | 1000+ | 2025-12-11 | Clinical Research |
| Catalyst | 500+ | 2025-12-09 | Healthcare Innovation |
| Evidence | 300+ | 2025-11-25 | Evidence-Based Medicine |
| Clinician | 800+ | 2025-12-30 | Clinical Practice |
| NEJM AI | 200+ | 2025-12-12 | Medical AI |

## 🎯 Content Types by Context

### Article Types Available:
- **Research Articles**: Original studies, clinical trials
- **Review Articles**: Systematic reviews, meta-analyses  
- **Case Studies**: Clinical cases, patient reports
- **Editorials**: Opinion pieces, commentary
- **Correspondence**: Letters to editor, responses
- **Practice Guidelines**: Clinical recommendations
- **Innovation Reports**: Healthcare delivery improvements

### Media Types Available:
- **Figures**: Charts, graphs, medical images
- **Tables**: Data summaries, statistical tables
- **Videos**: Procedure demonstrations, interviews
- **Audio**: Podcasts, audio summaries
- **Visual Abstracts**: Graphical article summaries

## 🔧 Usage Examples

### Single Context Ingestion
```bash
# Ingest latest NEJM research articles
python nejm_api_client.py --context nejm --limit 10

# Ingest healthcare innovation articles
python nejm_api_client.py --context catalyst --limit 5

# Ingest evidence-based medicine reviews
python nejm_api_client.py --context evidence --limit 5

# Ingest clinical practice updates
python nejm_api_client.py --context clinician --limit 5

# Ingest AI in medicine articles
python nejm_api_client.py --context nejm-ai --limit 5
```

### Multi-Context Automation
```bash
# Automated ingestion from multiple sources
python automated_ingestion.py
```

The automation script is configured to ingest from:
- NEJM (5 articles)
- Catalyst (5 articles) 
- Evidence (5 articles)

### Federated Search
```bash
# Search across all journals
python nejm_api_client.py --context federated --limit 20
```

## 📈 Content Freshness

- **NEJM**: New issues weekly (Thursday)
- **Catalyst**: Updated regularly with innovation reports
- **Evidence**: Updated with new evidence reviews
- **Clinician**: Updated with practice alerts and summaries
- **NEJM AI**: Updated with latest AI research

## 🎨 Customizing Your Ingestion

### Focus Areas by Context:

**For Clinical Research**: Use `nejm`
- Latest clinical trials
- Original research
- Medical breakthroughs

**For Healthcare Innovation**: Use `catalyst`  
- Health system improvements
- Delivery innovations
- Operational excellence

**For Evidence-Based Practice**: Use `evidence`
- Systematic reviews
- Clinical evidence
- Practice guidelines

**For Daily Practice**: Use `clinician`
- Practice updates
- Clinical alerts
- Journal summaries

**For AI/Digital Health**: Use `nejm-ai`
- Machine learning applications
- Digital health tools
- AI research

**For Comprehensive Coverage**: Use `federated`
- Cross-journal search
- Broad topic coverage
- Maximum content diversity

## 🔍 Search and Discovery

Each context provides rich metadata for semantic search:
- **Title**: Full article title
- **Abstract**: Article summary
- **Authors**: Author information
- **DOI**: Digital object identifier
- **Publication Date**: When published
- **Article Type**: Research, review, case study, etc.
- **Keywords**: Subject tags
- **Citation Info**: Volume, issue, pages

## 💡 Best Practices

1. **Start Specific**: Use targeted contexts for focused research
2. **Scale Gradually**: Begin with small limits, increase as needed
3. **Monitor Quality**: Check ingestion success rates
4. **Regular Updates**: Schedule automated ingestion
5. **Cross-Reference**: Use federated search for comprehensive coverage

## 🚀 Getting Started

1. **Test Individual Contexts**:
   ```bash
   python nejm_api_client.py --context nejm --dry-run --limit 3
   ```

2. **Run Full Ingestion**:
   ```bash
   python automated_ingestion.py
   ```

3. **Monitor Results**:
   ```bash
   tail -f nejm_ingestion.log
   ```

Your semantic search database now has access to the most comprehensive medical literature available through NEJM's API ecosystem!