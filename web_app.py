"""
Interactive Research Paper Processing Web Interface
Built with Streamlit for comprehensive paper search, analysis, and processing
"""

import streamlit as st
import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path
import pandas as pd
from typing import List, Dict, Optional

# Import our modules
from paper_search import PaperSearcher, PaperMetadata
from unified_paper_processor import UnifiedPaperProcessor

# Page configuration
st.set_page_config(
    page_title="Research Paper Analyzer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .paper-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e6e9ef;
        margin-bottom: 1rem;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = 'idle'
    if 'current_query' not in st.session_state:
        st.session_state.current_query = ''
    if 'manual_urls' not in st.session_state:
        st.session_state.manual_urls = ''
    if 'processor_results' not in st.session_state:
        st.session_state.processor_results = None
    if 'processing_progress' not in st.session_state:
        st.session_state.processing_progress = {}

def main():
    """Main application"""
    init_session_state()
    
    # Main header
    st.markdown('<div class="main-header">📚 Research Paper Analyzer</div>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox(
            "Choose a page:",
            ["🔍 Search Papers", "📝 Manual URLs", "⚙️ Process Papers", "📊 View Results", "📈 Progress Monitor"]
        )
        
        st.markdown("---")
        st.header("Quick Stats")
        
        # Display quick statistics
        if st.session_state.search_results:
            st.metric("Papers Found", len(st.session_state.search_results))
        
        if st.session_state.processor_results:
            results = st.session_state.processor_results
            st.metric("Papers Processed", results.get('total_processed', 0))
            st.metric("Relevant Papers", results.get('relevant_count', 0))
        
        # Status indicator
        status_color = {
            'idle': '🔵',
            'searching': '🟡',
            'processing': '🟠',
            'completed': '🟢',
            'error': '🔴'
        }
        st.markdown(f"**Status:** {status_color.get(st.session_state.processing_status, '⚪')} {st.session_state.processing_status.title()}")
    
    # Route to appropriate page
    if page == "🔍 Search Papers":
        search_papers_page()
    elif page == "📝 Manual URLs":
        manual_urls_page()
    elif page == "⚙️ Process Papers":
        process_papers_page()
    elif page == "📊 View Results":
        view_results_page()
    elif page == "📈 Progress Monitor":
        progress_monitor_page()

def search_papers_page():
    """Search papers from academic sources"""
    st.header("🔍 Search Research Papers")
    
    # Search form
    with st.form("search_form"):
        query = st.text_input(
            "Research Topic/Query",
            value=st.session_state.current_query,
            placeholder="e.g., curriculum harmonization Africa higher education",
            help="Enter keywords or phrases related to your research topic"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            max_results = st.number_input(
                "Max Results per Source",
                min_value=5,
                max_value=100,
                value=25,
                step=5
            )
        
        with col2:
            sources = st.multiselect(
                "Sources to Search",
                ["arXiv", "Google Scholar", "PubMed"],
                default=["arXiv", "Google Scholar", "PubMed"]
            )
        
        submit_search = st.form_submit_button("🔍 Search Papers")
    
    # Handle search
    if submit_search and query:
        st.session_state.current_query = query
        st.session_state.processing_status = 'searching'
        
        with st.spinner("Searching for papers..."):
            searcher = PaperSearcher()
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            papers = []
            total_sources = len(sources)
            
            for i, source in enumerate(sources):
                status_text.text(f"Searching {source}...")
                progress_bar.progress((i) / total_sources)
                
                try:
                    if source == "arXiv":
                        source_papers = searcher.search_arxiv(query, max_results)
                    elif source == "Google Scholar":
                        source_papers = searcher.search_google_scholar(query, max_results)
                    elif source == "PubMed":
                        source_papers = searcher.search_pubmed(query, max_results)
                    
                    papers.extend(source_papers)
                    
                except Exception as e:
                    st.error(f"Error searching {source}: {str(e)}")
            
            progress_bar.progress(1.0)
            status_text.text("Removing duplicates...")
            
            # Deduplicate
            unique_papers = searcher._deduplicate_papers(papers)
            st.session_state.search_results = unique_papers
            
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"search_results_{timestamp}.json"
            searcher.save_search_results(unique_papers, query, filename)
            
            st.session_state.processing_status = 'completed'
            
        st.success(f"Found {len(st.session_state.search_results)} unique papers!")
    
    # Display search results
    if st.session_state.search_results:
        st.subheader("Search Results")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            source_filter = st.selectbox(
                "Filter by Source",
                ["All"] + list(set(paper.source for paper in st.session_state.search_results))
            )
        
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                ["Relevance", "Title", "Date", "Source"]
            )
        
        with col3:
            papers_per_page = st.selectbox("Papers per page", [10, 20, 50], index=1)
        
        # Filter papers
        filtered_papers = st.session_state.search_results
        if source_filter != "All":
            filtered_papers = [p for p in filtered_papers if p.source == source_filter]
        
        # Pagination
        total_papers = len(filtered_papers)
        total_pages = (total_papers - 1) // papers_per_page + 1
        
        if total_pages > 1:
            page_num = st.number_input(
                f"Page (1-{total_pages})",
                min_value=1,
                max_value=total_pages,
                value=1
            )
        else:
            page_num = 1
        
        start_idx = (page_num - 1) * papers_per_page
        end_idx = start_idx + papers_per_page
        page_papers = filtered_papers[start_idx:end_idx]
        
        # Display papers
        for i, paper in enumerate(page_papers, start_idx + 1):
            with st.expander(f"{i}. {paper.title[:100]}..." if len(paper.title) > 100 else f"{i}. {paper.title}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Authors:** {', '.join(paper.authors[:5])}")
                    if len(paper.authors) > 5:
                        st.write(f"*... and {len(paper.authors) - 5} more*")
                    
                    if paper.abstract:
                        st.write(f"**Abstract:** {paper.abstract[:300]}...")
                    
                    if paper.doi:
                        st.write(f"**DOI:** {paper.doi}")
                    
                    if paper.published_date:
                        st.write(f"**Published:** {paper.published_date}")
                
                with col2:
                    st.write(f"**Source:** {paper.source}")
                    if paper.url:
                        st.link_button("View Paper", paper.url)
                    if paper.pdf_url:
                        st.link_button("PDF", paper.pdf_url)
        
        # Action buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save URLs for Processing"):
                searcher = PaperSearcher()
                urls_file = searcher.save_urls_file(filtered_papers, st.session_state.current_query)
                st.success(f"URLs saved to {urls_file}")
        
        with col2:
            if st.button("▶️ Process These Papers"):
                st.session_state.manual_urls = '\n'.join(
                    searcher.convert_to_url_format(filtered_papers)
                )
                st.success("Papers loaded into processing queue!")
                st.info("Go to 'Process Papers' tab to continue.")

def manual_urls_page():
    """Manual URL input page"""
    st.header("📝 Manual URL Input")
    
    st.write("Enter URLs directly if you already have specific papers to analyze:")
    
    # URL input
    manual_urls = st.text_area(
        "Paper URLs (one per line)",
        value=st.session_state.manual_urls,
        height=300,
        placeholder="1. https://arxiv.org/abs/2301.00001\n2. https://pubmed.ncbi.nlm.nih.gov/12345678/\n3. https://doi.org/10.1000/182",
        help="Enter URLs in numbered format (1. URL, 2. URL, etc.) or plain URLs"
    )
    
    if st.button("💾 Save URLs"):
        st.session_state.manual_urls = manual_urls
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"manual_urls_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Manual URLs Input\n")
            f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(manual_urls)
        
        st.success(f"URLs saved to {filename}")
    
    # URL validation and preview
    if manual_urls:
        lines = [line.strip() for line in manual_urls.split('\n') if line.strip()]
        
        st.subheader("URL Preview")
        valid_urls = []
        invalid_urls = []
        
        for line in lines:
            # Extract URL from numbered format
            if '. ' in line and line.split('. ', 1)[1].startswith('http'):
                url = line.split('. ', 1)[1]
            elif line.startswith('http'):
                url = line
            else:
                invalid_urls.append(line)
                continue
            
            valid_urls.append(url)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Valid URLs", len(valid_urls))
            if valid_urls:
                with st.expander("View Valid URLs"):
                    for i, url in enumerate(valid_urls[:10], 1):
                        st.write(f"{i}. {url}")
                    if len(valid_urls) > 10:
                        st.write(f"... and {len(valid_urls) - 10} more")
        
        with col2:
            st.metric("Invalid URLs", len(invalid_urls))
            if invalid_urls:
                with st.expander("View Invalid URLs", expanded=True):
                    for url in invalid_urls:
                        st.error(url)
        
        if valid_urls:
            if st.button("▶️ Process These URLs"):
                st.info("Go to 'Process Papers' tab to start processing.")

