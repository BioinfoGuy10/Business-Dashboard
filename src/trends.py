"""
Trend analysis and aggregation engine for business transcript insights.
Analyzes patterns across multiple transcripts over time.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from collections import Counter
import pandas as pd

# Local imports
sys.path.append(str(Path(__file__).parent.parent))
import config


def load_all_insights() -> List[Dict]:
    """
    Load all insight JSON files from the insights directory.
    
    Returns:
        List of insight dictionaries, sorted by date
    """
    insights = []
    
    for json_file in config.INSIGHTS_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                insights.append(data)
        except Exception as e:
            print(f"⚠️  Could not load {json_file.name}: {e}")
    
    # Sort by date (newest first)
    insights.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return insights


def analyze_topics(insights: List[Dict]) -> Dict:
    """
    Analyze topic frequency across all transcripts.
    
    Args:
        insights: List of insight dictionaries
        
    Returns:
        Dictionary with topic analysis results
    """
    all_topics = []
    
    for insight in insights:
        topics = insight.get('topics', [])
        all_topics.extend(topics)
    
    # Count frequency
    topic_counts = Counter(all_topics)
    
    # Get top topics
    top_topics = topic_counts.most_common(20)
    
    return {
        'total_unique_topics': len(topic_counts),
        'total_mentions': len(all_topics),
        'top_topics': [
            {'topic': topic, 'count': count}
            for topic, count in top_topics
        ],
        'topic_frequency': dict(topic_counts)
    }


def analyze_risks(insights: List[Dict]) -> Dict:
    """
    Analyze risks, including repeated/unresolved risks.
    
    Args:
        insights: List of insight dictionaries
        
    Returns:
        Dictionary with risk analysis results
    """
    all_risks = []
    risk_timeline = []
    
    for insight in insights:
        risks = insight.get('risks', [])
        date = insight.get('date', '')
        filename = insight.get('filename', '')
        
        for risk in risks:
            all_risks.append(risk)
            risk_timeline.append({
                'risk': risk,
                'date': date,
                'filename': filename
            })
    
    # Count frequency
    risk_counts = Counter(all_risks)
    
    # Find repeated risks (appearing 2+ times)
    repeated_risks = [
        {'risk': risk, 'count': count, 'occurrences': [
            r for r in risk_timeline if r['risk'] == risk
        ]}
        for risk, count in risk_counts.items()
        if count >= 2
    ]
    
    # Sort by frequency
    repeated_risks.sort(key=lambda x: x['count'], reverse=True)
    
    return {
        'total_unique_risks': len(risk_counts),
        'total_risk_mentions': len(all_risks),
        'repeated_risks': repeated_risks,
        'top_risks': [
            {'risk': risk, 'count': count}
            for risk, count in risk_counts.most_common(10)
        ]
    }


def analyze_opportunities(insights: List[Dict]) -> Dict:
    """
    Analyze business opportunities mentioned across transcripts.
    
    Args:
        insights: List of insight dictionaries
        
    Returns:
        Dictionary with opportunity analysis
    """
    all_opportunities = []
    
    for insight in insights:
        opportunities = insight.get('opportunities', [])
        all_opportunities.extend(opportunities)
    
    opp_counts = Counter(all_opportunities)
    
    return {
        'total_unique_opportunities': len(opp_counts),
        'total_mentions': len(all_opportunities),
        'top_opportunities': [
            {'opportunity': opp, 'count': count}
            for opp, count in opp_counts.most_common(10)
        ]
    }


def analyze_sentiment_over_time(insights: List[Dict]) -> pd.DataFrame:
    """
    Create time series of sentiment across transcripts.
    
    Args:
        insights: List of insight dictionaries
        
    Returns:
        Pandas DataFrame with date and sentiment columns
    """
    sentiment_data = []
    
    # Sentiment to numeric mapping
    sentiment_map = {
        'positive': 1,
        'neutral': 0,
        'negative': -1
    }
    
    for insight in insights:
        date_str = insight.get('date', '')
        sentiment = insight.get('sentiment', 'neutral')
        filename = insight.get('filename', '')
        
        try:
            # Parse date
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            sentiment_data.append({
                'date': date,
                'sentiment': sentiment,
                'sentiment_score': sentiment_map.get(sentiment, 0),
                'filename': filename
            })
        except ValueError:
            continue
    
    # Create DataFrame
    df = pd.DataFrame(sentiment_data)
    
    if not df.empty:
        df = df.sort_values('date')
    
    return df


def track_action_items(insights: List[Dict]) -> Dict:
    """
    Track action items across transcripts.
    
    Args:
        insights: List of insight dictionaries
        
    Returns:
        Dictionary with action item statistics
    """
    all_action_items = []
    
    for insight in insights:
        action_items = insight.get('action_items', [])
        filename = insight.get('filename', '')
        date = insight.get('date', '')
        
        for item in action_items:
            all_action_items.append({
                'task': item.get('task', ''),
                'owner': item.get('owner', 'Unassigned'),
                'deadline': item.get('deadline', 'No deadline'),
                'status': item.get('status', 'open'),
                'source_file': filename,
                'source_date': date
            })
    
    # Count by status
    open_items = [item for item in all_action_items if item['status'] == 'open']
    closed_items = [item for item in all_action_items if item['status'] == 'closed']
    
    # Owner distribution
    owner_counts = Counter([item['owner'] for item in all_action_items])
    
    return {
        'total_action_items': len(all_action_items),
        'open_items': len(open_items),
        'closed_items': len(closed_items),
        'completion_rate': len(closed_items) / len(all_action_items) * 100 if all_action_items else 0,
        'all_items': all_action_items,
        'open_items_list': open_items,
        'by_owner': dict(owner_counts)
    }


def detect_emerging_themes(insights: List[Dict], threshold: int = 3) -> List[Dict]:
    """
    Detect topics that appear frequently (threshold+ times) across transcripts.
    
    Args:
        insights: List of insight dictionaries
        threshold: Minimum number of appearances to be considered emerging
        
    Returns:
        List of emerging themes with details
    """
    all_topics = []
    topic_timeline = {}
    
    for insight in insights:
        topics = insight.get('topics', [])
        date = insight.get('date', '')
        filename = insight.get('filename', '')
        
        for topic in topics:
            all_topics.append(topic)
            
            if topic not in topic_timeline:
                topic_timeline[topic] = []
            
            topic_timeline[topic].append({
                'date': date,
                'filename': filename
            })
    
    # Find topics appearing threshold+ times
    topic_counts = Counter(all_topics)
    emerging = []
    
    for topic, count in topic_counts.items():
        if count >= threshold:
            emerging.append({
                'theme': topic,
                'count': count,
                'occurrences': topic_timeline[topic]
            })
    
    # Sort by frequency
    emerging.sort(key=lambda x: x['count'], reverse=True)
    
    return emerging


def generate_executive_summary(insights: List[Dict], period: str = "recent") -> str:
    """
    Generate an AI-powered executive summary of insights.
    
    Args:
        insights: List of insight dictionaries
        period: Time period descriptor (e.g., "recent", "weekly", "monthly")
        
    Returns:
        Formatted executive summary string
    """
    if not insights:
        return "No transcripts available for summary."
    
    # Analyze data
    topics = analyze_topics(insights)
    risks = analyze_risks(insights)
    opps = analyze_opportunities(insights)
    actions = track_action_items(insights)
    emerging = detect_emerging_themes(insights, threshold=2)
    
    # Get sentiment distribution
    sentiments = [i.get('sentiment', 'neutral') for i in insights]
    sentiment_dist = Counter(sentiments)
    
    # Build summary
    summary = f"""# Executive Summary ({period.title()})
    
