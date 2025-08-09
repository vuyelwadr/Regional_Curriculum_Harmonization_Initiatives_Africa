#!/usr/bin/env python3
"""
Interactive Research Paper Discovery and Analysis Tool

This tool allows users to:
1. Provide a research topic and have AI find relevant papers automatically
2. Provide direct URLs for immediate processing
3. Analyze papers, determine relevance, and generate comprehensive research summaries

Usage:
    python3 interactive_app.py
"""

import os
import sys
import json
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Import the existing processing pipeline
from unified_paper_processor import UnifiedPaperProcessor

# Load environment variables
load_dotenv()


class ResearchTopicSearcher:
    """Handles automatic research paper discovery based on user topics"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
        
        # Academic search endpoints and patterns
        self.search_sources = [
            {
                'name': 'Google Scholar',
                'search_url': 'https://scholar.google.com/scholar?q={query}',
                'type': 'academic_search'
            },
            {
                'name': 'arXiv',
                'search_url': 'https://arxiv.org/search/?query={query}&searchtype=all',
                'type': 'repository'
            },
            {
                'name': 'Semantic Scholar', 
                'search_url': 'https://www.semanticscholar.org/search?q={query}',
                'type': 'academic_search'
            },
            {
                'name': 'ResearchGate',
                'search_url': 'https://www.researchgate.net/search/publication?q={query}',
                'type': 'academic_network'
            },
            {
                'name': 'CORE',
                'search_url': 'https://core.ac.uk/search?q={query}',
                'type': 'repository'
            }
        ]
    
    def generate_search_queries(self, research_topic: str) -> List[str]:
        """Generate multiple search queries for the research topic using AI"""
        print(f"🔍 Generating search queries for: '{research_topic}'")
        
        prompt = f"""Generate 5-7 diverse academic search queries for finding research papers about: "{research_topic}"

Focus specifically on:
- Regional curriculum harmonization in Africa
- Cross-border education initiatives  
- Regional education frameworks (EAC, ECOWAS, SADC)
- Mutual recognition of qualifications
- Regional qualification frameworks

Generate queries that would find papers in academic databases. Include both broad and specific terms.
Vary the terminology (e.g., "harmonization" vs "harmonisation", "curriculum" vs "curricula").

Return a JSON array of search query strings:
["query1", "query2", "query3", ...]"""

        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                'contents': [{
                    'parts': [{'text': prompt}]
                }],
                'generationConfig': {
                    'temperature': 0.3,
                    'maxOutputTokens': 2048,
                    'responseMimeType': 'application/json'
                }
            }
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    response_text = result['candidates'][0]['content']['parts'][0]['text']
                    queries = json.loads(response_text.strip())
                    print(f"✓ Generated {len(queries)} search queries")
                    return queries
            
            print(f"⚠ API request failed: {response.status_code}")
            
        except Exception as e:
            print(f"⚠ Error generating search queries: {e}")
        
        # Fallback: Generate basic queries manually
        fallback_queries = [
            f'"{research_topic}" Africa regional curriculum',
            f'"{research_topic}" regional education harmonization',
            f'"{research_topic}" cross-border education Africa',
            f'curriculum harmonization {research_topic}',
            f'regional qualification framework {research_topic}',
            f'{research_topic} EAC ECOWAS SADC education',
            f'mutual recognition qualifications {research_topic} Africa'
        ]
        print(f"📝 Using {len(fallback_queries)} fallback queries")
        return fallback_queries
    
    def search_for_papers(self, queries: List[str], max_papers: int = 50) -> List[str]:
        """Search for academic papers using AI to extract URLs from search results"""
        print(f"\n🌐 Searching for academic papers (target: {max_papers} papers)")
        
        all_urls = []
        
        for i, query in enumerate(queries[:5], 1):  # Limit to first 5 queries
            print(f"\n[Query {i}/5] Searching: '{query[:60]}...'")
            
            # Use AI to find papers for this query
            urls = self._ai_search_query(query)
            
            if urls:
                new_urls = [url for url in urls if url not in all_urls]
                all_urls.extend(new_urls)
                print(f"  ✓ Found {len(new_urls)} new papers (total: {len(all_urls)})")
                
                if len(all_urls) >= max_papers:
                    print(f"  📝 Reached target of {max_papers} papers")
                    break
            else:
                print(f"  ⚠ No papers found for this query")
            
            # Rate limiting
            time.sleep(2)
        
        # Remove duplicates and limit results
        unique_urls = list(dict.fromkeys(all_urls))[:max_papers]
        print(f"\n✓ Found {len(unique_urls)} unique papers to process")
        
        return unique_urls
    
    def _ai_search_query(self, query: str) -> List[str]:
        """Use AI to search for papers and extract URLs"""
        
        search_prompt = f"""You are an expert at finding academic research papers. I need you to find papers related to this query: "{query}"

