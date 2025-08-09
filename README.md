# Interactive Research Paper Processing Tool

A comprehensive web-based application for searching, downloading, processing, and analyzing research papers with AI assistance.

## 🚀 Features

### 📚 Multi-Source Paper Search
- **arXiv Integration**: Search the arXiv repository for academic papers
- **Google Scholar Support**: Access Google Scholar through the scholarly library
- **PubMed Integration**: Search biomedical literature from PubMed
- **Automatic Deduplication**: Remove duplicate papers across sources
- **Mock Data Fallback**: Demo functionality when APIs are unavailable

### 🔍 Advanced Search Interface
- **Topic-Based Search**: Enter research topics to find relevant papers
- **Configurable Results**: Adjust maximum results per source
- **Source Selection**: Choose which databases to search
- **Real-Time Progress**: Visual progress bars during search operations
- **Results Filtering**: Filter by source, sort by relevance, pagination support

### 📝 Manual URL Input
- **Direct URL Entry**: Input specific paper URLs manually
- **URL Validation**: Automatic validation and preview of entered URLs
- **Flexible Format**: Support for numbered lists or plain URLs
- **Batch Processing**: Process multiple URLs at once

### ⚙️ AI-Powered Paper Processing
- **Gemini AI Integration**: Use Google's Gemini for paper analysis
- **Relevance Assessment**: Automatically categorize papers as relevant/not relevant
- **Content Summarization**: Generate summaries and extract key findings
- **Configurable Criteria**: Customize research criteria for relevance assessment
- **Batch Processing**: Process multiple papers efficiently
- **Demo Mode**: Test functionality without API keys

### 📊 Comprehensive Results Analysis
- **Processing Statistics**: View total processed, relevance rates, processing dates
- **Detailed Paper Views**: Expandable cards with full paper information
- **Export Functionality**: Download results in JSON format
- **File Downloads**: Access generated analysis files
- **Progress Monitoring**: Real-time processing progress tracking

### 🎨 Professional Web Interface
- **Streamlit-Based UI**: Modern, responsive web interface
- **Multi-Page Navigation**: Organized workflow across different pages
- **Status Indicators**: Real-time status updates and progress tracking
- **Error Handling**: Comprehensive error handling with helpful messages
- **Mobile-Friendly**: Works on desktop and mobile devices

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Git

### Quick Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/Regional_Curriculum_Harmonization_Initiatives_Africa.git
   cd Regional_Curriculum_Harmonization_Initiatives_Africa
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API keys** (optional for demo mode):
   ```bash
   # Create .env file
   echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
   ```

4. **Launch the application**:
   ```bash
   streamlit run web_app.py
   ```

5. **Open your browser** to `http://localhost:8501`

## 📖 Usage Guide

### 1. Search for Papers
1. Navigate to **🔍 Search Papers**
2. Enter your research topic (e.g., "curriculum harmonization Africa")
3. Configure search parameters:
   - Max results per source (5-100)
   - Select sources to search (arXiv, Google Scholar, PubMed)
4. Click **🔍 Search Papers**
5. Review results with expandable paper details
6. Use **▶️ Process These Papers** to continue to processing

### 2. Manual URL Input
1. Navigate to **📝 Manual URLs**
2. Enter paper URLs (one per line):
   ```
   1. https://arxiv.org/abs/2301.12345
   2. https://pubmed.ncbi.nlm.nih.gov/12345678/
   3. https://doi.org/10.1000/182
   ```
3. Click **💾 Save URLs**
4. Preview and validate entered URLs

### 3. Process Papers
1. Navigate to **⚙️ Process Papers**
2. Configure processing settings:
   - Concurrent workers (1-10)
   - Batch size (1-10)
   - Research criteria (customize relevance assessment)
3. **For demo mode** (no API key required):
   - Click **🎮 Run Demo Processing**
4. **For full processing** (requires Gemini API key):
   - Ensure API key is set in `.env` file
   - Click **🚀 Start Processing**

### 4. View Results
1. Navigate to **📊 View Results**
2. Review processing statistics
3. Browse processed papers with relevance categorization
4. Download generated files:
   - Paper Information & Analysis
   - Processing Summary
   - Extracted References
   - Non-Relevant Papers
