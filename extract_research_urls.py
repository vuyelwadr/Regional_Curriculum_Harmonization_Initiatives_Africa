import re
import os
from collections import OrderedDict
from datetime import datetime

def extract_urls_from_text(text):
    """Extract all URLs from text, including those in markdown links and references"""
    urls = []
    
    # Pattern 1: URLs in markdown links [text](url) - More precise pattern
    markdown_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    markdown_matches = re.findall(markdown_pattern, text)
    for text_part, url_part in markdown_matches:
        # Clean the URL part - remove any trailing bracket content
        url_clean = url_part.strip()
        if url_clean.startswith('http'):
            # Remove any trailing ], [ or other markdown artifacts
            url_clean = re.sub(r'[\]\[]+.*$', '', url_clean)
            urls.append(url_clean)
    
    # Pattern 2: Standard URLs (but exclude those already found in markdown)
    # First, temporarily replace markdown URLs to avoid double extraction
    temp_text = text
    for match in re.finditer(markdown_pattern, text):
        temp_text = temp_text.replace(match.group(0), '###MARKDOWN###')
    
    # Now extract standalone URLs
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\])]+[^\s<>"{}|\\^`\[\].,;:)}\]]*'
    standard_urls = re.findall(url_pattern, temp_text)
    
    # Clean and add standard URLs
    for url in standard_urls:
        # Remove any trailing punctuation or markdown artifacts
        url = re.sub(r'[\]\[,;:.)]+$', '', url.strip())
        # Skip if it's a placeholder
        if '###MARKDOWN###' not in url and url.startswith('http'):
            urls.append(url)
    
    # Pattern 3: URLs in reference-style links
    reference_pattern = r'^\[(\d+)\]:\s*(https?://[^\s]+)'
    reference_matches = re.findall(reference_pattern, text, re.MULTILINE)
    for ref_num, url in reference_matches:
        # Clean reference URLs
        url = re.sub(r'[\]\[,;:.)]+$', '', url.strip())
        urls.append(url)
    
    # Clean up all URLs
    cleaned_urls = []
    for url in urls:
        # Remove trailing punctuation and markdown artifacts more aggressively
        url = url.strip()
        
        # Remove common trailing patterns
        url = re.sub(r'[\]\[.,;:)}\'">\s]+$', '', url)
        
        # Remove any remaining ], [ sequences
        url = re.sub(r'[\]\[]+.*$', '', url)
        
        # Handle special case where URL ends with a bracket followed by text
        url = re.split(r'[\]\[]', url)[0]
        
        # Ensure URL is properly formed
        if url and len(url) > 10 and url.startswith('http'):
            # Validate URL structure
            if re.match(r'https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+$', url):
                cleaned_urls.append(url)
    
    return cleaned_urls

def extract_urls_with_context(text):
    """Extract URLs with their surrounding context for better identification"""
    urls_with_context = []
    
    # Find URLs with surrounding text
    lines = text.split('\n')
    for i, line in enumerate(lines):
        urls_in_line = extract_urls_from_text(line)
        for url in urls_in_line:
            context = {
                'url': url,
                'line': line.strip(),
                'line_number': i + 1
            }
            urls_with_context.append(context)
    
    return urls_with_context

def extract_urls_from_file(filepath):
    """Extract all URLs from a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return extract_urls_from_text(content)
    except Exception as e:
        print(f"Error reading {filepath}: {str(e)}")
        return []

def get_section_name(filename):
    """Extract section name from filename"""
    # Remove 'research_' prefix and '.txt' suffix
    name = filename.replace('research_', '').replace('.txt', '')
    return name.capitalize()

def main():
    # Directory containing research files
    research_dir = '/Users/ruwodda/Documents/Personal/tmp/gr2a/paper5/researchCombined'
    
    # Find all research_*.txt files
    research_files = []
    for filename in os.listdir(research_dir):
        if filename.startswith('research_') and filename.endswith('.txt'):
            research_files.append(filename)
    
    # Sort files for consistent ordering
    research_files.sort()
    
    print(f"Found {len(research_files)} research files: {', '.join(research_files)}")
    
    # Dictionary to store URLs by section
    sections_urls = OrderedDict()
    all_unique_urls = set()
    url_counts = {}  # Track which sections each URL appears in
    
    # Extract URLs from each file
    for filename in research_files:
        filepath = os.path.join(research_dir, filename)
        section_name = get_section_name(filename)
        
        print(f"\nProcessing {filename}...")
        urls = extract_urls_from_file(filepath)
        
        # Remove duplicates within each section while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            # Additional validation - ensure URL doesn't contain markdown artifacts
            if url not in seen and '], [' not in url and not url.endswith(']'):
                seen.add(url)
                unique_urls.append(url)
                # Track which sections contain this URL
                if url not in url_counts:
                    url_counts[url] = []
                url_counts[url].append(section_name)
        
        sections_urls[section_name] = unique_urls
        all_unique_urls.update(unique_urls)
        
        print(f"  Found {len(urls)} URLs ({len(unique_urls)} unique)")
    
    # Write sectioned URLs file
    sectioned_file = os.path.join(research_dir, 'urls.txt')
    with open(sectioned_file, 'w', encoding='utf-8') as f:
        f.write("# Research URLs by Section\n")
        f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for section, urls in sections_urls.items():
            f.write(f"## {section}\n\n")
            for i, url in enumerate(urls, 1):
                f.write(f"{i}. {url}\n")
            f.write(f"\nTotal: {len(urls)} URLs\n\n")
    
    print(f"\nWrote sectioned URLs to: {sectioned_file}")
    
    # Write combined unique URLs file with additional validation
    combined_file = os.path.join(research_dir, 'urls_combined.txt')
    # Sort URLs for consistent ordering and validate
    validated_urls = []
    for url in all_unique_urls:
        # Final validation check
        if (url.startswith('http') and 
            '], [' not in url and 
            not url.endswith(']') and
            not url.endswith('[') and
            re.match(r'https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+$', url)):
            validated_urls.append(url)
        else:
            print(f"Filtered out invalid URL: {url}")
    
    sorted_unique_urls = sorted(validated_urls)
    
    with open(combined_file, 'w', encoding='utf-8') as f:
        f.write("# All Unique Research URLs Combined\n")
        f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total unique URLs: {len(sorted_unique_urls)}\n\n")
        
        for i, url in enumerate(sorted_unique_urls, 1):
            f.write(f"{i}. {url}\n")
    
    print(f"Wrote combined unique URLs to: {combined_file}")
    print(f"\nTotal unique URLs found: {len(sorted_unique_urls)}")
    
    # Print summary
    print("\nSummary by section:")
    total_urls = 0
    for section, urls in sections_urls.items():
        print(f"  {section}: {len(urls)} URLs")
        total_urls += len(urls)
    print(f"\nTotal URLs (with duplicates): {total_urls}")
    print(f"Total unique URLs: {len(sorted_unique_urls)}")
    
    # Find URLs that appear in multiple sections
    multi_section_urls = {url: sections for url, sections in url_counts.items() if len(sections) > 1}
    if multi_section_urls:
        print(f"\nURLs appearing in multiple sections: {len(multi_section_urls)}")
        # Show first 5 as examples
        for i, (url, sections) in enumerate(list(multi_section_urls.items())[:5]):
            print(f"  {url[:80]}{'...' if len(url) > 80 else ''}")
            print(f"    Appears in: {', '.join(sections)}")
            if i >= 4:
                print(f"  ... and {len(multi_section_urls) - 5} more")
                break
    
    # Write comprehensive summary file
    summary_file = os.path.join(research_dir, 'summary_extract_research_urls.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("URL EXTRACTION SUMMARY REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Files processed
        f.write("FILES PROCESSED:\n")
        f.write("-" * 40 + "\n")
        for filename in research_files:
            f.write(f"  - {filename}\n")
        f.write(f"\nTotal files: {len(research_files)}\n\n")
        
        # Overall statistics
        f.write("OVERALL STATISTICS:\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total URLs found (with duplicates): {total_urls}\n")
        f.write(f"Total unique URLs: {len(sorted_unique_urls)}\n")
        f.write(f"URLs appearing in multiple sections: {len(multi_section_urls)}\n\n")
        
        # Per-section statistics
        f.write("PER-SECTION STATISTICS:\n")
        f.write("-" * 40 + "\n")
        for section, urls in sections_urls.items():
            f.write(f"{section}:\n")
            f.write(f"  - Total URLs: {len(urls)}\n")
            f.write(f"  - File: research_{section.lower()}.txt\n\n")
        
        # Domain analysis
        f.write("DOMAIN ANALYSIS:\n")
        f.write("-" * 40 + "\n")
        domain_counts = {}
        for url in sorted_unique_urls:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                domain = domain.replace('www.', '')
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            except:
                pass
        
        # Sort domains by count
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        f.write(f"Total unique domains: {len(sorted_domains)}\n\n")
        f.write("All domains by URL count:\n")
        for domain, count in sorted_domains:
            f.write(f"  {domain}: {count} URLs\n")
        
        # URLs appearing in multiple sections
        f.write("\n\nURLs APPEARING IN MULTIPLE SECTIONS:\n")
        f.write("-" * 40 + "\n")
        if multi_section_urls:
            f.write(f"Total: {len(multi_section_urls)} URLs\n\n")
            for i, (url, sections) in enumerate(sorted(multi_section_urls.items(), 
                                                      key=lambda x: len(x[1]), reverse=True)):
                f.write(f"{i+1}. {url}\n")
                f.write(f"   Appears in: {', '.join(sorted(sections))}\n\n")
        else:
            f.write("No URLs appear in multiple sections.\n")
        
        # URL patterns analysis
        f.write("\nURL PATTERNS ANALYSIS:\n")
        f.write("-" * 40 + "\n")
        pdf_urls = [url for url in sorted_unique_urls if '.pdf' in url.lower()]
        article_urls = [url for url in sorted_unique_urls if '/article/' in url or '/articles/' in url]
        doi_urls = [url for url in sorted_unique_urls if 'doi.org' in url or '/doi/' in url]
        
        f.write(f"PDF URLs: {len(pdf_urls)}\n")
        f.write(f"Article URLs: {len(article_urls)}\n")
        f.write(f"DOI URLs: {len(doi_urls)}\n")
        
        # Output files created
        f.write("\n\nOUTPUT FILES CREATED:\n")
        f.write("-" * 40 + "\n")
        f.write(f"1. {sectioned_file}\n")
        f.write(f"   - Contains all URLs organized by section\n")
        f.write(f"2. {combined_file}\n")
        f.write(f"   - Contains all unique URLs combined and numbered\n")
        f.write(f"3. {summary_file}\n")
        f.write(f"   - This comprehensive summary report\n")
    
    print(f"\nWrote comprehensive summary to: {summary_file}")

if __name__ == "__main__":
    main()