def process_papers_page():
    """Process papers with AI analysis"""
    st.header("⚙️ Process Papers")
    
    # Check if we have URLs to process
    urls_to_process = []
    
    # From search results
    if st.session_state.search_results:
        searcher = PaperSearcher()
        search_urls = searcher.convert_to_url_format(st.session_state.search_results)
        urls_to_process.extend(search_urls)
    
    # From manual input
    if st.session_state.manual_urls:
        manual_lines = [line.strip() for line in st.session_state.manual_urls.split('\n') if line.strip()]
        urls_to_process.extend(manual_lines)
    
    if not urls_to_process:
        st.warning("No papers to process. Please search for papers or enter URLs manually first.")
        return
    
    st.success(f"Ready to process {len(urls_to_process)} papers")
    
    # Processing configuration
    with st.expander("⚙️ Processing Configuration", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            max_workers = st.slider("Concurrent Workers", 1, 20, 10)
            batch_size = st.slider("Batch Size", 1, 10, 5)
        
        with col2:
            research_criteria = st.text_area(
                "Research Criteria",
                value="Focus on curriculum harmonization, educational standards, regional cooperation in Africa",
                help="Specify what makes a paper relevant to your research"
            )
    
    # API Key check
    api_key_status = "✅ Configured" if os.getenv('GEMINI_API_KEY') else "❌ Missing"
    st.write(f"**Gemini API Key:** {api_key_status}")
    
    if not os.getenv('GEMINI_API_KEY'):
        st.error("Gemini API key is required for processing. Please set GEMINI_API_KEY in your .env file.")
        st.code("GEMINI_API_KEY=your_api_key_here")
        return
    
    # Processing button
    if st.button("🚀 Start Processing", type="primary"):
        st.session_state.processing_status = 'processing'
        
        # Create temporary URLs file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_urls_file = f"temp_urls_{timestamp}.txt"
        
        with open(temp_urls_file, 'w', encoding='utf-8') as f:
            for url in urls_to_process:
                f.write(f"{url}\n")
        
        # Start processing in a separate thread (simulation)
        with st.spinner("Processing papers..."):
            try:
                # Initialize processor
                processor = UnifiedPaperProcessor(
                    apa_file=temp_urls_file,
                    max_workers=max_workers,
                    batch_size=batch_size
                )
                
                # Run processing
                processor.process_papers()
                
                # Store results
                st.session_state.processor_results = {
                    'total_processed': len(processor.results),
                    'relevant_count': len([r for r in processor.results if r.matches_criteria]),
                    'timestamp': datetime.now().isoformat(),
                    'stats': processor.stats
                }
                
                st.session_state.processing_status = 'completed'
                st.success("Processing completed!")
                
                # Clean up temp file
                os.remove(temp_urls_file)
                
            except Exception as e:
                st.error(f"Processing failed: {str(e)}")
                st.session_state.processing_status = 'error'

def view_results_page():
    """View processing results"""
    st.header("📊 View Results")
    
    if not st.session_state.processor_results:
        st.info("No processing results available. Process some papers first.")
        return
    
    results = st.session_state.processor_results
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Processed", results.get('total_processed', 0))
    
    with col2:
        st.metric("Relevant Papers", results.get('relevant_count', 0))
    
    with col3:
        relevance_rate = (results.get('relevant_count', 0) / max(results.get('total_processed', 1), 1)) * 100
        st.metric("Relevance Rate", f"{relevance_rate:.1f}%")
    
    with col4:
        st.metric("Processing Date", results.get('timestamp', '').split('T')[0])
    
    # File downloads
    st.subheader("📁 Generated Files")
    
    files_to_show = [
        ('paper_information.json', 'Paper Information & Analysis'),
        ('unified_processing_summary.txt', 'Processing Summary'),
        ('paper_references.txt', 'Extracted References'),
        ('non_matching_papers.json', 'Non-Relevant Papers')
    ]
    
    for filename, description in files_to_show:
        if os.path.exists(filename):
            with open(filename, 'rb') as file:
                st.download_button(
                    label=f"📄 {description}",
                    data=file.read(),
                    file_name=filename,
                    mime='application/octet-stream'
                )
    
    # Display paper information if available
    if os.path.exists('paper_information.json'):
        st.subheader("📋 Processed Papers Summary")
        
        try:
            with open('paper_information.json', 'r', encoding='utf-8') as f:
                paper_info = json.load(f)
            
            # Create DataFrame for easier viewing
            papers_data = []
            for paper in paper_info:
                papers_data.append({
                    'Title': paper.get('Title', 'Unknown')[:50] + '...',
                    'Status': paper.get('status', 'Unknown'),
                    'Relevant': paper.get('matches_criteria', False),
                    'Source': paper.get('source', 'Unknown'),
                    'Download Type': paper.get('download_type', 'Unknown')
                })
            
            df = pd.DataFrame(papers_data)
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All"] + list(df['Status'].unique()))
            with col2:
                relevance_filter = st.selectbox("Filter by Relevance", ["All", "Relevant", "Not Relevant"])
            
            # Apply filters
            filtered_df = df.copy()
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df['Status'] == status_filter]
            if relevance_filter == "Relevant":
                filtered_df = filtered_df[filtered_df['Relevant'] == True]
            elif relevance_filter == "Not Relevant":
                filtered_df = filtered_df[filtered_df['Relevant'] == False]
            
            st.dataframe(filtered_df, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error loading paper information: {str(e)}")

def progress_monitor_page():
    """Real-time progress monitoring"""
    st.header("📈 Progress Monitor")
    
    # Check for progress file
    if os.path.exists('processing_progress.json'):
        try:
            with open('processing_progress.json', 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            st.subheader("Current Progress")
            
            # Progress metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total = progress_data.get('total_papers', 0)
                processed = progress_data.get('processed_count', 0)
                st.metric("Papers Processed", f"{processed}/{total}")
            
            with col2:
                if total > 0:
                    progress_pct = (processed / total) * 100
                    st.metric("Progress", f"{progress_pct:.1f}%")
                else:
                    st.metric("Progress", "0%")
            
            with col3:
                status = progress_data.get('status', 'Unknown')
                st.metric("Status", status)
            
            # Progress bar
            if total > 0:
                st.progress(processed / total)
            
            # Detailed progress
            with st.expander("Detailed Progress"):
                st.json(progress_data)
            
            # Auto-refresh
            if st.session_state.processing_status == 'processing':
                time.sleep(2)
                st.rerun()
        
        except Exception as e:
            st.error(f"Error loading progress data: {str(e)}")
    else:
        st.info("No active processing to monitor.")
    
    # Processing logs
    if os.path.exists('unified_processing_summary.txt'):
        st.subheader("Processing Logs")
        
        with open('unified_processing_summary.txt', 'r', encoding='utf-8') as f:
            logs = f.read()
        
        st.text_area("Logs", logs, height=300)

if __name__ == "__main__":
    main()