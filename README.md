# Interactive Research Paper Discovery and Analysis Tool

An AI-powered tool for discovering, downloading, and analyzing academic research papers on regional curriculum harmonization in Africa.

## Features

### 🔍 **Interactive Research Discovery**
- **Topic Search**: Provide a research topic and let AI automatically find relevant papers
- **Direct URL Input**: Provide specific URLs of papers you want to analyze
- **Intelligent Search**: AI generates multiple search queries and finds papers from academic databases

### 🤖 **AI-Powered Analysis**
- **Relevance Detection**: Automatically determines if papers match regional curriculum harmonization criteria
- **Full-Text Processing**: Downloads and analyzes complete papers (PDFs and HTML)
- **Content Extraction**: Extracts key findings, recommendations, and research details

### 📊 **Comprehensive Reporting**
- **Research State Summary**: AI-generated overview of the current research landscape
- **Grounded References**: All claims backed by exact citations from analyzed papers
- **Categorized Results**: Papers separated into relevant/not relevant with explanations
- **Detailed Statistics**: Processing metrics and success rates

## Quick Start

### Prerequisites
- Python 3.7 or higher
- Gemini API key (get one at [ai.google.dev](https://ai.google.dev/))

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/vuyelwadr/Regional_Curriculum_Harmonization_Initiatives_Africa.git
   cd Regional_Curriculum_Harmonization_Initiatives_Africa
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API key**:
   - Create a `.env` file in the project root
   - Add your Gemini API key:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```

### Usage

#### Option 1: Quick Start (Recommended)
```bash
./run.sh
```

#### Option 2: Manual Start
```bash
python3 interactive_app.py
```

## How to Use

### 1. Research Topic Search Mode 🔍

When you select this mode:

1. **Enter your research topic**:
   - Example: "Regional curriculum harmonization in higher education"
   - Example: "Cross-border recognition of qualifications in Africa"
   - Example: "SADC education framework implementation"

2. **Specify number of papers** (1-100, default: 20)

3. **AI automatically**:
   - Generates multiple search queries
   - Searches academic databases and repositories
   - Finds relevant papers
   - Downloads and analyzes each paper
   - Categorizes papers as relevant/not relevant
   - Generates comprehensive research summary

### 2. Direct URL Mode 📎

When you select this mode:

1. **Enter URLs** of specific papers you want to analyze
2. **Submit** when finished (press Enter twice)
3. **AI processes** each paper using the same analysis pipeline

### 3. View Status 📊

Check current processing results and statistics from previous runs.

## Output Files

The tool generates several output files:

### Core Results
- **`paper_information.json`**: Complete extraction data for papers matching criteria
- **`non_matching_papers.json`**: Basic info for papers not matching criteria  
- **`paper_references.txt`**: APA references for all matching papers

### Research Summaries
- **`research_state_summary_YYYYMMDD_HHMMSS.txt`**: AI-generated comprehensive research overview
- **`unified_processing_summary.txt`**: Detailed processing statistics and results

### Downloaded Papers
- **`downloads/`**: PDFs of papers matching criteria
- **`downloads/not_relevant/`**: PDFs of papers not matching criteria

### Technical Details
- **`processing_progress.json`**: Progress tracking (for resuming interrupted processing)
- **`model/`**: All AI model responses for transparency and debugging

## Research Criteria

The tool focuses on papers about **regional curriculum harmonization** that involve:

- ✅ Multiple African countries or regions
- ✅ Regional frameworks (EAC, ECOWAS, SADC, etc.)
- ✅ Cross-border education initiatives
- ✅ Mutual recognition of qualifications
- ✅ Regional qualification frameworks
- ✅ Multi-institutional harmonization efforts

❌ **Not included**: Single-institution curriculum changes or purely national initiatives

## Advanced Features

### Batch Processing
- Processes multiple papers concurrently for efficiency
- Rate-limited API calls to respect service limits
- Robust error handling and retry logic

### Full-Text Discovery
- Automatically finds full-text versions of papers
- Tries multiple strategies: direct PDFs, repositories, DOI resolution
- Falls back gracefully when full text unavailable

### Research State Analysis
- AI synthesizes findings across all relevant papers
- Identifies themes, patterns, and research gaps
- Provides grounded conclusions with exact citations
- Highlights implementation approaches and challenges

## Example Workflow

1. **Start the tool**: `./run.sh`
2. **Choose option 1**: Research topic search
3. **Enter topic**: "Regional education harmonization in East Africa"
4. **Specify papers**: 15 papers
5. **Wait for processing**: AI finds and analyzes papers automatically
6. **Review results**: Check generated summary and downloaded papers

The tool will:
- Generate 5-7 search queries about East African education harmonization
- Find ~15 relevant academic papers
- Download PDFs where possible
- Analyze each paper for relevance to regional harmonization
- Generate a comprehensive research state summary
- Provide exact references for all findings

## Troubleshooting

### Common Issues

1. **API Key Error**: Make sure your Gemini API key is correctly set in `.env`
2. **No Papers Found**: Try broader or different search terms
3. **Processing Errors**: Check internet connection; some papers may be behind paywalls
4. **Memory Issues**: Reduce batch size for very large papers

### Getting Help

- Check the processing logs for specific error messages
- Review the `unified_processing_summary.txt` for detailed statistics
- Ensure all dependencies are installed: `pip install -r requirements.txt`

## Original Functionality

This tool extends the original paper processing system. You can still use the original scripts:

- **`unified_paper_processor.py`**: Direct processing of URL files
- **`extract_research_urls.py`**: URL extraction from text files

## Requirements

See `requirements.txt` for all Python dependencies:
- requests>=2.31.0
- python-dotenv>=1.0.0
- beautifulsoup4>=4.12.0
- PyPDF2>=3.0.0

## License

This tool is designed for academic research purposes. Please respect publisher terms when downloading papers.

---

**Made for researchers studying regional curriculum harmonization in Africa** 🌍📚