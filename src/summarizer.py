import datetime
from . import db

def generate_weekly_summary_text(workspace_id, start_date, end_date):
    """
    Generates a markdown summary of the week's activity.
    In a real app, this would call an LLM. Here, we simulate it.
    """
    # Bytes to strings if needed (depending on how dates are passed)
    # Assuming start_date and end_date are definition objects or strings
    
    # 1. Fetch Data
    posts = db.get_workspace_posts(workspace_id)
    # Filter by date range (naive simulation, ideally DB filter)
    # converting format YYYY-MM-DD to check
    
    week_posts = []
    # Simple check - assuming timestamp is YYYY-MM-DD HH:MM:SS
    s_date = str(start_date)
    e_date = str(end_date)
    
    for p in posts:
        # p['timestamp'] is a string
        if s_date <= p['timestamp'][:10] <= e_date:
            week_posts.append(p)
            
    # Mocking Work Notes fetch (assuming logic exists or we add it)
    # For MVP, let's focus on posts
    
    if not week_posts:
        return "No activity found for this week."

    # 2. Analyze Data (Heuristic/deterministic for MVP)
    praise_count = sum(1 for p in week_posts if p['type'] == 'praise')
    credit_count = sum(1 for p in week_posts if p['type'] == 'credit')
    update_count = sum(1 for p in week_posts if p['type'] == 'update')
    
    highlights = []
    for p in week_posts:
        if p['type'] in ['praise', 'credit']:
            highlights.append(f"- {p['content']}")
            
    updates = []
    for p in week_posts:
        if p['type'] == 'update':
            updates.append(f"- {p['content']}")

    # 3. Formulate Summary
    summary = f"""
### 📅 Weekly Roundup ({s_date} to {e_date})

**🏆 Wins & Shoutouts**
{chr(10).join(highlights) if highlights else "No specific shoutouts this week."}

**📌 Key Updates**
{chr(10).join(updates) if updates else "No major updates recorded."}

**📊 Activity Stats**
- Praises: {praise_count}
- Credits: {credit_count}
- Updates: {update_count}

*Generated automatically by Team Workspace AI*
    """
    
    return summary.strip()


def generate_team_work_summary(work_notes: list, start_date, end_date) -> str:
    """
    Generate an AI-powered executive summary of team work updates.
    
    Args:
        work_notes: List of work note dictionaries
        start_date: Start date of the period
        end_date: End date of the period
        
    Returns:
        Executive summary as markdown text
    """
    if not work_notes:
        return "No work updates were recorded during this period."
    
    try:
        # Import config for API settings
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        import config
        from openai import OpenAI
        
        # Prepare the work updates for analysis
        updates_text = []
        for note in work_notes:
            author = note.get('author_name', 'Unknown')
            update = note.get('final_accepted_description') or note.get('generated_description', '')
            if update:
                updates_text.append(f"- {author}: {update}")
        
        combined_updates = "\n".join(updates_text)
        
        prompt = f"""You are analyzing team work updates for the period {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}.

Here are all the work updates from team members:

{combined_updates}

Please provide a concise executive summary (3-4 sentences) that:
1. Highlights the main areas of work and key accomplishments
2. Identifies any common themes or focus areas
3. Notes the overall progress and team productivity

Keep it professional and actionable. Focus on what was achieved, not who did what."""

        # Use the same client configuration as the rest of the app
        client_kwargs = {"api_key": config.OPENAI_API_KEY}
        if config.OPENAI_BASE_URL:
            client_kwargs["base_url"] = config.OPENAI_BASE_URL
        
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional team manager creating executive summaries of team work."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        return f"Unable to generate AI summary: {str(e)}"