Focus on finding papers about:
- Regional curriculum harmonization in Africa
- Cross-border educational initiatives  
- Regional education frameworks and policies
- Mutual recognition of qualifications
- Educational harmonization across African regions

Search strategy:
1. Use the query to identify the most relevant academic databases and repositories
2. Look for papers that specifically address regional (multi-country) initiatives, not just single-institution studies
3. Prioritize recent papers (2015-2024) but include seminal works
4. Find papers from African journals, international development organizations, and regional bodies

Return a JSON array of direct URLs to academic papers (preferably PDFs or full-text articles):
[
  "https://example.com/paper1.pdf",
  "https://example.com/article/12345",
  "https://doi.org/10.1000/example"
]

Find 5-10 high-quality, relevant papers. Prioritize:
- Open access papers when possible
- Papers from reputable journals and conferences
- Working papers from development organizations (World Bank, African Development Bank, etc.)
- Papers from African universities and research institutions"""

        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                'contents': [{
                    'parts': [{'text': search_prompt}]
                }],
                'generationConfig': {
                    'temperature': 0.2,
                    'maxOutputTokens': 4096,
                    'responseMimeType': 'application/json'
                }
            }
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    response_text = result['candidates'][0]['content']['parts'][0]['text']
                    try:
                        urls = json.loads(response_text.strip())
                        # Validate URLs
                        valid_urls = []
                        for url in urls:
                            if isinstance(url, str) and url.startswith('http'):
                                valid_urls.append(url)
                        return valid_urls
                    except json.JSONDecodeError:
                        print("  ⚠ Invalid JSON response from AI")
                        return []
            
            print(f"  ⚠ Search request failed: {response.status_code}")
            
        except Exception as e:
            print(f"  ⚠ Error in AI search: {e}")
        
        return []


class InteractiveResearchApp:
    """Main interactive application for research paper discovery and analysis"""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            print("❌ Error: GEMINI_API_KEY not found in environment variables")
            print("Please set your Gemini API key in the .env file")
            sys.exit(1)
        
        self.searcher = ResearchTopicSearcher(self.api_key)
        self.processor = None
        
        print("🚀 Interactive Research Paper Discovery and Analysis Tool")
        print("=" * 60)
    
    def display_menu(self):
        """Display the main menu options"""
        print("\n📋 Choose an option:")
        print("1. 🔍 Provide research topic (AI will find papers automatically)")
        print("2. 📎 Provide URLs directly (skip search)")
        print("3. ℹ️  View current processing status")
        print("4. 🚪 Exit")
        print("-" * 40)
    
    def get_user_choice(self) -> str:
        """Get and validate user menu choice"""
        while True:
            choice = input("Enter your choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return choice
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
    
    def handle_topic_search(self):
        """Handle research topic input and automatic paper discovery"""
        print("\n🔍 RESEARCH TOPIC SEARCH MODE")
        print("=" * 40)
        
        # Get research topic from user
        print("Enter your research topic. Be specific about what you're looking for.")
        print("Examples:")
        print("  - 'Regional curriculum harmonization in higher education'")
        print("  - 'Cross-border recognition of qualifications in Africa'")
        print("  - 'SADC education framework implementation'")
        print()
        
        topic = input("Research topic: ").strip()
        if not topic:
            print("❌ No topic provided. Returning to main menu.")
            return
        
        print(f"\n📝 Research topic: '{topic}'")
        
        # Ask for number of papers
        while True:
            try:
                max_papers = input(f"How many papers to find? (default: 20, max: 100): ").strip()
                if not max_papers:
                    max_papers = 20
                else:
                    max_papers = int(max_papers)
                    if max_papers < 1 or max_papers > 100:
                        print("❌ Please enter a number between 1 and 100")
                        continue
                break
            except ValueError:
                print("❌ Please enter a valid number")
        
        # Generate search queries
        queries = self.searcher.generate_search_queries(topic)
        
        # Search for papers
        urls = self.searcher.search_for_papers(queries, max_papers)
        
        if not urls:
            print("\n❌ No papers found. Please try a different topic or use direct URLs.")
            return
        
        # Save found URLs to file for processing
        self._save_urls_to_file(urls, f"auto_search_{topic[:30].replace(' ', '_')}")
        
        # Process the papers
        self._process_papers(urls, source_type="topic_search", topic=topic)
    
    def handle_direct_urls(self):
        """Handle direct URL input from user"""
        print("\n📎 DIRECT URL INPUT MODE")
        print("=" * 40)
        
        print("Enter URLs of research papers to process.")
        print("You can:")
        print("  - Enter URLs one by one (press Enter twice when done)")
        print("  - Paste multiple URLs separated by newlines")
        print("  - Provide a file path containing URLs")
        print()
        
        # Get URLs from user
        urls = []
        print("Enter URLs (press Enter twice when finished):")
        
        while True:
            url = input().strip()
            if not url:
                # Empty line - check if we should stop
                if urls:  # If we have some URLs, ask for confirmation
                    confirm = input(f"\nYou've entered {len(urls)} URLs. Process them now? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        break
                    else:
                        print("Continue entering URLs:")
                        continue
                else:
                    print("❌ No URLs provided. Returning to main menu.")
                    return
            
            # Validate URL
            if url.startswith('http'):
                urls.append(url)
                print(f"  ✓ Added: {url[:60]}{'...' if len(url) > 60 else ''}")
            else:
                print(f"  ❌ Invalid URL (must start with http): {url}")
        
        if not urls:
            print("❌ No valid URLs provided.")
            return
        
        print(f"\n📝 Ready to process {len(urls)} URLs")
        
        # Save URLs to file
        self._save_urls_to_file(urls, "direct_input")
        
        # Process the papers
        self._process_papers(urls, source_type="direct_urls")
    
    def _save_urls_to_file(self, urls: List[str], source_name: str):
        """Save URLs to a numbered file format compatible with existing processor"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"urls_{source_name}_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Research URLs - {source_name}\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total URLs: {len(urls)}\n\n")
            
            for i, url in enumerate(urls, 1):
                f.write(f"{i}. {url}\n")
        
        print(f"💾 URLs saved to: {filename}")
        return filename
    
    def _process_papers(self, urls: List[str], source_type: str, topic: str = None):
        """Process papers using the existing pipeline"""
        print(f"\n⚙️ PROCESSING {len(urls)} PAPERS")
        print("=" * 40)
        
        # Create a temporary URL file for the processor
        temp_filename = self._save_urls_to_file(urls, "temp_processing")
        
        try:
            # Initialize processor with the temporary file
            self.processor = UnifiedPaperProcessor(
                apa_file=temp_filename,
                max_workers=5,  # Moderate concurrency for interactive use
                batch_size=3    # Smaller batches for better progress feedback
            )
            
            print("🔄 Starting paper processing...")
            print("This may take several minutes depending on the number of papers.")
            print()
            
            # Run the processing
            start_time = time.time()
            self.processor.run()
            end_time = time.time()
            
            # Generate enhanced summary
            self._generate_research_summary(source_type, topic, end_time - start_time)
            
            print("\n✅ Processing completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error during processing: {e}")
            
        finally:
            # Clean up temporary file
            try:
                os.remove(temp_filename)
            except:
                pass
    
    def _generate_research_summary(self, source_type: str, topic: str, processing_time: float):
        """Generate an enhanced research summary with grounded conclusions"""
        print("\n📊 GENERATING RESEARCH SUMMARY")
        print("=" * 40)
        
        if not self.processor or not self.processor.results:
            print("❌ No processing results available for summary")
            return
        
        # Collect relevant papers
        relevant_papers = [r for r in self.processor.results if r.matches_criteria and r.extraction_data]
        
        if not relevant_papers:
            print("📝 No papers matched the regional curriculum harmonization criteria")
            return
        
        print(f"📈 Generating comprehensive research summary from {len(relevant_papers)} relevant papers...")
        
        # Prepare summary data
        summary_data = {
            'source_type': source_type,
            'research_topic': topic,
            'generation_date': datetime.now().isoformat(),
            'processing_stats': {
                'total_papers_found': len(self.processor.results),
                'relevant_papers': len(relevant_papers),
                'processing_time_minutes': processing_time / 60,
                'success_rate': len(relevant_papers) / len(self.processor.results) * 100 if self.processor.results else 0
            },
            'papers': []
        }
        
        # Extract key information from each paper
        for paper in relevant_papers:
            paper_summary = {
                'title': paper.extraction_data.get('Title', 'Unknown'),
                'authors': paper.extraction_data.get('Authors', []),
                'year': paper.extraction_data.get('Year', 'Unknown'),
                'url': paper.url,
                'key_findings': paper.extraction_data.get('KEY_FINDINGS', {}),
                'geographic_focus': paper.extraction_data.get('STUDY_CHARACTERISTICS', {}).get('Geographic_Focus', ''),
                'regional_initiatives': paper.extraction_data.get('CONTENT_ANALYSIS', {}).get('Regional_Initiatives', []),
                'main_recommendations': paper.extraction_data.get('KEY_FINDINGS', {}).get('Recommendations', [])
            }
            summary_data['papers'].append(paper_summary)
        
        # Use AI to generate comprehensive research state summary
        self._ai_generate_research_state(summary_data)
    
    def _ai_generate_research_state(self, summary_data: Dict[str, Any]):
        """Use AI to generate a comprehensive research state summary"""
        
        papers_text = ""
        for i, paper in enumerate(summary_data['papers'], 1):
            papers_text += f"\n{i}. {paper['title']} ({paper['year']})\n"
            papers_text += f"   Authors: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}\n"
            papers_text += f"   Geographic Focus: {paper['geographic_focus']}\n"
            papers_text += f"   Regional Initiatives: {', '.join(paper['regional_initiatives'][:3])}\n"
            papers_text += f"   URL: {paper['url']}\n"
        
        prompt = f"""Based on the analysis of {len(summary_data['papers'])} research papers on regional curriculum harmonization in Africa, provide a comprehensive research state summary.

PAPERS ANALYZED:
{papers_text}

Generate a detailed summary that includes:

1. **CURRENT STATE OF RESEARCH**: Overview of what the field currently knows about regional curriculum harmonization in Africa

2. **KEY THEMES AND PATTERNS**: Major themes emerging from the literature

3. **REGIONAL INITIATIVES**: Specific regional frameworks and initiatives identified (EAC, ECOWAS, SADC, etc.)

4. **IMPLEMENTATION APPROACHES**: Common approaches and strategies being used

5. **CHALLENGES AND BARRIERS**: Main obstacles identified across the literature

6. **SUCCESS FACTORS**: Key enablers and best practices

7. **RESEARCH GAPS**: Areas that need more investigation

8. **FUTURE DIRECTIONS**: Recommendations for policy and practice

For each major claim or finding, provide EXACT REFERENCES to the papers that support it (use the paper titles and years).

Format as a well-structured report with clear sections and bullet points. Make sure every significant claim is grounded in the specific papers analyzed."""

        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                'contents': [{
                    'parts': [{'text': prompt}]
                }],
                'generationConfig': {
                    'temperature': 0.2,
                    'maxOutputTokens': 8192
                }
            }
            
            response = requests.post(
                f"{self.searcher.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    research_summary = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Save the summary to file
                    summary_filename = f"research_state_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    
                    with open(summary_filename, 'w', encoding='utf-8') as f:
                        f.write("COMPREHENSIVE RESEARCH STATE SUMMARY\n")
                        f.write("=" * 60 + "\n\n")
                        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Source: {summary_data['source_type']}\n")
                        if summary_data['research_topic']:
                            f.write(f"Topic: {summary_data['research_topic']}\n")
                        f.write(f"Papers Analyzed: {len(summary_data['papers'])}\n")
                        f.write(f"Processing Time: {summary_data['processing_stats']['processing_time_minutes']:.1f} minutes\n")
                        f.write("\n" + "=" * 60 + "\n\n")
                        f.write(research_summary)
                        f.write("\n\n" + "=" * 60 + "\n")
                        f.write("PAPER REFERENCES\n")
                        f.write("=" * 60 + "\n\n")
                        
                        for i, paper in enumerate(summary_data['papers'], 1):
                            f.write(f"{i}. {paper['title']} ({paper['year']})\n")
                            f.write(f"   Authors: {', '.join(paper['authors'])}\n")
                            f.write(f"   URL: {paper['url']}\n\n")
                    
                    print(f"✅ Research state summary saved to: {summary_filename}")
                    print("\n📊 SUMMARY PREVIEW:")
                    print("-" * 40)
                    print(research_summary[:500] + "..." if len(research_summary) > 500 else research_summary)
                    print("-" * 40)
                    print(f"📄 Full summary available in: {summary_filename}")
                    
            else:
                print(f"⚠ Failed to generate AI summary: {response.status_code}")
                
        except Exception as e:
            print(f"⚠ Error generating research summary: {e}")
    
    def view_status(self):
        """View current processing status and results"""
        print("\n📊 CURRENT STATUS")
        print("=" * 40)
        
        # Check for existing output files
        output_files = [
            'paper_information.json',
            'non_matching_papers.json', 
            'paper_references.txt',
            'unified_processing_summary.txt',
            'processing_progress.json'
        ]
        
        existing_files = [f for f in output_files if os.path.exists(f)]
        
        if not existing_files:
            print("📝 No processing results found.")
            print("Run a search or provide URLs to process papers.")
            return
        
        print(f"📁 Found {len(existing_files)} result files:")
        
        for file in existing_files:
            try:
                stat = os.stat(file)
                size_kb = stat.st_size / 1024
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                print(f"  ✓ {file} ({size_kb:.1f} KB, modified: {mod_time.strftime('%Y-%m-%d %H:%M')})")
            except:
                print(f"  ✓ {file}")
        
        # Try to load and display summary stats
        try:
            if os.path.exists('processing_progress.json'):
                with open('processing_progress.json', 'r') as f:
                    progress = json.load(f)
                    
                stats = progress.get('stats', {})
                print(f"\n📈 Processing Statistics:")
                print(f"  Total papers processed: {stats.get('processed', 0)}")
                print(f"  Papers matching criteria: {stats.get('papers_matching_criteria', 0)}")
                print(f"  Papers not matching: {stats.get('papers_not_matching_criteria', 0)}")
                print(f"  Downloads successful: {stats.get('download_success', 0)}")
                
        except Exception as e:
            print(f"⚠ Could not load detailed statistics: {e}")
    
    def run(self):
        """Main application loop"""
        while True:
            self.display_menu()
            choice = self.get_user_choice()
            
            if choice == '1':
                self.handle_topic_search()
            elif choice == '2':
                self.handle_direct_urls()
            elif choice == '3':
                self.view_status()
            elif choice == '4':
                print("\n👋 Thank you for using the Interactive Research Tool!")
                print("📁 Check the generated files for your research results.")
                sys.exit(0)
            
            # Ask if user wants to continue
            print("\n" + "-" * 40)
            continue_choice = input("Press Enter to return to main menu (or 'q' to quit): ").strip().lower()
            if continue_choice == 'q':
                print("\n👋 Goodbye!")
                sys.exit(0)


def main():
    """Main entry point"""
    try:
        app = InteractiveResearchApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()