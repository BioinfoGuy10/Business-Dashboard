"""
Report generation module for Team Work Updates.
Generates CSV and PDF reports based on date ranges.
"""

import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import Counter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def get_date_range_presets(preset: str) -> Tuple[datetime, datetime]:
    """
    Get start and end dates for common presets.
    
    Args:
        preset: One of 'this_week', 'last_week', 'this_month', 'last_month'
        
    Returns:
        Tuple of (start_date, end_date)
    """
    today = datetime.now()
    
    if preset == 'this_week':
        # Monday of current week
        start = today - timedelta(days=today.weekday())
        end = today
    elif preset == 'last_week':
        # Monday to Sunday of last week
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
    elif preset == 'this_month':
        # First day of current month
        start = today.replace(day=1)
        end = today
    elif preset == 'last_month':
        # First day of last month to last day of last month
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
    else:
        raise ValueError(f"Unknown preset: {preset}")
    
    return start, end


def generate_report_data(work_notes: List[Dict]) -> Dict:
    """
    Aggregate work notes data and calculate statistics.
    
    Args:
        work_notes: List of work note dictionaries from database
        
    Returns:
        Dictionary with report data and statistics
    """
    if not work_notes:
        return {
            'total_updates': 0,
            'active_contributors': 0,
            'contributors': [],
            'updates_by_author': {},
            'trending_themes': [],
            'notes': []
        }
    
    # Calculate statistics
    authors = set()
    updates_by_author = Counter()
    all_text = []
    
    for note in work_notes:
        authors.add(note['author_name'])
        updates_by_author[note['author_name']] += 1
        text = note.get('final_accepted_description') or note.get('generated_description') or ''
        all_text.append(text)
    
    # Simple keyword extraction for trending themes
    # Combine all text and find common meaningful words
    combined_text = ' '.join(all_text).lower()
    words = combined_text.split()
    
    # Filter out common words and short words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                  'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                  'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
                  'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your',
                  'his', 'her', 'its', 'our', 'their'}
    
    meaningful_words = [w for w in words if len(w) > 3 and w not in stop_words and w.isalpha()]
    word_freq = Counter(meaningful_words)
    trending_themes = [{'theme': word, 'count': count} for word, count in word_freq.most_common(5)]
    
    return {
        'total_updates': len(work_notes),
        'active_contributors': len(authors),
        'contributors': sorted(list(authors)),
        'updates_by_author': dict(updates_by_author),
        'trending_themes': trending_themes,
        'notes': work_notes
    }


def export_to_csv(report_data: Dict, workspace_name: str, start_date: datetime, end_date: datetime, ai_summary: str = None) -> str:
    """
    Generate CSV content from report data.
    
    Args:
        report_data: Report data dictionary from generate_report_data
        workspace_name: Name of the workspace
        start_date: Report start date
        end_date: Report end date
        ai_summary: Optional AI-generated executive summary
        
    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([f"Team Work Updates Report - {workspace_name}"])
    writer.writerow([f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"])
    writer.writerow([])
    
    # AI Executive Summary
    if ai_summary:
        writer.writerow(["Executive Summary"])
        writer.writerow([ai_summary])
        writer.writerow([])
    
    # Summary statistics
    writer.writerow(["Summary Statistics"])
    writer.writerow(["Total Updates", report_data['total_updates']])
    writer.writerow(["Active Contributors", report_data['active_contributors']])
    writer.writerow([])
    
    # Updates by author
    writer.writerow(["Updates by Author"])
    for author, count in report_data['updates_by_author'].items():
        writer.writerow([author, count])
    writer.writerow([])
    
    # Trending themes
    if report_data['trending_themes']:
        writer.writerow(["Trending Themes"])
        for theme in report_data['trending_themes']:
            writer.writerow([theme['theme'], theme['count']])
        writer.writerow([])
    
    # Detailed updates
    writer.writerow(["Detailed Work Updates"])
    writer.writerow(["Author", "Update", "Date"])
    
    for note in report_data['notes']:
        author = note['author_name']
        update = note.get('final_accepted_description') or note.get('generated_description') or 'No description'
        date = note['created_at']
        writer.writerow([author, update, date])
    
    return output.getvalue()


def export_to_pdf(report_data: Dict, workspace_name: str, start_date: datetime, end_date: datetime, ai_summary: str = None) -> bytes:
    """
    Generate PDF content from report data.
    
    Args:
        report_data: Report data dictionary from generate_report_data
        workspace_name: Name of the workspace
        start_date: Report start date
        end_date: Report end date
        ai_summary: Optional AI-generated executive summary
        
    Returns:
        PDF content as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=10,
        spaceBefore=10
    )
    
    # Title
    title = Paragraph(f"Team Work Updates Report", title_style)
    elements.append(title)
    
    subtitle = Paragraph(f"<b>{workspace_name}</b>", styles['Normal'])
    elements.append(subtitle)
    
    period = Paragraph(
        f"Period: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}",
        styles['Normal']
    )
    elements.append(period)
    elements.append(Spacer(1, 0.3*inch))
    
    # AI Executive Summary Section
    if ai_summary:
        summary_style = ParagraphStyle(
            'SummaryBox',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            leftIndent=10,
            rightIndent=10,
            spaceAfter=15,
            spaceBefore=10,
            borderColor=colors.HexColor('#1f77b4'),
            borderWidth=1,
            borderPadding=10,
            backColor=colors.HexColor('#f0f8ff')
        )
        
        elements.append(Paragraph("Executive Summary", heading_style))
        summary_para = Paragraph(ai_summary, summary_style)
        elements.append(summary_para)
        elements.append(Spacer(1, 0.2*inch))
    
    # Summary Statistics Section
    elements.append(Paragraph("Summary Statistics", heading_style))
    
    stats_data = [
        ['Metric', 'Value'],
        ['Total Updates', str(report_data['total_updates'])],
        ['Active Contributors', str(report_data['active_contributors'])],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Updates by Author
    if report_data['updates_by_author']:
        elements.append(Paragraph("Updates by Author", heading_style))
        
        author_data = [['Author', 'Number of Updates']]
        for author, count in sorted(report_data['updates_by_author'].items()):
            author_data.append([author, str(count)])
        
        author_table = Table(author_data, colWidths=[3*inch, 2*inch])
        author_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(author_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Trending Themes
    if report_data['trending_themes']:
        elements.append(Paragraph("Trending Themes", heading_style))
        
        theme_data = [['Theme', 'Mentions']]
        for theme in report_data['trending_themes']:
            theme_data.append([theme['theme'].capitalize(), str(theme['count'])])
        
        theme_table = Table(theme_data, colWidths=[3*inch, 2*inch])
        theme_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(theme_table)
        elements.append(Spacer(1, 0.3*inch))
    
    # Detailed Updates
    elements.append(Paragraph("Detailed Work Updates", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    for i, note in enumerate(report_data['notes'], 1):
        author = note['author_name']
        update = note.get('final_accepted_description') or note.get('generated_description') or 'No description'
        date = note['created_at']
        
        # Create a mini section for each update
        update_text = f"<b>{i}. {author}</b> - <i>{date}</i><br/>{update}"
        update_para = Paragraph(update_text, styles['Normal'])
        elements.append(update_para)
        elements.append(Spacer(1, 0.15*inch))
    
    # Build PDF
    doc.build(elements)
    
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content