5. Export results in JSON format

### 5. Monitor Progress
1. Navigate to **📈 Progress Monitor**
2. View real-time processing progress
3. Monitor detailed progress metrics
4. Access processing logs

## 🔧 API Configuration

### Gemini API Setup
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to your `.env` file:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
4. Restart the application

### Optional API Enhancements
- **Scholarly**: May require additional setup for Google Scholar access
- **PubMed**: Uses public API, no key required
- **arXiv**: Uses public API, no key required

## 📁 File Structure

```
├── web_app.py              # Main Streamlit application
├── paper_search.py         # Multi-source paper search functionality
├── unified_paper_processor.py  # AI-powered paper processing (existing)
├── extract_research_urls.py    # URL extraction utilities (existing)
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys)
├── README.md              # This documentation
└── downloads/             # Downloaded papers and processing results
    ├── html/              # HTML versions of papers
    ├── temp/              # Temporary processing files
    └── not_relevant/      # Papers categorized as not relevant
```

## 🎯 Key Workflows

### Research Paper Discovery Workflow
1. **Topic Search** → **Results Review** → **Paper Selection** → **Processing Queue**
2. **Manual URLs** → **URL Validation** → **Processing Queue**

### AI Processing Workflow
1. **Paper Download** → **Content Extraction** → **AI Analysis** → **Relevance Assessment** → **Summarization**

### Results Analysis Workflow
1. **Statistics Overview** → **Paper Categorization** → **Detailed Review** → **Export Results**

## 🔍 Advanced Features

### Batch Processing
- Process multiple papers simultaneously
- Configurable concurrency and batch sizes
- Progress tracking and error handling

### Content Analysis
- Full-text extraction from PDFs and web pages
- AI-powered summarization
- Key findings extraction
- Reference extraction

### Relevance Assessment
- Customizable research criteria
- AI-powered relevance scoring
- Automatic categorization
- Detailed explanations for decisions

## 🚨 Troubleshooting

### Common Issues

**1. Search Returns No Results**
- Check internet connection
- Try different search terms
- Use demo mode if APIs are unavailable

**2. Processing Fails**
- Verify Gemini API key is correctly set
- Check API key permissions
- Try demo mode for testing

**3. File Download Issues**
- Ensure sufficient disk space
- Check file permissions
- Some papers may be behind paywalls

**4. UI Not Loading**
- Restart the Streamlit application
- Clear browser cache
- Check console for errors

### Error Messages
- **"Gemini API key is required"**: Set up API key in `.env` file
- **"No papers to process"**: Search for papers or enter URLs first
- **"Network connection error"**: Check internet connectivity

## 🎮 Demo Mode

When you don't have API keys or want to test the interface:

1. Use the search functionality to find papers
2. Navigate to Process Papers
3. Click **🎮 Run Demo Processing**
4. View simulated results in the Results page
5. Export demo data for review

Demo mode provides:
- Simulated processing progress
- Mock relevance assessments
- Sample summaries and findings
- Full UI workflow testing

## 🔄 Integration with Existing Tools

This tool enhances and integrates with existing components:

- **unified_paper_processor.py**: Core processing engine with AI analysis
- **extract_research_urls.py**: URL extraction and validation utilities
- **Existing research data**: Compatible with current paper collections

## 📈 Future Enhancements

Potential improvements and features:

1. **Additional Sources**: IEEE Xplore, Scopus, Web of Science
2. **Advanced AI**: Custom models, multi-language support
3. **Collaboration**: Multi-user support, shared workspaces
4. **Analytics**: Advanced research analytics and insights
5. **Export Formats**: PDF reports, citation formats
6. **API Integration**: RESTful API for external tools

## 🤝 Contributing

This tool is designed to be extensible and customizable:

1. **Add New Sources**: Extend `paper_search.py` with new academic databases
2. **Enhance AI Processing**: Modify `unified_paper_processor.py` for new analysis types
3. **UI Improvements**: Enhance `web_app.py` with new features and pages
4. **Documentation**: Keep this README updated with new features

## 📄 License

This project builds upon existing research tools and maintains compatibility with the original codebase while adding comprehensive web-based functionality.

---

**Happy Research! 📚🔬**