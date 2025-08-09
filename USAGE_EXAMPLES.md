# Usage Examples - Interactive Research Tool

## Example 1: Research Topic Search

```bash
$ python3 interactive_app.py

🚀 Interactive Research Paper Discovery and Analysis Tool
============================================================

📋 Choose an option:
1. 🔍 Provide research topic (AI will find papers automatically)
2. 📎 Provide URLs directly (skip search)
3. ℹ️  View current processing status
4. 🚪 Exit
----------------------------------------

Enter your choice (1-4): 1

🔍 RESEARCH TOPIC SEARCH MODE
========================================

Enter your research topic. Be specific about what you're looking for.
Examples:
  - 'Regional curriculum harmonization in higher education'
  - 'Cross-border recognition of qualifications in Africa'
  - 'SADC education framework implementation'

Research topic: Regional curriculum harmonization in higher education

📝 Research topic: 'Regional curriculum harmonization in higher education'

How many papers to find? (default: 20, max: 100): 15

🔍 Generating search queries for: 'Regional curriculum harmonization in higher education'
✓ Generated 6 search queries

🌐 Searching for academic papers (target: 15 papers)
[Query 1/5] Searching: 'regional curriculum harmonization higher education Africa'...
  ✓ Found 3 new papers (total: 3)
[Query 2/5] Searching: 'cross-border education recognition qualifications Africa'...
  ✓ Found 4 new papers (total: 7)
[Query 3/5] Searching: 'EAC ECOWAS SADC education framework harmonization'...
  ✓ Found 5 new papers (total: 12)
[Query 4/5] Searching: 'mutual recognition degrees Africa regional'...
  ✓ Found 3 new papers (total: 15)
  📝 Reached target of 15 papers

✓ Found 15 unique papers to process

💾 URLs saved to: urls_auto_search_Regional_curriculum_harmon_20250809_144512.txt

⚙️ PROCESSING 15 PAPERS
========================================

🔄 Starting paper processing...
This may take several minutes depending on the number of papers.

============================================================
Processing batch 1 with 3 papers
============================================================

[Batch 1, Paper 1/3] APA #1
  → Finding full text...
  ✓ Direct PDF detected
  📥 Downloading PDF immediately to avoid expiration...
  ✓ PDF saved temporarily: downloads/temp/paper_001.pdf
  🔍 Attempting analysis with URL: https://example.edu/paper1.pdf
  ✓ Analysis successful with URL
  📁 PDF moved to: downloads/paper_001.pdf
  → Completed in 12.3s

[Batch 1, Paper 2/3] APA #2
  → Finding full text...
  ✓ Content fetched via standard_get_retry_1
  ✓ Analysis successful with URL
  📁 PDF moved to: downloads/not_relevant/paper_002.pdf
  → Completed in 8.7s

... (processing continues)

📊 GENERATING RESEARCH SUMMARY
========================================

📈 Generating comprehensive research summary from 8 relevant papers...
✅ Research state summary saved to: research_state_summary_20250809_144532.txt

📊 SUMMARY PREVIEW:
----------------------------------------
COMPREHENSIVE RESEARCH STATE SUMMARY

The analysis of 8 relevant papers reveals significant progress in regional 
curriculum harmonization across Africa, with the East African Community (EAC) 
leading implementation efforts. Key findings include:

CURRENT STATE OF RESEARCH:
Regional curriculum harmonization in Africa has evolved from policy frameworks 
to practical implementation, with three major regional economic communities 
(EAC, ECOWAS, SADC) developing comprehensive strategies...

REGIONAL INITIATIVES:
• EAC Inter-University Council coordinating harmonization (Mukama et al., 2023)
• SADC University Association quality assurance framework (Ngoma & Chibamba, 2022)
• ECOWAS education ministers' harmonization protocol (Diallo & Sow, 2023)
----------------------------------------

✅ Processing completed successfully!

📁 Output files:
  - paper_information.json
  - non_matching_papers.json
  - paper_references.txt
  - research_state_summary_20250809_144532.txt
  - unified_processing_summary.txt

📄 Full summary available in: research_state_summary_20250809_144532.txt
```

