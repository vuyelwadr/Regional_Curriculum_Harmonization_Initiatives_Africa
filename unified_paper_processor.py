import os
import re
import time
import json
import requests
import threading
import traceback
import queue
import base64
import shutil
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse, urljoin, quote
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Import PDF processing capabilities
import PyPDF2
from bs4 import BeautifulSoup

# Try importing optional libraries
try:
    from weasyprint import HTML as WeasyHTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class PaperResult:
    """Data class for paper processing results"""
    apa_number: int
    url: str
    original_reference: str
    status: str = 'pending'  # pending, success, failed, not_relevant
    
    # Download info
    pdf_url: Optional[str] = None
    download_path: Optional[str] = None
    download_type: Optional[str] = None  # direct_pdf, html_fulltext, open_repository
    
    # Extraction info
    matches_criteria: Optional[bool] = None
    criteria_explanation: Optional[str] = None
    extraction_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    error: Optional[str] = None
    ai_interactions: List[Dict[str, Any]] = field(default_factory=list)
    processing_time: float = 0.0
    batch_id: Optional[int] = None


class RateLimiter:
    """Precise rate limiter for API calls"""
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # 6 seconds for 10 RPM
        self.request_times = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to maintain rate limit"""
        with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            if len(self.request_times) >= self.requests_per_minute:
                # Need to wait
                oldest_request = min(self.request_times)
                wait_time = 60 - (now - oldest_request) + 0.1  # Add small buffer
                if wait_time > 0:
                    print(f"Rate limit reached. Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    now = time.time()
            
            self.request_times.append(now)


class UnifiedPaperProcessor:
    """Combined paper downloader and information extractor with enhanced full text finding"""
    
    def __init__(self, apa_file: str = 'urls_combined.txt', max_workers: int = 10, batch_size: int = 5):
        self.apa_file = apa_file
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        self.max_workers = max_workers
        self.batch_size = batch_size  # Number of papers per batch
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
        
        # Directories
        self.download_dir = 'downloads'
        self.not_relevant_dir = os.path.join(self.download_dir, 'not_relevant')
        self.html_dir = os.path.join(self.download_dir, 'html')
        self.temp_dir = os.path.join(self.download_dir, 'temp')  # Add temp directory
        self.model_dir = 'model'
        
        # Create directories
        for dir_path in [self.download_dir, self.not_relevant_dir, self.html_dir, self.temp_dir, self.model_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Output files
        self.paper_info_file = 'paper_information.json'
        self.non_matching_file = 'non_matching_papers.json'
        self.references_file = 'paper_references.txt'
        self.summary_file = 'unified_processing_summary.txt'
        self.extraction_summary_file = 'summary_paper_extraction.txt'
        self.progress_file = 'processing_progress.json'
        
        # Rate limiting
        self.rate_limiter = RateLimiter(requests_per_minute=10)
        
        # Session for HTTP requests
        self.session = self._create_session()
        
        # Results storage
        self.results = []
        self.results_lock = threading.Lock()
        
        # Batch processing queue
        self.batch_queue = queue.Queue()
        self.batch_results = {}
        
        # Add model response tracking
        self.model_responses = []
        self.model_response_counter = 0
        
        # Statistics
        self.stats = {
            'total_urls': 0,
            'processed': 0,
            'papers_matching_criteria': 0,
            'papers_not_matching_criteria': 0,
            'download_success': 0,
            'download_failed': 0,
            'direct_pdf': 0,
            'html_fulltext': 0,
            'open_repository': 0,
            'ai_requests': 0,
            'ai_failures': 0,
            'paywall_detected': 0,
            'not_found_404': 0,
            'batches_processed': 0,
            # Add new stats
            'fulltext_search_attempts': 0,
            'fulltext_found_method': defaultdict(int),
            'extraction_with_fulltext': 0,
            'extraction_without_fulltext': 0,
            'immediate_pdf_downloads': 0,
            'pdf_download_failures': 0,
            'temp_files_cleaned': 0,
            'processing_errors': defaultdict(int),
            'batch_timings': [],
            'paper_timings': []
        }
        
        # Enhanced full text search repositories
        self.repositories = [
            {'name': 'arXiv', 'search_url': 'https://arxiv.org/search/?query={query}&searchtype=all'},
            {'name': 'ResearchGate', 'search_url': 'https://www.researchgate.net/search/publication?q={query}'},
            {'name': 'Google Scholar', 'search_url': 'https://scholar.google.com/scholar?q={query}'},
            {'name': 'CORE', 'search_url': 'https://core.ac.uk/search?q={query}'},
            {'name': 'Semantic Scholar', 'search_url': 'https://www.semanticscholar.org/search?q={query}'},
            {'name': 'DOAJ', 'search_url': 'https://doaj.org/search/articles?source=%7B%22query%22%3A%5B%22{query}%22%5D%7D'},
            {'name': 'BASE', 'search_url': 'https://www.base-search.net/Search/Results?lookfor={query}'},
            {'name': 'SSRN', 'search_url': 'https://www.ssrn.com/index.cfm/en/search/?term={query}'},
            {'name': 'Academia.edu', 'search_url': 'https://www.academia.edu/search?q={query}'}
        ]
        
        # API endpoints for DOI resolution
        self.doi_apis = {
            'unpaywall': 'https://api.unpaywall.org/v2/{doi}?email=researcher@example.com',
            'crossref': 'https://api.crossref.org/works/{doi}',
            'datacite': 'https://api.datacite.org/dois/{doi}'
        }
        
        # Enhanced find fulltext prompt
        self.find_fulltext_prompt = """You are an expert at finding full text of academic papers. Analyze the given content and:

1. FIRST: Check if this is already a PDF or contains the full paper text (not just abstract/landing page)
2. SECOND: Extract paper metadata (title, authors, DOI, journal, year)
3. THIRD: Find ALL possible full text access points:
   - Direct PDF download links
   - "Full Text", "View PDF", "Download", "Get PDF" buttons/links
   - Publisher full text pages
   - Open access repository links
   - DOI URLs that might redirect to full text
   - Alternative versions (preprints, postprints)
   - Institutional repository links

Be thorough and look for subtle indicators like:
- Links ending in .pdf
- URLs containing "download", "pdf", "fulltext"
- Repository domains (arxiv.org, researchgate.net, etc.)
- Publisher platforms (springer, elsevier, wiley, etc.)

Respond with JSON:
{
  "is_fulltext": true/false,
  "content_type": "pdf/html_fulltext/abstract_only/landing_page",
  "paper_metadata": {
    "title": "paper title",
    "authors": ["author1", "author2"],
    "doi": "DOI if found",
    "journal": "journal name",
    "year": "year",
    "abstract": "abstract text"
  },
  "fulltext_links": [
    {"url": "link", "type": "direct_pdf/publisher_page/repository", "confidence": "high/medium/low"}
  ],
  "repository_indicators": ["arxiv", "researchgate", "academia", "institutional"],
  "paywall_detected": true/false,
  "open_access_indicators": ["gold", "green", "bronze"],
  "confidence": "high/medium/low"
}"""

        # Add new prompts for finding full text
        self.extraction_prompt = """You are analyzing the FULL TEXT of an academic paper to determine if it matches specific research criteria and extract detailed information.

IMPORTANT: You now have access to the FULL PAPER, not just the abstract. Look throughout the entire document for evidence of regional curriculum harmonization.

RESEARCH CRITERIA:
- The paper must focus on REGIONAL curriculum harmonization initiatives (not single-institution transformations)
- It should involve multiple African countries or regions (like EAC, ECOWAS, SADC frameworks)
- It should address harmonization across institutions/countries, not just within one university
- Look for mentions of: regional frameworks, cross-border education, mutual recognition, credit transfer systems, regional qualifications frameworks

