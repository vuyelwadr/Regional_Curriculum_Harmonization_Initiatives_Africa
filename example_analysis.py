#!/usr/bin/env python3
"""
Example script demonstrating how to work with the Regional Curriculum 
Harmonization Initiatives Africa research database.
"""

import json
from collections import Counter
from datetime import datetime

def load_research_data():
    """Load the main research database."""
    with open('paper_information.json', 'r') as f:
        return json.load(f)

def analyze_research_trends():
    """Analyze trends in the research database."""
    data = load_research_data()
    papers = data['papers']
    
    print("=" * 60)
    print("REGIONAL CURRICULUM HARMONIZATION RESEARCH ANALYSIS")
    print("=" * 60)
    
    # Basic statistics
    print(f"\n📊 BASIC STATISTICS:")
    print(f"   Total papers analyzed: {data['total_papers_analyzed']}")
    print(f"   Papers matching criteria: {data['papers_matching_criteria']}")
    print(f"   Papers with full text: {data['full_text_found']}")
    print(f"   Extraction date: {data['extraction_date']}")
    
    # Year distribution
    years = [p.get('Year', 'Unknown') for p in papers if p.get('Year')]
    year_counts = Counter(years)
    print(f"\n📅 PUBLICATION YEARS (Top 5):")
    for year, count in year_counts.most_common(5):
        print(f"   {year}: {count} papers")
    
    # Geographic focus
    geographic_focus = [p['STUDY_CHARACTERISTICS']['Geographic_Focus'] 
                       for p in papers 
                       if 'STUDY_CHARACTERISTICS' in p and 
                          'Geographic_Focus' in p['STUDY_CHARACTERISTICS']]
    geo_counts = Counter(geographic_focus)
    print(f"\n🌍 GEOGRAPHIC FOCUS (Top 5):")
    for geo, count in geo_counts.most_common(5):
        print(f"   {geo}: {count} papers")
    
    # Regional initiatives
    initiatives = []
    for paper in papers:
        if 'CONTENT_ANALYSIS' in paper and 'Regional_Initiatives' in paper['CONTENT_ANALYSIS']:
            initiatives.extend(paper['CONTENT_ANALYSIS']['Regional_Initiatives'])
    
    initiative_counts = Counter(initiatives)
    print(f"\n🏛️  REGIONAL INITIATIVES (Top 5):")
    for initiative, count in initiative_counts.most_common(5):
        print(f"   {initiative}: {count} mentions")
    
    # Implementation mechanisms
    mechanisms = []
    for paper in papers:
        if 'THEMATIC_CLASSIFICATION' in paper and 'Implementation_Mechanisms' in paper['THEMATIC_CLASSIFICATION']:
            mechanisms.extend(paper['THEMATIC_CLASSIFICATION']['Implementation_Mechanisms'])
    
    mechanism_counts = Counter(mechanisms)
    print(f"\n🔧 IMPLEMENTATION MECHANISMS (Top 5):")
    for mechanism, count in mechanism_counts.most_common(5):
        print(f"   {mechanism}: {count} mentions")
    
    # Challenges and barriers
    challenges = []
    for paper in papers:
        if 'THEMATIC_CLASSIFICATION' in paper and 'Challenges_and_Barriers' in paper['THEMATIC_CLASSIFICATION']:
            challenges.extend(paper['THEMATIC_CLASSIFICATION']['Challenges_and_Barriers'])
    
    challenge_counts = Counter(challenges)
    print(f"\n🚧 COMMON CHALLENGES (Top 5):")
    for challenge, count in challenge_counts.most_common(5):
        print(f"   {challenge}: {count} mentions")

def search_papers_by_keyword(keyword):
    """Search papers by keyword in title or content."""
    data = load_research_data()
    papers = data['papers']
    
    matches = []
    keyword_lower = keyword.lower()
    
    for paper in papers:
        title = paper.get('Title', '').lower()
        content = str(paper).lower()
        
        if keyword_lower in title or keyword_lower in content:
            matches.append({
                'title': paper.get('Title', 'N/A'),
                'authors': paper.get('Authors', []),
                'year': paper.get('Year', 'N/A'),
                'paper_id': paper.get('paper_id', 'N/A')
            })
    
    print(f"\n🔍 SEARCH RESULTS for '{keyword}':")
    print(f"   Found {len(matches)} matching papers:")
    
    for i, match in enumerate(matches[:10], 1):  # Show top 10
        print(f"\n   {i}. {match['title']}")
        print(f"      Authors: {', '.join(match['authors'][:3])}{'...' if len(match['authors']) > 3 else ''}")
        print(f"      Year: {match['year']}")
        print(f"      Paper ID: {match['paper_id']}")

def main():
    """Main function demonstrating various analyses."""
    try:
        print("Loading research database...")
        analyze_research_trends()
        
        print("\n" + "=" * 60)
        search_papers_by_keyword("SADC")
        
        print("\n" + "=" * 60)
        search_papers_by_keyword("quality assurance")
        
        print("\n" + "=" * 60)
        print("✨ Analysis complete! Explore the data further by:")
        print("   - Modifying search keywords")
        print("   - Analyzing specific themes")
        print("   - Examining individual papers in detail")
        print("   - Creating visualizations of trends")
        
    except FileNotFoundError:
        print("Error: paper_information.json not found.")
        print("Please ensure you're in the correct directory.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()