## Overview
- **Total Meetings Analyzed**: {len(insights)}
- **Sentiment Distribution**: {sentiment_dist.get('positive', 0)} positive, {sentiment_dist.get('neutral', 0)} neutral, {sentiment_dist.get('negative', 0)} negative
- **Open Action Items**: {actions['open_items']} / {actions['total_action_items']} ({actions['completion_rate']:.1f}% completion rate)

## Key Themes
"""
    
    # Top topics
    if topics['top_topics']:
        summary += "\n### Most Discussed Topics:\n"
        for item in topics['top_topics'][:5]:
            summary += f"- **{item['topic']}** ({item['count']} mentions)\n"
    
    # Emerging themes
    if emerging:
        summary += "\n### 🔥 Emerging Themes (2+ mentions):\n"
        for theme in emerging[:5]:
            summary += f"- **{theme['theme']}** ({theme['count']} times)\n"
    
    # Critical risks
    if risks['repeated_risks']:
        summary += "\n### ⚠️  Repeated Risks (Requires Attention):\n"
        for risk in risks['repeated_risks'][:3]:
            summary += f"- **{risk['risk']}** (mentioned {risk['count']} times)\n"
    
    # Top opportunities
    if opps['top_opportunities']:
        summary += "\n### 💡 Top Opportunities:\n"
        for opp in opps['top_opportunities'][:3]:
            summary += f"- {opp['opportunity']}\n"
    
    # Action item summary
    if actions['all_items']:
        summary += f"\n### 📋 Action Items:\n"
        summary += f"- {actions['open_items']} open items requiring attention\n"
        if actions['by_owner']:
            top_owners = sorted(actions['by_owner'].items(), key=lambda x: x[1], reverse=True)[:3]
            summary += "- Top owners: " + ", ".join([f"{owner} ({count})" for owner, count in top_owners]) + "\n"
    
    return summary


def get_dashboard_data(insights: List[Dict] = None) -> Dict:
    """
    Get all aggregated data for dashboard display.
    
    Args:
        insights: Optional pre-loaded insights. If None, loads from disk.
        
    Returns:
        Dictionary with all dashboard data
    """
    if insights is None:
        insights = load_all_insights()
    
    return {
        'total_transcripts': len(insights),
        'topics': analyze_topics(insights),
        'risks': analyze_risks(insights),
        'opportunities': analyze_opportunities(insights),
        'sentiment_timeline': analyze_sentiment_over_time(insights),
        'action_items': track_action_items(insights),
        'emerging_themes': detect_emerging_themes(insights, threshold=3),
        'executive_summary': generate_executive_summary(insights)
    }


if __name__ == "__main__":
    # Test the module
    print("🔧 Testing trends module...")
    print(f"✓ Insights directory: {config.INSIGHTS_DIR}")
    
    # Load insights
    insights = load_all_insights()
    print(f"✓ Loaded {len(insights)} insights")
    
    if insights:
        # Test analysis functions
        topics = analyze_topics(insights)
        print(f"✓ Found {topics['total_unique_topics']} unique topics")
        
        risks = analyze_risks(insights)
        print(f"✓ Found {risks['total_unique_risks']} unique risks")
        
        actions = track_action_items(insights)
        print(f"✓ Tracking {actions['total_action_items']} action items")
    
    print("\n✅ Trends module ready!")


def analyze_work_note_themes(notes: List[str]) -> List[Dict]:
    """
    Extract trending keywords/themes from a list of professional work descriptions.
    
    Args:
        notes: List of final accepted work descriptions
        
    Returns:
        List of themes with counts
    """
    if not notes:
        return []
        
    # Combine all text
    all_text = " ".join(notes).lower()
    
    # Simple keyword extraction (words > 3 chars, not common stop words)
    stop_words = {'this', 'that', 'with', 'from', 'have', 'were', 'been', 'started', 'finished', 'fixed', 'implemented', 'working', 'on', 'the', 'and', 'for', 'was', 'were', 'will', 'ould', 'hould', 'these', 'those'}
    
    # Split into words and clean
    import re
    words = re.findall(r'\b[a-z]{4,}\b', all_text)
    
    # Filter stop words
    filtered_words = [w for w in words if w not in stop_words]
    
    # Count frequency
    counts = Counter(filtered_words)
    
    # Get top 5
    top_themes = counts.most_common(5)
    
    return [{'theme': t, 'count': c} for t, c in top_themes]