## Example 2: Direct URL Input

```bash
$ python3 interactive_app.py

📋 Choose an option:
1. 🔍 Provide research topic (AI will find papers automatically)
2. 📎 Provide URLs directly (skip search)
3. ℹ️  View current processing status
4. 🚪 Exit
----------------------------------------

Enter your choice (1-4): 2

📎 DIRECT URL INPUT MODE
========================================

Enter URLs of research papers to process.
You can:
  - Enter URLs one by one (press Enter twice when done)
  - Paste multiple URLs separated by newlines
  - Provide a file path containing URLs

Enter URLs (press Enter twice when finished):
https://www.example.edu/papers/regional-education-africa.pdf
  ✓ Added: https://www.example.edu/papers/regional-education-africa.pdf

https://repository.university.ac.za/handle/123456/eac-curriculum
  ✓ Added: https://repository.university.ac.za/handle/123456/eac-curriculum

https://doi.org/10.1016/j.edudev.2023.04.001
  ✓ Added: https://doi.org/10.1016/j.edudev.2023.04.001

[Press Enter again to finish]

You've entered 3 URLs. Process them now? (y/n): y

📝 Ready to process 3 URLs

💾 URLs saved to: urls_direct_input_20250809_144612.txt

⚙️ PROCESSING 3 PAPERS
========================================
[Processing continues as above...]
```

## Example 3: Status Check

```bash
$ python3 interactive_app.py

📋 Choose an option:
1. 🔍 Provide research topic (AI will find papers automatically)
2. 📎 Provide URLs directly (skip search)
3. ℹ️  View current processing status
4. 🚪 Exit
----------------------------------------

Enter your choice (1-4): 3

📊 CURRENT STATUS
========================================

📁 Found 5 result files:
  ✓ paper_information.json (234.5 KB, modified: 2025-08-09 14:45)
  ✓ non_matching_papers.json (67.2 KB, modified: 2025-08-09 14:45)
  ✓ paper_references.txt (12.8 KB, modified: 2025-08-09 14:45)
  ✓ unified_processing_summary.txt (23.4 KB, modified: 2025-08-09 14:45)
  ✓ processing_progress.json (8.9 KB, modified: 2025-08-09 14:45)

📈 Processing Statistics:
  Total papers processed: 18
  Papers matching criteria: 8
  Papers not matching: 10
  Downloads successful: 15
```

## Output Files Generated

### Core Results
- **`paper_information.json`**: Complete extraction data for relevant papers
- **`non_matching_papers.json`**: Basic info for non-relevant papers
- **`paper_references.txt`**: APA references for all matching papers

### Research Summaries
- **`research_state_summary_YYYYMMDD_HHMMSS.txt`**: Comprehensive AI-generated overview
- **`unified_processing_summary.txt`**: Detailed statistics and processing info

### Downloaded Papers
- **`downloads/`**: PDFs of papers matching criteria
- **`downloads/not_relevant/`**: PDFs of papers not matching criteria

## Demo Mode (No API Key Required)

```bash
$ python3 demo.py

🎭 DEMO MODE - Interactive Research Paper Discovery Tool
============================================================
This demo shows how the tool works without requiring an API key.
For full functionality, set up your Gemini API key in .env

[Demo shows complete workflow with sample data...]
```

## Quick Start Options

### Option 1: Automated Setup
```bash
./run.sh
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set API key in .env
echo "GEMINI_API_KEY=your_key_here" > .env

# Run interactive tool
python3 interactive_app.py

# Or run demo mode
python3 demo.py
```

## Research Focus Areas

The tool is specifically designed for papers about:
- ✅ Regional curriculum harmonization (multi-country initiatives)
- ✅ Cross-border education recognition
- ✅ Regional frameworks (EAC, ECOWAS, SADC)
- ✅ Mutual qualification recognition
- ❌ Single-institution curriculum changes
- ❌ Purely national education reforms