For each paper, provide a JSON object with these fields:

REQUIRED FIELDS (always include):
{
  "paper_filename": "filename or URL",
  "MATCHES_CRITERIA": true/false,
  "CRITERIA_MATCH_EXPLANATION": "explanation with specific evidence from the full text",
  "Title": "paper title",
  "Authors": ["list of authors"],
  "Year": "publication year"
}

IF MATCHES_CRITERIA is true, also include:

{
  "BIBLIOGRAPHIC_DETAILS": {
    "Journal_Publisher": "journal name",
    "DOI_URL": "DOI or URL",
    "APA_Reference": "complete APA 7th reference"
  },
  "STUDY_CHARACTERISTICS": {
    "Research_Design": "methodology",
    "Geographic_Focus": "countries/regions",
    "Educational_Level": "level/sector",
    "Sample_Size": "sample info",
    "Is_Longitudinal": true/false
  },
  "CONTENT_ANALYSIS": {
    "Theoretical_Framework": "frameworks used",
    "Harmonization_Definition": "how defined",
    "Regional_Initiatives": ["initiatives studied"],
    "Implementation_Approaches": ["approaches"],
    "Stakeholder_Groups": ["stakeholders"],
    "Data_Sources": ["data sources"]
  },
  "KEY_FINDINGS": {
    "Main_Findings": ["key findings"],
    "Challenges_Barriers": ["challenges"],
    "Success_Factors": ["enablers"],
    "Recommendations": ["recommendations"],
    "Future_Research": ["suggestions"],
    "Specific_Examples": ["examples"]
  },
  "THEMATIC_CLASSIFICATION": {
    "Implementation_Mechanisms": ["mechanisms"],
    "Challenges_and_Barriers": ["barriers"],
    "Success_Factors_Enablers": ["factors"],
    "Outcomes_and_Impacts": ["impacts"]
  }
}"""

        # Track full text search attempts
        self.fulltext_search_attempts = {}
        self.max_fulltext_attempts = 3

        # Load progress if exists
        self.processed_papers = self._load_progress()

    def _load_progress(self) -> Set[int]:
        """Load processing progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_apa_numbers', []))
            except:
                pass
        return set()

    def _save_progress(self):
        """Save processing progress"""
        with self.results_lock:
            processed_numbers = [r.apa_number for r in self.results if r.status in ['success', 'failed']]
            data = {
                'processed_apa_numbers': processed_numbers,
                'stats': self.stats,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)

    def _create_session(self) -> requests.Session:
        """Create HTTP session with default headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session

    def save_model_response(self, response_type: str, content: Any, metadata: Dict[str, Any] = None) -> str:
        """Save model response to file in model directory"""
        self.model_response_counter += 1
        filename = f"response_{self.model_response_counter:04d}_{response_type}.json"
        filepath = os.path.join(self.model_dir, filename)
        
        response_data = {
            'response_id': self.model_response_counter,
            'type': response_type,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {},
            'content': content
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)
        
        # Track response
        self.model_responses.append({
            'id': self.model_response_counter,
            'type': response_type,
            'file': filename,
            'metadata': metadata
        })
        
        return filename

    def extract_urls_from_apa(self) -> List[Dict[str, Any]]:
        """Extract URLs from APA file"""
        urls = []
        
        try:
            with open(self.apa_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into references
            references = re.split(r'\n(?=\d+\.\s+)', content)
            
            for ref in references:
                if not ref.strip():
                    continue
                
                # Extract reference number
                ref_match = re.match(r'^(\d+)\.\s+', ref)
                if ref_match:
                    apa_number = int(ref_match.group(1))
                    
                    # Skip if already processed
                    if apa_number in self.processed_papers:
                        print(f"Skipping #{apa_number} (already processed)")
                        continue
                    
                    # Find URLs
                    url_matches = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', ref)
                    if url_matches:
                        # Clean and use first URL
                        for url in url_matches:
                            url = url.rstrip('.,;:)')
                            
                            # Validate URL
                            try:
                                parsed = urlparse(url)
                                if parsed.scheme and parsed.netloc:
                                    urls.append({
                                        'apa_number': apa_number,
                                        'url': url,
                                        'original_reference': ref.strip()
                                    })
                                    break
                            except:
                                continue
        
        except Exception as e:
            print(f"Error reading APA file: {str(e)}")
        
        self.stats['total_urls'] = len(urls)
        return urls

    def extract_doi_from_text(self, text: str) -> Optional[str]:
        """Extract DOI from text using regex patterns"""
        doi_patterns = [
            r'doi:\s*([^\s,\]]+)',
            r'doi\.org/([^\s,\]]+)',
            r'DOI:\s*([^\s,\]]+)',
            r'https?://(?:dx\.)?doi\.org/([^\s,\]]+)',
            r'doi\s*=\s*["\']?([^"\'>\s,\]]+)["\']?'
        ]
        
        for pattern in doi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                doi = match.group(1).strip()
                # Clean up common suffixes
                doi = re.sub(r'[.,;)\]]+$', '', doi)
                if doi and '/' in doi:
                    return doi
        return None

    def check_if_pdf_url(self, url: str) -> Dict[str, Any]:
        """Check if URL directly points to a PDF with robust error handling"""
        try:
            # First check URL extension
            if url.lower().endswith('.pdf'):
                return {'is_pdf': True, 'method': 'url_extension', 'url': url}
            
            # Robust HEAD request with multiple attempts
            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = self.session.head(url, timeout=15, allow_redirects=True)
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if 'pdf' in content_type or 'application/pdf' in content_type:
                        return {'is_pdf': True, 'method': 'content_type', 'url': response.url or url}
                    
                    # Check for PDF indicators in final URL after redirects
                    final_url = response.url or url
                    if final_url.lower().endswith('.pdf') or 'pdf' in final_url.lower():
                        return {'is_pdf': True, 'method': 'redirected_url', 'url': final_url}
                    
                    # Successfully checked, not a PDF
                    return {'is_pdf': False, 'method': 'checked_ok', 'url': url}
                    
                except Exception as e:
                    if retry < max_retries - 1:
                        print(f"    PDF check retry {retry + 1}/{max_retries}: {str(e)}")
                        time.sleep(1)  # Brief pause before retry
                        continue
                    else:
                        # Final attempt failed - return error info but don't fail completely
                        print(f"    PDF check failed after {max_retries} attempts: {str(e)}")
                        return {
                            'is_pdf': False, 
                            'method': 'connection_failed', 
                            'url': url, 
                            'error': str(e),
                            'should_continue': True  # Signal that we should try other strategies
                        }
                        
        except Exception as e:
            print(f"    Unexpected error in PDF check: {str(e)}")
            return {
                'is_pdf': False, 
                'method': 'unexpected_error', 
                'url': url, 
                'error': str(e),
                'should_continue': True
            }
        
        return {'is_pdf': False, 'method': 'not_detected', 'url': url}

    def robust_get_content(self, url: str, max_retries: int = 3) -> Dict[str, Any]:
        """Universal robust content fetching with multiple strategies"""
        
        # Strategy 1: Standard GET request with retries
        for retry in range(max_retries):
            try:
                response = self.session.get(url, timeout=30, allow_redirects=True)
                if response.status_code == 200:
                    return {
                        'success': True,
                        'content': response.text,
                        'url': response.url or url,
                        'method': f'standard_get_retry_{retry + 1}'
                    }
                elif response.status_code in [403, 429]:  # Rate limited or forbidden
                    wait_time = (2 ** retry) * 2  # Longer wait for these errors
                    print(f"    HTTP {response.status_code}, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    HTTP {response.status_code} on attempt {retry + 1}")
                    
            except requests.exceptions.ConnectionError as e:
                if retry < max_retries - 1:
                    wait_time = 2 ** retry
                    print(f"    Connection error (attempt {retry + 1}/{max_retries}): {str(e)}")
                    print(f"    Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    Connection failed after {max_retries} attempts: {str(e)}")
                    
            except requests.exceptions.Timeout as e:
                if retry < max_retries - 1:
                    print(f"    Timeout (attempt {retry + 1}/{max_retries}), retrying with longer timeout...")
                    # Increase timeout on retry
                    try:
                        response = self.session.get(url, timeout=60, allow_redirects=True)
                        if response.status_code == 200:
                            return {
                                'success': True,
                                'content': response.text,
                                'url': response.url or url,
                                'method': f'extended_timeout_retry_{retry + 1}'
                            }
                    except:
                        continue
                else:
                    print(f"    Timeout after {max_retries} attempts: {str(e)}")
                    
            except Exception as e:
                print(f"    Unexpected error (attempt {retry + 1}/{max_retries}): {str(e)}")
                if retry < max_retries - 1:
                    time.sleep(2 ** retry)
                    continue
        
        # Strategy 2: Try with different headers (some sites block certain user agents)
        print(f"    Trying with alternative headers...")
        alternative_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        temp_session = requests.Session()
        temp_session.headers.update(alternative_headers)
        
        try:
            response = temp_session.get(url, timeout=45, allow_redirects=True)
            if response.status_code == 200:
                return {
                    'success': True,
                    'content': response.text,
                    'url': response.url or url,
                    'method': 'alternative_headers'
                }
        except Exception as e:
            print(f"    Alternative headers failed: {str(e)}")
        
        # Strategy 3: Try common URL variations for repositories
        if any(indicator in url.lower() for indicator in ['handle', 'dspace', 'repository', 'archive']):
            print(f"    Trying repository URL variations...")
            variations = self._get_repository_url_variations(url)
            
            for i, variant_url in enumerate(variations[:3]):  # Try top 3 variations
                try:
                    response = self.session.get(variant_url, timeout=30)
                    if response.status_code == 200:
                        return {
                            'success': True,
                            'content': response.text,
                            'url': response.url or variant_url,
                            'method': f'repository_variation_{i + 1}'
                        }
                except Exception as e:
                    print(f"    Repository variation {i + 1} failed: {str(e)}")
                    continue
        
        return {
            'success': False,
            'error': 'All content fetching strategies failed',
            'method': 'all_failed'
        }

    def _get_repository_url_variations(self, url: str) -> List[str]:
        """Generate common URL variations for repository sites"""
        variations = []
        
        # For handle-based repositories (DSpace, etc.)
        if 'handle' in url.lower():
            # Try adding common suffixes
            variations.extend([
                url + '?show=full',
                url + '/pdf',
                url + '/download',
                url.replace('/handle/', '/bitstream/handle/') + '/1/document.pdf',
                url.replace('/handle/', '/bitstream/handle/') + '/1/' + url.split('/')[-1] + '.pdf'
            ])
        
        # For general repositories
        variations.extend([
            url + '/fulltext',
            url + '/pdf',
            url + '/download',
            url.rstrip('/') + '.pdf',
            url + '?format=pdf'
        ])
        
        # Try HTTPS if HTTP
        if url.startswith('http://'):
            variations.append(url.replace('http://', 'https://'))
        
        return variations

    def find_fulltext_with_ai(self, url: str, attempt: int = 1) -> Dict[str, Any]:
        """Enhanced full text finding with universal robust error handling"""
        print(f"  {'  ' * (attempt-1)}Finding full text (attempt {attempt}): {url}")
        
        self.stats['fulltext_search_attempts'] += 1
        
        # Strategy 1: Check if URL is already a PDF (with robust error handling)
        pdf_check = self.check_if_pdf_url(url)
        if pdf_check['is_pdf']:
            print(f"  {'  ' * (attempt-1)}✓ Direct PDF found via {pdf_check['method']}")
            return {
                'status': 'found_fulltext',
                'url': pdf_check['url'],
                'type': 'direct_pdf',
                'method': pdf_check['method'],
                'confidence': 'high'
            }
        
        # Don't give up if PDF check failed due to connection issues
        if pdf_check.get('method') in ['connection_failed', 'unexpected_error']:
            print(f"  {'  ' * (attempt-1)}PDF check failed, but continuing with other strategies...")
        
        # Strategy 2: Robust content fetching and AI analysis
        content_result = self.robust_get_content(url)
        
        if not content_result['success']:
            print(f"  {'  ' * (attempt-1)}⚠ Could not fetch content: {content_result.get('error', 'Unknown error')}")
            return {
                'status': 'error',
                'url': url,
                'error': content_result.get('error', 'Content fetching failed'),
                'attempted_strategies': ['pdf_check', 'robust_content_fetch']
            }
        
        print(f"  {'  ' * (attempt-1)}✓ Content fetched via {content_result['method']}")
        content = content_result['content']
        final_url = content_result['url']
        
        # Extract DOI from content
        extracted_doi = self.extract_doi_from_text(content)
        
        # Strategy 3: Use AI to analyze the page
        try:
            self.rate_limiter.wait_if_needed()
            self.stats['ai_requests'] += 1
            
            # Prepare AI analysis
            headers = {'Content-Type': 'application/json'}
            ai_content = f"{self.find_fulltext_prompt}\n\nAnalyze this webpage:\nURL: {final_url}\nContent (first 8000 chars):\n{content[:8000]}"
            
            data = {
                'contents': [{
                    'parts': [{'text': ai_content}]
                }],
                'generationConfig': {
                    'temperature': 0.1,
                    'maxOutputTokens': 4096,
                    'responseMimeType': 'application/json'
                }
            }
            
            ai_response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=120
            )
            
            # Save the model response
            response_metadata = {
                'url': url,
                'final_url': final_url,
                'attempt': attempt,
                'purpose': 'find_fulltext'
            }
            
            if ai_response.status_code == 200:
                result = ai_response.json()
                
                # Save successful response
                self.save_model_response('find_fulltext_success', result, response_metadata)
                
                if 'candidates' in result and result['candidates']:
                    response_text = result['candidates'][0]['content']['parts'][0]['text']
                    analysis = json.loads(response_text.strip())
                    
                    # Track method statistics
                    if analysis.get('is_fulltext'):
                        self.stats['fulltext_found_method']['already_fulltext'] += 1
                    
                    # Check if AI found it's already full text
                    if analysis.get('is_fulltext') and analysis.get('content_type') in ['pdf', 'html_fulltext']:
                        return {
                            'status': 'found_fulltext',
                            'url': final_url,
                            'type': analysis.get('content_type', 'html_fulltext'),
                            'method': 'ai_analysis',
                            'confidence': analysis.get('confidence', 'medium'),
                            'metadata': analysis.get('paper_metadata', {})
                        }
                    
                    # Strategy 4: Try AI-suggested full text links
                    fulltext_links = analysis.get('fulltext_links', [])
                    if fulltext_links and attempt < self.max_fulltext_attempts:
                        # Sort by confidence
                        fulltext_links.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x.get('confidence', 'low'), 1), reverse=True)
                        
                        for link_info in fulltext_links[:3]:  # Try top 3
                            try:
                                link_url = urljoin(final_url, link_info['url'])
                                print(f"  {'  ' * attempt}Trying AI-suggested link: {link_url}")
                                
                                # Use robust PDF checking for suggested links too
                                pdf_check = self.check_if_pdf_url(link_url)
                                if pdf_check['is_pdf']:
                                    return {
                                        'status': 'found_fulltext',
                                        'url': pdf_check['url'],
                                        'type': 'direct_pdf',
                                        'method': 'ai_suggested_pdf',
                                        'confidence': 'high'
                                    }
                                
                                # Recursively analyze the link (with robust error handling)
                                if attempt < self.max_fulltext_attempts:
                                    result = self.find_fulltext_with_ai(link_url, attempt + 1)
                                    if result['status'] == 'found_fulltext':
                                        return result
                                        
                            except Exception as e:
                                print(f"  {'  ' * attempt}Failed to check suggested link: {str(e)}")
                                continue
                    
                    # Strategy 5: DOI-based search
                    paper_doi = extracted_doi or analysis.get('paper_metadata', {}).get('doi')
                    if paper_doi and attempt <= 2:  # Only try DOI search early
                        print(f"  {'  ' * attempt}Trying DOI resolution: {paper_doi}")
                        doi_sources = self.resolve_doi_to_fulltext(paper_doi)
                        
                        for source in doi_sources[:3]:  # Try top 3 DOI sources
                            try:
                                if source['type'] in ['open_access_pdf', 'publisher_pdf']:
                                    pdf_check = self.check_if_pdf_url(source['url'])
                                    if pdf_check['is_pdf']:
                                        return {
                                            'status': 'found_fulltext',
                                            'url': pdf_check['url'],
                                            'type': 'direct_pdf',
                                            'method': f"doi_{source['source'].lower()}",
                                            'confidence': 'high'
                                        }
                            except Exception as e:
                                print(f"  {'  ' * attempt}DOI source failed: {str(e)}")
                                continue
                    
                    # Strategy 6: Repository search (only on first attempt)
                    if attempt == 1:
                        paper_metadata = analysis.get('paper_metadata', {})
                        if paper_metadata.get('title'):
                            print(f"  {'  ' * attempt}Searching repositories...")
                            repo_sources = self.search_repositories(paper_metadata)
                            
                            # Try arXiv sources specifically (they're most reliable)
                            arxiv_sources = [s for s in repo_sources if s['source'] == 'arXiv' and s['type'] == 'repository_pdf']
                            for source in arxiv_sources[:2]:
                                try:
                                    pdf_check = self.check_if_pdf_url(source['url'])
                                    if pdf_check['is_pdf']:
                                        return {
                                            'status': 'found_fulltext',
                                            'url': pdf_check['url'],
                                            'type': 'direct_pdf',
                                            'method': 'arxiv_search',
                                            'confidence': 'high'
                                        }
                                except Exception as e:
                                    continue
                    
                    # Return analysis for potential later use
                    return {
                        'status': 'no_fulltext_found',
                        'url': final_url,
                        'analysis': analysis,
                        'attempted_strategies': ['pdf_check', 'robust_content_fetch', 'ai_analysis', 'fulltext_links', 'doi_resolution', 'repository_search'],
                        'metadata': analysis.get('paper_metadata', {}),
                        'content_fetched': True
                    }
            
            else:
                # Save error response
                self.save_model_response('find_fulltext_error', {
                    'status_code': ai_response.status_code,
                    'error': ai_response.text
                }, response_metadata)
                
                self.stats['ai_failures'] += 1
                print(f"  {'  ' * attempt}AI API error: {ai_response.status_code}")
        
        except Exception as e:
            # Save exception
            self.save_model_response('find_fulltext_exception', {
                'error': str(e),
                'traceback': traceback.format_exc()
            }, {'url': url, 'attempt': attempt})
            
            print(f"  {'  ' * attempt}Error in AI analysis: {str(e)}")
            self.stats['processing_errors']['ai_analysis'] += 1
        
        return {
            'status': 'error',
            'url': url,
            'error': 'AI analysis failed but content was fetched',
            'content_available': True
        }

    def _try_repository_alternative(self, url: str, attempt: int) -> Dict[str, Any]:
        """Alternative approach for repository URLs when direct access fails"""
        print(f"  {'  ' * (attempt-1)}Trying repository-specific approach...")
        
        # For DSpace repositories, try common PDF patterns
        if 'dspace' in url.lower() and 'handle' in url.lower():
            # DSpace often has predictable PDF URLs
            handle_part = url.split('handle/')[-1]
            possible_pdf_urls = [
                url + '/pdf',
                url + '/download',
                url.replace('/handle/', '/bitstream/handle/') + '/1/' + handle_part.split('/')[-1] + '.pdf',
                url + '?mode=full'
            ]
            
            for pdf_url in possible_pdf_urls:
                try:
                    pdf_check = self.check_if_pdf_url(pdf_url)
                    if pdf_check['is_pdf']:
                        return {
                            'status': 'found_fulltext',
                            'url': pdf_check['url'],
                            'type': 'direct_pdf',
                            'method': 'repository_pattern_match',
                            'confidence': 'high'
                        }
                except:
                    continue
        
        return {
            'status': 'error',
            'error': 'Repository access failed and no alternative found'
        }

    def download_pdf_immediately(self, url: str, apa_number: int) -> Optional[str]:
        """Download PDF immediately when full text is found"""
        try:
            print(f"  📥 Downloading PDF immediately to avoid expiration...")
            self.stats['immediate_pdf_downloads'] += 1
            
            # Generate filename
            filename = f"paper_{apa_number:03d}.pdf"
            
            # Download with retry
            response = self.download_with_retry(url)
            if response:
                # Save to temporary location (we don't know if it matches criteria yet)
                temp_filepath = os.path.join(self.temp_dir, filename)
                
                with open(temp_filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                response.close()
                print(f"  ✓ PDF saved temporarily: {temp_filepath}")
                return temp_filepath
            else:
                print(f"  ✗ Failed to download PDF from: {url}")
                self.stats['pdf_download_failures'] += 1
                return None
                
        except Exception as e:
            print(f"  ✗ Error downloading PDF: {str(e)}")
            self.stats['pdf_download_failures'] += 1
            self.stats['processing_errors']['pdf_download'] += 1
            return None

    def resolve_doi_to_fulltext(self, doi: str) -> List[Dict[str, Any]]:
        """Resolve DOI to potential full text sources"""
        sources = []
        
        # Try Unpaywall API
        try:
            unpaywall_url = self.doi_apis['unpaywall'].format(doi=doi)
            response = self.session.get(unpaywall_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('is_oa'):
                    best_oa = data.get('best_oa_location', {})
                    if best_oa.get('url_for_pdf'):
                        sources.append({
                            'url': best_oa['url_for_pdf'],
                            'type': 'open_access_pdf',
                            'source': 'unpaywall',
                            'confidence': 'high'
                        })
        except Exception as e:
            print(f"    Unpaywall API error: {str(e)}")
        
        # Try CrossRef
        try:
            crossref_url = self.doi_apis['crossref'].format(doi=doi)
            response = self.session.get(crossref_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                message = data.get('message', {})
                
                # Check for links
                for link in message.get('link', []):
                    if link.get('content-type') == 'application/pdf':
                        sources.append({
                            'url': link.get('URL'),
                            'type': 'publisher_pdf',
                            'source': 'crossref',
                            'confidence': 'medium'
                        })
        except Exception as e:
            print(f"    CrossRef API error: {str(e)}")
        
        # Direct DOI.org resolution
        doi_url = f"https://doi.org/{doi}"
        sources.append({
            'url': doi_url,
            'type': 'doi_redirect',
            'source': 'doi.org',
            'confidence': 'low'
        })
        
        return sources

    def search_repositories(self, paper_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search repositories for full text using paper metadata"""
        sources = []
        title = paper_metadata.get('title', '')
        
        if not title:
            return sources
        
        # Simple repository search simulation
        # In a real implementation, this would make API calls to repository search endpoints
        
        # Check for arXiv pattern in title or metadata
        if any(term in title.lower() for term in ['arxiv', 'preprint']):
            sources.append({
                'url': f"https://arxiv.org/search/?query={quote(title)}&searchtype=title",
                'type': 'repository_search',
                'source': 'arXiv',
                'confidence': 'medium'
            })
        
        # Add generic repository search
        sources.append({
            'url': f"https://scholar.google.com/scholar?q={quote(title)}",
            'type': 'repository_search',
            'source': 'Google Scholar',
            'confidence': 'low'
        })
        
        return sources

    def analyze_paper_with_fulltext_and_fallback(self, paper_info: Dict[str, Any], fulltext_url: str, local_pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """Analyze paper with full text URL, with fallback to local PDF - MEMORY OPTIMIZED"""
        self.rate_limiter.wait_if_needed()
        
        # First, try with the original URL
        try:
            print(f"  🔍 Attempting analysis with URL: {fulltext_url}")
            headers = {'Content-Type': 'application/json'}
            data = {
                'contents': [{
                    'parts': [
                        {'text': f"{self.extraction_prompt}\n\nAnalyze this paper: {fulltext_url}"}
                    ]
                }],
                'generationConfig': {
                    'temperature': 0.1,
                    'maxOutputTokens': 65536,
                    'responseMimeType': 'application/json'
                },
                'tools': [
                    {'url_context': {}}  # Use URL context to read the full paper
                ]
            }
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=300
            )
            
            # Save model response
            response_metadata = {
                'apa_number': paper_info['apa_number'],
                'url': fulltext_url,
                'method': 'url_analysis',
                'purpose': 'extract_paper_info'
            }
            
            if response.status_code == 200:
                result = response.json()
                
                # Save successful response
                self.save_model_response('extract_info_success', result, response_metadata)
                
                if 'candidates' in result and result['candidates']:
                    response_text = result['candidates'][0]['content']['parts'][0]['text']
                    analysis = json.loads(response_text.strip())
                    print(f"  ✓ Analysis successful with URL")
                    
                    # Track statistics
                    if analysis.get('MATCHES_CRITERIA'):
                        self.stats['extraction_with_fulltext'] += 1
                    
                    return analysis
            else:
                # Save error response
                self.save_model_response('extract_info_error', {
                    'status_code': response.status_code,
                    'error': response.text
                }, response_metadata)
                
                print(f"  ⚠ URL analysis failed (status: {response.status_code})")
                
        except Exception as e:
            # Save exception
            self.save_model_response('extract_info_exception', {
                'error': str(e),
                'traceback': traceback.format_exc()
            }, {'apa_number': paper_info['apa_number'], 'url': fulltext_url, 'method': 'url_analysis'})
            
            print(f"  ⚠ URL analysis failed: {str(e)}")
            self.stats['processing_errors']['url_analysis'] += 1
        
        # Fallback: Try with local PDF if available - MEMORY OPTIMIZED
        if local_pdf_path and os.path.exists(local_pdf_path):
            try:
                print(f"  🔄 Falling back to local PDF: {local_pdf_path}")
                
                # Check file size first
                file_size = os.path.getsize(local_pdf_path)
                if file_size > 50 * 1024 * 1024:  # 50MB limit
                    print(f"  ⚠ PDF too large ({file_size / 1024 / 1024:.1f}MB), skipping to avoid memory issues")
                    self.stats['processing_errors']['pdf_too_large'] += 1
                    return {'error': 'PDF too large for processing'}
                
                # Upload the local PDF and analyze it
                headers = {'Content-Type': 'application/json'}
                
                # Read and encode the PDF in chunks to avoid memory spikes
                chunk_size = 1024 * 1024  # 1MB chunks
                pdf_chunks = []
                
                with open(local_pdf_path, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        pdf_chunks.append(chunk)
                
                # Combine and encode
                pdf_data = base64.b64encode(b''.join(pdf_chunks)).decode('utf-8')
                
                # Clear chunks from memory
                pdf_chunks = None
                
                data = {
                    'contents': [{
                        'parts': [
                            {'text': self.extraction_prompt},
                            {
                                'inline_data': {
                                    'mime_type': 'application/pdf',
                                    'data': pdf_data
                                }
                            }
                        ]
                    }],
                    'generationConfig': {
                        'temperature': 0.1,
                        'maxOutputTokens': 65536,
                        'responseMimeType': 'application/json'
                    }
                }
                
                response = requests.post(
                    f"{self.base_url}?key={self.api_key}",
                    headers=headers,
                    json=data,
                    timeout=300
                )
                
                # Clear pdf_data from memory immediately after sending
                pdf_data = None
                data = None
                
                # Save model response
                response_metadata = {
                    'apa_number': paper_info['apa_number'],
                    'local_pdf': local_pdf_path,
                    'method': 'local_pdf_fallback',
                    'purpose': 'extract_paper_info',
                    'file_size_mb': file_size / 1024 / 1024
                }
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Save successful response
                    self.save_model_response('extract_info_fallback_success', result, response_metadata)
                    
                    if 'candidates' in result and result['candidates']:
                        response_text = result['candidates'][0]['content']['parts'][0]['text']
                        analysis = json.loads(response_text.strip())
                        print(f"  ✓ Analysis successful with local PDF")
                        
                        # Track statistics
                        if analysis.get('MATCHES_CRITERIA'):
                            self.stats['extraction_with_fulltext'] += 1
                        
                        return analysis
                else:
                    # Save error response
                    self.save_model_response('extract_info_fallback_error', {
                        'status_code': response.status_code,
                        'error': response.text
                    }, response_metadata)
                    
                    print(f"  ✗ Local PDF analysis failed (status: {response.status_code})")
                    
            except MemoryError:
                print(f"  ✗ Memory error processing PDF")
                self.stats['processing_errors']['memory_error'] += 1
                return {'error': 'Memory error processing PDF'}
            except Exception as e:
                # Save exception
                self.save_model_response('extract_info_fallback_exception', {
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }, {'apa_number': paper_info['apa_number'], 'local_pdf': local_pdf_path})
                
                print(f"  ✗ Local PDF analysis failed: {str(e)}")
                self.stats['processing_errors']['local_pdf_analysis'] += 1
        
        self.stats['extraction_without_fulltext'] += 1
        return {'error': 'Both URL and local PDF analysis failed'}

    def move_temp_pdf_to_final_location(self, temp_path: str, apa_number: int, matches_criteria: bool) -> Optional[str]:
        """Move PDF from temp location to final location based on criteria matching"""
        try:
            filename = f"paper_{apa_number:03d}.pdf"
            
            if matches_criteria:
                final_path = os.path.join(self.download_dir, filename)
            else:
                final_path = os.path.join(self.not_relevant_dir, filename)
            
            # Move file
            shutil.move(temp_path, final_path)
            print(f"  📁 PDF moved to: {final_path}")
            
            return final_path
            
        except Exception as e:
            print(f"  ⚠ Error moving PDF: {str(e)}")
            return None

    def analyze_paper_with_fulltext(self, paper_info: Dict[str, Any], fulltext_url: str) -> Dict[str, Any]:
        """Legacy method - now redirects to new fallback method"""
        return self.analyze_paper_with_fulltext_and_fallback(paper_info, fulltext_url)

    def process_batch_fixed(self, batch_id: int, batch_papers: List[Dict[str, Any]]) -> List[PaperResult]:
        """Process a batch of papers - FIXED VERSION"""
        batch_start_time = time.time()
        batch_results = []
        
        print(f"\n{'='*60}")
        print(f"Processing batch {batch_id} with {len(batch_papers)} papers")
        print(f"{'='*60}")
        
        for idx, paper_info in enumerate(batch_papers, 1):
            paper_start_time = time.time()
            apa_number = paper_info['apa_number']
            
            print(f"\n[Batch {batch_id}, Paper {idx}/{len(batch_papers)}] APA #{apa_number}")
            
            # Process paper
            result = self.process_single_paper_optimized(paper_info)
            batch_results.append(result)
            
            # Mark as processed
            self.processed_papers.add(apa_number)
            
            # Update stats
            processing_time = time.time() - paper_start_time
            self.stats['paper_timings'].append(processing_time)
            
            print(f"  → Completed in {processing_time:.1f}s")
            
            # Rate limiting is handled inside API calls, but add small delay between papers
            if idx < len(batch_papers):
                time.sleep(1)  # Small delay between papers in same batch
        
        # Update batch stats
        batch_time = time.time() - batch_start_time
        self.stats['batch_timings'].append(batch_time)
        self.stats['batches_processed'] += 1  # This will now be correct!
        
        print(f"\n{'='*60}")
        print(f"Batch {batch_id} completed in {batch_time:.1f}s")
        print(f"Average: {batch_time/len(batch_papers) if batch_papers else 0:.1f}s per paper")
        print(f"{'='*60}")
        
        return batch_results

    def process_single_paper_optimized(self, paper_info: Dict[str, Any]) -> PaperResult:
        """Process a single paper with optimizations"""
        apa_number = paper_info['apa_number']
        url = paper_info['url']
        
        result = PaperResult(
            apa_number=apa_number,
            url=url,
            original_reference=paper_info['original_reference']
        )
        
        try:
            # Step 1: Check if URL is direct PDF (fast check, no download)
            pdf_check = self.check_if_pdf_url(url)
            
            if pdf_check['is_pdf']:
                print(f"  ✓ Direct PDF detected")
                # Download PDF
                pdf_path = self.download_pdf_immediately(pdf_check['url'], apa_number)
                if pdf_path:
                    result.download_path = pdf_path
                    result.download_type = 'direct_pdf'
                    self.stats['direct_pdf'] += 1
                    
                    # Analyze PDF (one AI call)
                    analysis = self.analyze_paper_with_fulltext_and_fallback(paper_info, pdf_check['url'], pdf_path)
                    if 'error' not in analysis:
                        result.matches_criteria = analysis.get('MATCHES_CRITERIA', False)
                        result.criteria_explanation = analysis.get('CRITERIA_MATCH_EXPLANATION', '')
                        result.extraction_data = analysis
                        result.status = 'success'
                    else:
                        result.status = 'failed'
                        result.error = analysis.get('error', 'Failed to analyze content')
            else:
                # Step 2: Find full text (one AI call)
                print(f"  → Finding full text...")
                fulltext_result = self.find_fulltext_with_ai(url, attempt=1)
                
                if fulltext_result['status'] == 'found_fulltext':
                    # Process based on what we found
                    local_pdf_path = None
                    if fulltext_result.get('type') == 'direct_pdf':
                        # Download PDF if found
                        local_pdf_path = self.download_pdf_immediately(fulltext_result['url'], apa_number)
                        if local_pdf_path:
                            result.download_path = local_pdf_path
                            result.download_type = 'found_pdf'
                            self.stats['direct_pdf'] += 1
                    
                    # Analyze content (one AI call)
                    analysis = self.analyze_paper_with_fulltext_and_fallback(
                        paper_info,
                        fulltext_result['url'],
                        local_pdf_path
                    )
                    
                    if 'error' not in analysis:
                        result.matches_criteria = analysis.get('MATCHES_CRITERIA', False)
                        result.criteria_explanation = analysis.get('CRITERIA_MATCH_EXPLANATION', '')
                        result.extraction_data = analysis
                        result.status = 'success'
                    else:
                        result.status = 'failed'
                        result.error = analysis.get('error', 'Failed to analyze content')
                else:
                    result.status = 'failed'
                    result.error = fulltext_result.get('error', 'Failed to find full text')
            
            # Move PDF to final location based on criteria
            if result.download_path and os.path.exists(result.download_path):
                final_path = self.move_temp_pdf_to_final_location(
                    result.download_path,
                    apa_number,
                    result.matches_criteria
                )
                if final_path:
                    result.download_path = final_path
            
            # Update stats
            if result.status == 'success':
                if result.matches_criteria:
                    self.stats['papers_matching_criteria'] += 1
                else:
                    self.stats['papers_not_matching_criteria'] += 1
                
        except Exception as e:
            result.status = 'failed'
            result.error = str(e)
            print(f"  ✗ Error: {str(e)}")
            self.stats['processing_errors']['general'] += 1
        
        # Add to results
        with self.results_lock:
            self.results.append(result)
            self.stats['processed'] += 1
        
        return result

    def _write_paper_information(self):
        """Write paper_information.json for matching papers"""
        matching_papers = [r for r in self.results if r.matches_criteria and r.extraction_data]
        
        output_data = {
            'extraction_date': datetime.now().isoformat(),
            'total_papers_analyzed': len(self.results),
            'papers_matching_criteria': len(matching_papers),
            'papers_not_matching_criteria': self.stats['papers_not_matching_criteria'],
            'full_text_found': len([r for r in matching_papers if r.download_type != 'abstract_only']),
            'abstract_only': len([r for r in matching_papers if r.download_type == 'abstract_only']),
            'papers': []
        }
        
        for i, result in enumerate(matching_papers, 1):
            paper_data = result.extraction_data.copy()
            paper_data['paper_id'] = f"PAPER_{i:03d}"
            paper_data['download_info'] = {
                'original_url': result.url,
                'pdf_url': result.pdf_url,
                'download_type': result.download_type,
                'local_path': result.download_path,
                'batch_id': result.batch_id,
                'full_text_analyzed': result.download_type != 'abstract_only'
            }
            output_data['papers'].append(paper_data)
        
        with open(self.paper_info_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

    def _write_non_matching_papers(self):
        """Write non_matching_papers.json"""
        non_matching = [r for r in self.results if not r.matches_criteria and r.extraction_data]
        
        output_data = {
            'extraction_date': datetime.now().isoformat(),
            'total_papers': len(non_matching),
            'papers': []
        }
        
        for i, result in enumerate(non_matching, 1):
            paper_data = {
                'paper_id': f"NON_MATCH_{i:03d}",
                'apa_number': result.apa_number,
                'url': result.url,
                'Title': result.extraction_data.get('Title', 'Unknown'),
                'Authors': result.extraction_data.get('Authors', []),
                'Year': result.extraction_data.get('Year', 'Unknown'),
                'CRITERIA_MATCH_EXPLANATION': result.criteria_explanation,
                'download_path': result.download_path,
                'batch_id': result.batch_id
            }
            output_data['papers'].append(paper_data)
        
        with open(self.non_matching_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

    def _write_references(self):
        """Write paper_references.txt"""
        matching_papers = [r for r in self.results if r.matches_criteria and r.extraction_data]
        
        with open(self.references_file, 'w', encoding='utf-8') as f:
            f.write("APA REFERENCES FROM PAPERS MATCHING CRITERIA\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total matching papers: {len(matching_papers)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, result in enumerate(matching_papers, 1):
                f.write(f"{i}. ")
                
                # Try to get APA reference from extraction
                apa_ref = None
                if 'BIBLIOGRAPHIC_DETAILS' in result.extraction_data:
                    apa_ref = result.extraction_data['BIBLIOGRAPHIC_DETAILS'].get('APA_Reference')
                elif 'BIBLIOGRAPHIC DETAILS' in result.extraction_data:
                    apa_ref = result.extraction_data['BIBLIOGRAPHIC DETAILS'].get('APA_Reference')
                
                if apa_ref:
                    f.write(f"{apa_ref}\n")
                else:
                    # Fall back to original reference
                    f.write(f"{result.original_reference}\n")
                
                f.write(f"   Downloaded from: {result.url}\n")
                f.write(f"   Saved as: {os.path.basename(result.download_path) if result.download_path else 'Not downloaded'}\n")
                f.write(f"   Batch ID: {result.batch_id}\n\n")

    def _write_summaries(self):
        """Write summary files with enhanced details"""
        # Unified summary with enhanced details
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            f.write("UNIFIED PAPER PROCESSING SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("OVERALL STATISTICS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total URLs processed: {self.stats['total_urls']}\n")
            f.write(f"Successfully processed: {self.stats['processed']}\n")
            f.write(f"Papers matching criteria: {self.stats['papers_matching_criteria']}\n")
            f.write(f"Papers not matching: {self.stats['papers_not_matching_criteria']}\n")
            f.write(f"Downloads successful: {self.stats['download_success']}\n")
            f.write(f"Downloads failed: {self.stats['download_failed']}\n\n")
            
            f.write("BATCH PROCESSING:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total batches: {self.stats['batches_processed']}\n")
            f.write(f"Papers per batch: {self.batch_size}\n")
            f.write(f"Average papers per batch: {self.stats['processed']/self.stats['batches_processed'] if self.stats['batches_processed'] > 0 else 0:.1f}\n")
            if self.stats['batch_timings']:
                f.write(f"Average batch processing time: {sum(self.stats['batch_timings'])/len(self.stats['batch_timings']):.1f}s\n")
                f.write(f"Min batch time: {min(self.stats['batch_timings']):.1f}s\n")
                f.write(f"Max batch time: {max(self.stats['batch_timings']):.1f}s\n")
            f.write("\n")
            
            f.write("FULLTEXT SEARCH STATISTICS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total fulltext search attempts: {self.stats['fulltext_search_attempts']}\n")
            f.write(f"Immediate PDF downloads: {self.stats['immediate_pdf_downloads']}\n")
            f.write(f"PDF download failures: {self.stats['pdf_download_failures']}\n")
            f.write(f"Extractions with full text: {self.stats['extraction_with_fulltext']}\n")
            f.write(f"Extractions without full text: {self.stats['extraction_without_fulltext']}\n")
            f.write("\nFulltext found by method:\n")
            for method, count in sorted(self.stats['fulltext_found_method'].items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {method}: {count}\n")
            f.write("\n")
            
            f.write("DOWNLOAD TYPES:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Direct PDFs: {self.stats['direct_pdf']}\n")
            f.write(f"HTML full text: {self.stats['html_fulltext']}\n")
            f.write(f"Open repository: {self.stats['open_repository']}\n\n")
            
            f.write("AI STATISTICS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total AI requests: {self.stats['ai_requests']}\n")
            f.write(f"AI failures: {self.stats['ai_failures']}\n")
            f.write(f"Success rate: {(self.stats['ai_requests']-self.stats['ai_failures'])/self.stats['ai_requests']*100 if self.stats['ai_requests'] > 0 else 0:.1f}%\n")
            f.write(f"Model responses saved: {self.model_response_counter}\n\n")
            
            f.write("PROCESSING PERFORMANCE:\n")
            f.write("-" * 40 + "\n")
            if self.stats['paper_timings']:
                f.write(f"Average time per paper: {sum(self.stats['paper_timings'])/len(self.stats['paper_timings']):.1f}s\n")
                f.write(f"Min paper processing time: {min(self.stats['paper_timings']):.1f}s\n")
                f.write(f"Max paper processing time: {max(self.stats['paper_timings']):.1f}s\n")
            f.write(f"Temporary files cleaned: {self.stats['temp_files_cleaned']}\n\n")
            
            f.write("ISSUES ENCOUNTERED:\n")
            f.write("-" * 40 + "\n")
            f.write(f"404 Not Found: {self.stats['not_found_404']}\n")
            f.write(f"Paywalls detected: {self.stats['paywall_detected']}\n")
            if self.stats['processing_errors']:
                f.write("\nProcessing errors by type:\n")
                for error_type, count in sorted(self.stats['processing_errors'].items(), key=lambda x: x[1], reverse=True):
                    f.write(f"  {error_type}: {count}\n")
            f.write("\n")
            
            f.write("MODEL RESPONSES:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total responses saved: {len(self.model_responses)}\n")
            f.write(f"Response files in: {self.model_dir}/\n")
            
            # Count response types
            response_types = defaultdict(int)
            for resp in self.model_responses:
                response_types[resp['type']] += 1
            
            f.write("\nResponses by type:\n")
            for resp_type, count in sorted(response_types.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {resp_type}: {count}\n")
            f.write("\n")
            
            # Detailed results by category
            f.write("\nDETAILED RESULTS:\n")
            f.write("=" * 80 + "\n\n")
            
            # Matching papers
            matching = [r for r in self.results if r.matches_criteria]
            if matching:
                f.write("PAPERS MATCHING CRITERIA:\n")
                f.write("-" * 40 + "\n")
                for r in matching:
                    f.write(f"#{r.apa_number}: {r.extraction_data.get('Title', 'Unknown')[:60]}...\n")
                    f.write(f"  URL: {r.url}\n")
                    f.write(f"  Type: {r.download_type}\n")
                    f.write(f"  Batch: {r.batch_id}\n")
                    f.write(f"  Saved to: {r.download_path}\n\n")
            
            # Non-matching papers
            non_matching = [r for r in self.results if not r.matches_criteria and r.status in ['analyzed', 'analyzed_partial']]
            if non_matching:
                f.write("\nPAPERS NOT MATCHING CRITERIA:\n")
                f.write("-" * 40 + "\n")
                for r in non_matching[:10]:  # Show first 10
                    f.write(f"#{r.apa_number}: {r.extraction_data.get('Title', 'Unknown')[:60]}...\n")
                    f.write(f"  Reason: {r.criteria_explanation}\n")
                    f.write(f"  Batch: {r.batch_id}\n\n")
                
                if len(non_matching) > 10:
                    f.write(f"\n... and {len(non_matching) - 10} more non-matching papers\n")
            
            # Failed downloads
            failed = [r for r in self.results if r.status == 'failed']
            if failed:
                f.write("\nFAILED DOWNLOADS:\n")
                f.write("-" * 40 + "\n")
                for r in failed[:10]:  # Show first 10
                    f.write(f"#{r.apa_number}: {r.url}\n")
                    f.write(f"  Error: {r.error}\n")
                    f.write(f"  Batch: {r.batch_id}\n\n")
                
                if len(failed) > 10:
                    f.write(f"\n... and {len(failed) - 10} more failed downloads\n")
        
        # Enhanced extraction summary
        with open(self.extraction_summary_file, 'w', encoding='utf-8') as f:
            f.write("PAPER EXTRACTION SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("PROCESSING STATISTICS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total papers found: {self.stats['total_urls']}\n")
            f.write(f"Papers processed: {self.stats['processed']}\n")
            f.write(f"Processing success rate: {self.stats['processed']/self.stats['total_urls']*100 if self.stats['total_urls'] > 0 else 0:.1f}%\n\n")
            
            f.write("CRITERIA MATCHING:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Papers matching criteria: {self.stats['papers_matching_criteria']}\n")
            f.write(f"Papers NOT matching: {self.stats['papers_not_matching_criteria']}\n")
            f.write(f"Total analyzed: {self.stats['papers_matching_criteria'] + self.stats['papers_not_matching_criteria']}\n")
            f.write(f"Match rate: {self.stats['papers_matching_criteria']/(self.stats['papers_matching_criteria'] + self.stats['papers_not_matching_criteria'])*100 if (self.stats['papers_matching_criteria'] + self.stats['papers_not_matching_criteria']) > 0 else 0:.1f}%\n\n")
            
            f.write("FULLTEXT ACCESS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Papers with full text found: {self.stats['extraction_with_fulltext']}\n")
            f.write(f"Papers analyzed without full text: {self.stats['extraction_without_fulltext']}\n")
            f.write(f"Full text success rate: {self.stats['extraction_with_fulltext']/(self.stats['extraction_with_fulltext'] + self.stats['extraction_without_fulltext'])*100 if (self.stats['extraction_with_fulltext'] + self.stats['extraction_without_fulltext']) > 0 else 0:.1f}%\n\n")
            
            f.write("BATCH PROCESSING DETAILS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Batch size: {self.batch_size} papers\n")
            f.write(f"Total batches: {self.stats['batches_processed']}\n")
            f.write(f"API efficiency: {self.stats['processed']/self.stats['ai_requests'] if self.stats['ai_requests'] > 0 else 0:.1f} papers per API call\n\n")
            
            f.write("MODEL INTERACTIONS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total model responses saved: {self.model_response_counter}\n")
            f.write(f"Responses directory: {self.model_dir}/\n")
            f.write(f"Average responses per paper: {self.model_response_counter/self.stats['processed'] if self.stats['processed'] > 0 else 0:.1f}\n\n")
            
            f.write("OUTPUT FILES:\n")
            f.write("-" * 40 + "\n")
            f.write(f"- {self.paper_info_file}: Full extraction for matching papers\n")
            f.write(f"- {self.non_matching_file}: Basic info for non-matching papers\n")
            f.write(f"- {self.references_file}: APA references for matching papers\n")
            f.write(f"- {self.progress_file}: Processing progress (for resuming)\n")
            f.write(f"- {self.model_dir}/: Model responses for all AI interactions\n")
            f.write(f"- {self.download_dir}/: Downloaded papers matching criteria\n")
            f.write(f"- {self.not_relevant_dir}/: Papers not matching criteria\n")

    def _print_summary(self, elapsed_time: float):
        """Print summary to console"""
        print("\n" + "=" * 50)
        print("PROCESSING COMPLETE")
        print("=" * 50)
        print(f"Total time: {elapsed_time/60:.1f} minutes")
        print(f"URLs processed: {self.stats['processed']}/{self.stats['total_urls']}")
        print(f"Batches processed: {self.stats['batches_processed']}")
        print(f"Average time per paper: {elapsed_time/self.stats['processed'] if self.stats['processed'] > 0 else 0:.1f}s")
        
        # Calculate full text statistics
        analyzed_papers = [r for r in self.results if r.status in ['analyzed', 'analyzed_partial']]
        full_text_found = len([r for r in analyzed_papers if r.download_type != 'abstract_only'])
        abstract_only = len([r for r in analyzed_papers if r.download_type == 'abstract_only'])
        
        print(f"\nFull Text Analysis:")
        print(f"  Full text found: {full_text_found}")
        print(f"  Abstract only: {abstract_only}")
        print(f"  Full text rate: {full_text_found/len(analyzed_papers)*100 if analyzed_papers else 0:.1f}%")
        
        print(f"\nCriteria Matching:")
        print(f"  Matching: {self.stats['papers_matching_criteria']}")
        print(f"  Not matching: {self.stats['papers_not_matching_criteria']}")
        print(f"  Match rate: {self.stats['papers_matching_criteria']/(self.stats['papers_matching_criteria'] + self.stats['papers_not_matching_criteria']) * 100 if (self.stats['papers_matching_criteria'] + self.stats['papers_not_matching_criteria']) > 0 else 0:.1f}%")
        
        print(f"\nDownloads:")
        print(f"  Successful: {self.stats['download_success']}")
        print(f"  Failed: {self.stats['download_failed']}")
        print(f"  Direct PDFs: {self.stats['direct_pdf']}")
        print(f"  HTML conversions: {self.stats['html_fulltext']}")
        print(f"\nAI Usage:")
        print(f"  Total requests: {self.stats['ai_requests']}")
        print(f"  Batches: {self.stats['batches_processed']}")
        print(f"  Papers per batch: {self.stats['processed']/self.stats['batches_processed'] if self.stats['batches_processed'] > 0 else 0:.1f}")
        print(f"  Failures: {self.stats['ai_failures']}")
        print("=" * 50)
        print(f"\nOutput files:")
        print(f"  - {self.paper_info_file}")
        print(f"  - {self.non_matching_file}")
        print(f"  - {self.references_file}")
        print(f"  - {self.summary_file}")
        print(f"  - {self.progress_file} (for resuming)")
        print(f"\nDownloaded papers:")
        print(f"  - Matching criteria: {self.download_dir}/")
        print(f"  - Not matching: {self.not_relevant_dir}/")

    def download_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Download with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30, stream=True)
                if response.status_code == 200:
                    return response
                elif response.status_code == 404:
                    self.stats['not_found_404'] += 1
                    return None
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Download failed after {max_retries} attempts: {str(e)}")
        return None

    def verify_extraction_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify and clean extraction output"""
        # Ensure required fields exist
        required_fields = ['MATCHES_CRITERIA', 'CRITERIA_MATCH_EXPLANATION', 'Title', 'Authors', 'Year']
        
        for field in required_fields:
            if field not in data:
                if field == 'MATCHES_CRITERIA':
                    data[field] = False
                elif field == 'Authors':
                    data[field] = []
                else:
                    data[field] = 'Unknown'
        
        return data

    def run(self):
        """Main execution method - FIXED with proper batch processing"""
        start_time = time.time()
        
        # Extract URLs from APA file
        urls = self.extract_urls_from_apa()
        
        if not urls:
            print("No URLs found in APA file")
            return
        
        print(f"Found {len(urls)} URLs to process")
        print(f"Previously processed: {len(self.processed_papers)} papers")
        
        # Filter out already processed papers
        urls_to_process = [u for u in urls if u['apa_number'] not in self.processed_papers]
        print(f"Remaining to process: {len(urls_to_process)} papers")
        
        if not urls_to_process:
            print("All papers already processed!")
            return
        
        # Create batches ONCE at the beginning
        batches = []
        for i in range(0, len(urls_to_process), self.batch_size):
            batch = urls_to_process[i:i + self.batch_size]
            batches.append(batch)
        
        print(f"Created {len(batches)} batches of up to {self.batch_size} papers each")
        print(f"Using {self.max_workers} concurrent workers")
        
        # Process batches
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches at once
            future_to_batch = {
                executor.submit(self.process_batch_fixed, batch_id, batch): (batch_id, batch)
                for batch_id, batch in enumerate(batches, 1)
            }
            
            # Process completed batches
            for future in as_completed(future_to_batch):
                batch_id, batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    print(f"\n✓ Batch {batch_id} completed with {len(batch_results)} papers")
                    
                    # Save progress after each batch
                    self._save_progress()
                    
                except Exception as e:
                    print(f"\n✗ Batch {batch_id} failed: {str(e)}")
                    self.stats['processing_errors']['batch_' + str(batch_id)] = str(e)
        
        # Save final progress
        self._save_progress()
        
        # Write output files
        self._write_paper_information()
        self._write_non_matching_papers()
        self._write_references()
        self._write_summaries()
        
        # Final statistics
        elapsed_time = time.time() - start_time
        self._print_summary(elapsed_time)


if __name__ == "__main__":
    # Initialize with batch processing
    processor = UnifiedPaperProcessor(
        apa_file='urls_combined.txt',
        max_workers=10,  # Maximize concurrency
        batch_size=5  # Process 5 papers per API call
    )
    processor.run()