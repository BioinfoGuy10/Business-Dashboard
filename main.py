"""
Business Transcript Analyzer - Main Streamlit Application
Multi-page app for uploading, analyzing, and visualizing business transcript insights.
"""

import streamlit as st
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import time

# Add src to path
sys.path.append(str(Path(__file__).parent))

# Import local modules
from src import ingestion, analysis, embedding_store, trends, intelligence, db
import config

# Page configuration
st.set_page_config(
    page_title="Business Transcript Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .kpi-number {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .kpi-label {
        font-size: 1rem;
        margin-top: 0.5rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'active_workspace' not in st.session_state:
        st.session_state.active_workspace = None
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = []
    if 'dashboard_data' not in st.session_state:
        st.session_state.dashboard_data = None
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    if 'company_info' not in st.session_state:
        st.session_state.company_info = intelligence.get_company_intelligence()

def login_register():
    """Login and Registration UI."""
    st.markdown('<p class="main-header">🔐 Collaborative Analytics Login</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                user = db.get_user_by_email(email)
                if user and db.check_password(password, user['password_hash']):
                    st.session_state.user = dict(user)
                    st.success("Successfully logged in!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
    
    with tab2:
        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Register")
            if submitted:
                if name and email and password:
                    if db.create_user(name, email, password):
                        st.success("✅ Account created! Please log in to start collaborating.")
                    else:
                        st.error("❌ Email already registered. Try logging in.")
                else:
                    st.warning("⚠️ Please fill in all fields.")

def page_workspace():
    """Team Workspace page."""
    st.markdown('<p class="main-header">👥 Team Workspace</p>', unsafe_allow_html=True)
    
    if not st.session_state.active_workspace:
        st.info("You are not currently in a workspace. Create one or join using an invite code.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Create Workspace")
            with st.form("create_workspace_form"):
                ws_name = st.text_input("Workspace Name")
                submitted = st.form_submit_button("Create")
                if submitted:
                    if ws_name:
                        ws_id = db.create_workspace(ws_name, st.session_state.user['id'])
                        if ws_id:
                            st.success(f"🚀 Workspace '{ws_name}' created successfully!")
                            # Refresh workspaces
                            workspaces = db.get_user_workspaces(st.session_state.user['id'])
                            st.session_state.active_workspace = dict(workspaces[0])
                            st.rerun()
                    else:
                        st.warning("⚠️ Please enter a workspace name.")
        
        with col2:
            st.subheader("Join Workspace")
            with st.form("join_workspace_form"):
                invite_code = st.text_input("Invite Code").upper()
                submitted = st.form_submit_button("Join")
                if submitted:
                    if invite_code:
                        success, message = db.join_workspace_by_invite(st.session_state.user['id'], invite_code)
                        if success:
                            st.success(f"✨ {message}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.warning("⚠️ Please enter an invite code.")
    else:
        ws = st.session_state.active_workspace
        st.subheader(f"Workspace: {ws['name']}")
        
        tabs = st.tabs(["Feed", "My Work Notes", "Team Work Updates", "Members", "Settings"])
        
        with tabs[0]:
            # My Stats Section
            st.subheader("📊 My Stats")
            stats = db.get_user_stats(st.session_state.user['id'], ws['id'])
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Praises Received", stats['praise_count'])
            with col2:
                st.metric("Credits Received", stats['credit_count'])
            with col3:
                st.write("**Recent Mentions:**")
                if stats['recent_mentions']:
                    for m in stats['recent_mentions']:
                        st.caption(f"From {m['author_name']}: {m['content'][:30]}...")
                else:
                    st.caption("No recent mentions yet.")
            
            st.markdown("---")
            st.subheader("Share an Update")
            st.subheader("Share an Update")
            
            # Using columns to organize inputs
            post_type = st.selectbox("Type", ["Praise", "Credit", "Update"])
            
            target_user_id = None
            if post_type in ["Praise", "Credit"]:
                members = db.get_workspace_members(ws['id'])
                member_options = {m['name']: m['id'] for m in members if m['id'] != st.session_state.user['id']}
                if member_options:
                    tagged_name = st.selectbox("Tag Teammate (Optional)", ["None"] + list(member_options.keys()))
                    if tagged_name != "None":
                        target_user_id = member_options[tagged_name]
            
            if 'post_content' not in st.session_state:
                st.session_state.post_content = ""

            def add_emoji(e):
                st.session_state.post_content += f" {e}"

            content = st.text_area("What's on your mind?", key="post_content")

            # Emoji Insertion
            st.write("**Add Emojis:**")
            mood_emojis = ["👍", "🎉", "🏅", "📢", "🔥", "🚀", "💡", "❤️", "😂", "👀"]
            emoji_cols = st.columns(len(mood_emojis))
            for i, emoji in enumerate(mood_emojis):
                emoji_cols[i].button(emoji, key=f"add_{emoji}", on_click=add_emoji, args=(emoji,))

            def submit_post(ws_id, user_id, type_val, target_uid):
                content_val = st.session_state.post_content
                if content_val:
                    success = db.create_post(ws_id, user_id, type_val, content_val, target_uid)
                    if success:
                        st.session_state.post_success = True
                        st.session_state.post_content = "" # Clear after post
                    else:
                        st.session_state.post_error = "Failed to create post."
                else:
                    st.session_state.post_error = "Please enter some content."

            if st.button("Post", type="primary", on_click=submit_post, args=(ws['id'], st.session_state.user['id'], post_type.lower(), target_user_id)):
                # Handle UI feedback after rerun
                if st.session_state.get('post_success'):
                    st.success("Post shared!")
                    st.session_state.post_success = False # Reset
                if st.session_state.get('post_error'):
                    st.warning(st.session_state.post_error)
                    st.session_state.post_error = None # Reset
            
            st.markdown("---")
            st.subheader("📣 Feed")
            
            # Filters
            filter_opt = st.radio(
                "Filter Feed:",
                ["All", "Praise only", "Credits only", "Updates only", "Mentions of me"],
                horizontal=True
            )
            
            posts = db.get_workspace_posts(ws['id'])
            
            # Apply filters
            if filter_opt == "Praise only":
                posts = [p for p in posts if p['type'] == 'praise']
            elif filter_opt == "Credits only":
                posts = [p for p in posts if p['type'] == 'credit']
            elif filter_opt == "Updates only":
                posts = [p for p in posts if p['type'] == 'update']
            elif filter_opt == "Mentions of me":
                posts = [p for p in posts if p['target_user_id'] == st.session_state.user['id']]

            if posts:
                for p in posts:
                    # Determine emoji and styling
                    if p['custom_emoji']:
                        emoji = p['custom_emoji']
                    else:
                        emoji = "🎉" if p['type'] == 'praise' else "🏅" if p['type'] == 'credit' else "📢"
                    
                    # Highlight if mentioning current user
                    is_mention = p['target_user_id'] == st.session_state.user['id']
                    
                    with st.container():
                        if is_mention:
                            st.markdown(f"""
                            <div style="background-color: #fff3cd; border-left: 5px solid #ffca2c; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                                <p style="margin: 0;">{emoji} <b>{p['author_name']}</b> posted a <b>{p['type'].capitalize()}</b> for you!</p>
                                <p style="margin: 5px 0;">{p['content']}</p>
                                <small style="color: #666;">{p['timestamp']}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"**{emoji} {p['author_name']}** shared an **{p['type'].capitalize()}**")
                            if p['target_name']:
                                st.markdown(f"🎯 *Tagged: {p['target_name']}*")
                            st.write(p['content'])
                            st.caption(f"{p['timestamp']}")
                        
                        # Reactions - REMOVED per user request
                        st.markdown("---")
            else:
                st.info("No posts yet. Be the first to share something!")
            
        with tabs[1]:
            st.subheader("📝 My Work Notes")
            st.write("Draft professional work updates from your rough notes. These are private until published.")
            
            # New Note Form
            with st.form("new_work_note_form", clear_on_submit=True):
                raw_notes = st.text_area("Rough Project Notes", placeholder="e.g., finished the auth module, fixed 3 bugs in login, started work on workspaces schema...")
                col1, col2 = st.columns(2)
                with col1:
                    save_draft = st.form_submit_button("💾 Save as Draft")
                with col2:
                    gen_desc = st.form_submit_button("🪄 Generate Description")
                
                if save_draft or gen_desc:
                    if raw_notes:
                        note_id = db.create_work_note(ws['id'], st.session_state.user['id'], raw_notes)
                        if note_id:
                            if gen_desc:
                                with st.spinner("Synthesizing professional update..."):
                                    suggestion = analysis.synthesize_work_update(raw_notes)
                                    db.update_work_note(note_id, generated_description=suggestion)
                                st.success("✨ AI Suggestion generated!")
                            else:
                                st.success("💾 Draft saved!")
                            st.rerun()
                    else:
                        st.warning("⚠️ Please enter some notes first.")
            
            st.markdown("---")
            st.subheader("Your Drafts")
            user_notes = db.get_user_work_notes(st.session_state.user['id'], ws['id'])
            drafts = [n for n in user_notes if n['status'] == 'draft']
            
            if drafts:
                for n in drafts:
                    with st.expander(f"Draft from {n['created_at']}", expanded=False):
                        st.write("**Rough Notes:**")
                        st.write(n['raw_note_text'])
                        
                        st.markdown("---")
                        st.write("**Professional Description:**")
                        # Show current suggestion or allowed edit
                        desc_to_edit = n['final_accepted_description'] or n['generated_description'] or ""
                        new_desc = st.text_area("Edit Update", value=desc_to_edit, key=f"edit_area_{n['id']}", help="This is what the team will see.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🚀 Accept & Publish", key=f"pub_{n['id']}", type="primary"):
                                db.update_work_note(n['id'], final_accepted_description=new_desc, status='published')
                                st.success("Published to Team Work Updates!")
                                time.sleep(1)
                                st.rerun()
                        with col2:
                            if st.button("💾 Save Changes", key=f"save_edit_{n['id']}"):
                                db.update_work_note(n['id'], final_accepted_description=new_desc)
                                st.success("Changes saved to draft.")
                                st.rerun()
            else:
                st.info("You don't have any drafts yet.")

        with tabs[2]:
            st.subheader("🚀 Team Work Updates")
            st.write("Professional updates shared by the team.")
            
            published_notes = db.get_workspace_published_notes(ws['id'])
            
            if published_notes:
                # Trending Themes (Step 8)
                st.markdown("#### 🔥 Trending work themes this week")
                notes_text = [n['final_accepted_description'] or n['generated_description'] or "" for n in published_notes]
                trending = trends.analyze_work_note_themes(notes_text)
                if trending:
                    cols = st.columns(len(trending))
                    for idx, t in enumerate(trending):
                        cols[idx].markdown(f"**{t['theme'].upper()}**\n\n{t['count']} mentions")
                else:
                    st.info("Not enough data for trending themes yet.")
                
                st.markdown("---")
                
                # Dashboard Controls
                st.markdown("#### 🔍 Filter & Search")
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    author_filter = st.selectbox("Filter by Author", ["All"] + sorted(list(set(n['author_name'] for n in published_notes))))
                with col2:
                    search_query = st.text_input("🔍 Search Keyword", placeholder="e.g., auth, bug...")
                with col3:
                    my_posts_only = st.toggle("Only Mine", value=False)
                
                # Apply Filters
                filtered_display_notes = published_notes
                if author_filter != "All":
                    filtered_display_notes = [n for n in filtered_display_notes if n['author_name'] == author_filter]
                if search_query:
                    search_query = search_query.lower()
                    filtered_display_notes = [n for n in filtered_display_notes if search_query in (n['final_accepted_description'] or "").lower() or search_query in (n['generated_description'] or "").lower()]
                if my_posts_only:
                    filtered_display_notes = [n for n in filtered_display_notes if n['author_id'] == st.session_state.user['id']]

                st.markdown("---")
                
                if filtered_display_notes:
                    for n in filtered_display_notes:
                        with st.container():
                            st.markdown(f"### 👤 {n['author_name']}")
                            display_text = n['final_accepted_description'] or n['generated_description'] or "No description available."
                            st.write(display_text)
                            st.caption(f"Shared on {n['created_at']}")
                            st.markdown("---")
                else:
                    st.info("No updates match your filters.")
            else:
                st.info("No work updates have been published to the team yet.")
            
        with tabs[3]:
            st.write("### Members")
            members = db.get_workspace_members(ws['id'])
            for m in members:
                role_icon = "👑" if m['role'] == 'admin' else "👤"
                st.write(f"{role_icon} **{m['name']}** ({m['email']}) - {m['role'].capitalize()}")
                
        with tabs[4]:
            st.write("### Settings")
            if ws['admin_id'] == st.session_state.user['id']:
                st.write("#### Invitations")
                if st.button("Generate New Invite Code"):
                    code = db.generate_invite_code(ws['id'])
                    if code:
                        st.success(f"Generated Code: **{code}**")
                
                invites = db.get_workspace_invites(ws['id'])
                if invites:
                    st.write("Active Invite Codes:")
                    for inv in invites:
                        st.code(inv['invite_code'])
                else:
                    st.info("No active invite codes.")
            else:
                st.info("Only admins can manage settings and invitations.")


def page_upload():
    """Upload & Process page."""
    st.markdown('<p class="main-header">📤 Upload & Process Transcripts</p>', unsafe_allow_html=True)
    
    st.write("""
    Upload business meeting transcripts in **TXT**, **PDF**, or **DOCX** format.  
    The system will automatically extract insights using AI.
    """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a transcript file",
        type=['txt', 'pdf', 'docx'],
        help=f"Maximum file size: {config.MAX_FILE_SIZE_MB}MB"
    )
    
    if uploaded_file is not None:
        st.info(f"📄 Selected: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            process_button = st.button("🚀 Process File", type="primary", use_container_width=True)
        
        if process_button:
            # Progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Ingestion
                status_text.text("📥 Step 1/3: Extracting text from file...")
                progress_bar.progress(10)
                
                result = ingestion.process_upload(uploaded_file)
                
                if not result['success']:
                    st.markdown(f'<div class="error-box">❌ {result["message"]}<br/>{result.get("error", "")}</div>', unsafe_allow_html=True)
                    if result.get('is_duplicate'):
                        st.info("💡 This file has already been processed. Check the Dashboard to view existing insights.")
                    return
                
                progress_bar.progress(33)
                
                # Step 2: LLM Analysis
                status_text.text("🤖 Step 2/3: Extracting insights with AI...")
                progress_bar.progress(40)
                
                extracted_text = result['data']['text']
                metadata = result['data']['metadata']
                
                insights = analysis.extract_insights(extracted_text, metadata)
                
                if insights.get('error'):
                    st.warning(f"⚠️ Partial extraction: {insights['error']}")
                
                progress_bar.progress(66)
                
                # Step 3: Embedding Storage
                status_text.text("🔍 Step 3/3: Building search index...")
                progress_bar.progress(70)
                
                embedding_store.add_document(extracted_text, metadata)
                
                progress_bar.progress(100)
                status_text.text("✅ Processing complete!")
                
                # Success message
                st.markdown(f'''
                <div class="success-box">
                    <h3>✅ Successfully processed: {uploaded_file.name}</h3>
                    <ul>
                        <li><strong>Topics Found:</strong> {len(insights.get("topics", []))}</li>
                        <li><strong>Risks Identified:</strong> {len(insights.get("risks", []))}</li>
                        <li><strong>Opportunities:</strong> {len(insights.get("opportunities", []))}</li>
                        <li><strong>Action Items:</strong> {len(insights.get("action_items", []))}</li>
                        <li><strong>Sentiment:</strong> {insights.get("sentiment", "neutral").title()}</li>
                    </ul>
                </div>
                ''', unsafe_allow_html=True)
                
                # Show extracted insights
                with st.expander("📊 View Extracted Insights"):
                    st.json(insights)
                
                # Update state
                st.session_state.processed_files.append(uploaded_file.name)
                st.session_state.dashboard_data = None  # Force refresh
                
                st.success("🎉 Ready to view in Dashboard!")
                
            except Exception as e:
                st.markdown(f'<div class="error-box">❌ Error: {str(e)}</div>', unsafe_allow_html=True)
                st.exception(e)
    
    # Show previously uploaded files
    st.markdown("---")
    st.subheader("📚 Uploaded Transcripts")
    
    transcripts = ingestion.get_all_transcripts()
    
    if transcripts:
        df = pd.DataFrame(transcripts)
        st.dataframe(
            df[['filename', 'file_type', 'file_size_mb', 'modified_date']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transcripts uploaded yet. Upload your first file above!")


def page_setup():
    """One-time company setup page."""
    st.markdown('<p class="main-header">🏢 Company Intelligence Setup</p>', unsafe_allow_html=True)
    
    st.write("""
    Set up your company profile to get automated business intelligence and trends.
    This is a one-time process where the AI will analyze public news and posts to create a strategic baseline.
    """)
    
    with st.form("company_setup_form"):
        company_name = st.text_input("Company Name", placeholder="e.g. NVIDIA, Tesla, Microsoft")
        linkedin_url = st.text_input("LinkedIn Page URL", placeholder="https://www.linkedin.com/company/...")
        
        submit_button = st.form_submit_button("🚀 Initialize Intelligence", use_container_width=True)
        
    if submit_button:
        if not company_name:
            st.error("Please enter a company name.")
            return
            
        with st.spinner(f"🔍 Analyzing {company_name}... This may take a minute."):
            try:
                intelligence_data = intelligence.process_company_setup(company_name, linkedin_url)
                st.session_state.company_info = intelligence_data
                st.success(f"✅ Intelligence baseline established for {company_name}!")
                
                # Show summary
                st.info(intelligence_data.get('strategic_summary', ""))
                
                if st.button("Go to Dashboard"):
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error during setup: {str(e)}")
                st.exception(e)


def page_dashboard():
    """Dashboard page with visualizations."""
    st.markdown('<p class="main-header">📊 Analytics Dashboard</p>', unsafe_allow_html=True)
    
    # Load or use cached dashboard data
    if st.session_state.dashboard_data is None:
        with st.spinner("Loading dashboard data..."):
            all_insights = trends.load_all_insights()
            if not all_insights and not st.session_state.company_info:
                st.warning("⚠️ No transcripts analyzed and no company setup. Please go to Setup or Upload page.")
                return
            st.session_state.dashboard_data = trends.get_dashboard_data(all_insights) if all_insights else None
    
    data = st.session_state.dashboard_data
    
    # Refresh buttons
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh Data", help="Reload transcript analytics"):
            st.session_state.dashboard_data = None
            st.rerun()
    
    # Company Intelligence Section
    if st.session_state.company_info:
        info = st.session_state.company_info
        
        st.markdown("---")
        col_title, col_btn = st.columns([3, 1])
        with col_title:
            st.markdown(f"## 🏢 {info['company_name']} - Intelligence Center")
        with col_btn:
            if st.button("🗞️ Update Baseline & News", help="Fetch latest company news and rebuild profile", use_container_width=True):
                with st.spinner(f"Updating data for {info['company_name']}..."):
                    try:
                        new_info = intelligence.process_company_setup(info['company_name'], info.get('linkedin_url'))
                        st.session_state.company_info = new_info
                        st.success("Strategic profile and news updated!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")

        # Strategic Summary Card
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 25px;">
            <h3 style="margin-top: 0; color: #1f77b4;">📝 Strategic Summary</h3>
            <p style="font-size: 1.1rem; line-height: 1.6;">{info.get('strategic_summary', "No summary available.")}</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Business Trends as Cards
            st.subheader("📊 Primary Business Trends")
            trends_cols = st.columns(2)
            for i, trend in enumerate(info.get('business_trends', [])):
                with trends_cols[i % 2]:
                    st.markdown(f"""
                    <div style="background-color: white; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 10px; height: 100px; display: flex; align-items: center;">
                        <span>🔹 {trend}</span>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📅 Strategic Timeline & Key Decisions")
            timeline = info.get('timeline', [])
            if timeline:
                for item in timeline:
                    with st.expander(f"📌 {item['date']} - {item['event'][:60]}..."):
                        st.write(item['event'])
                        if item.get('link') and item['link'].startswith("http"):
                            st.link_button("🌐 Read News Source", item['link'], use_container_width=True)
                        elif item.get('link'):
                            st.caption(f"Source Context: {item['link']}")
            else:
                st.write("No timeline events found.")
        
        with col2:
            st.subheader("🎯 Decision Patterns")
            for trend in info.get('decision_trends', []):
                st.success(f"📍 **Pattern:** {trend}")
            
        st.markdown("---")
        st.caption(f"Last Intelligence Update: {info.get('last_updated', 'Never')}")
                
        st.markdown("---")

    if data is None:
        st.info("No transcript insights available yet. Upload transcripts to see analytics.")
        return
    
    # KPI Cards
    st.subheader("📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Transcripts",
            value=data['total_transcripts'],
            delta=None
        )
    
    with col2:
        sent_df = data['sentiment_timeline']
        if not sent_df.empty:
            avg_sentiment = sent_df['sentiment_score'].mean()
            sentiment_label = "Positive" if avg_sentiment > 0.3 else "Negative" if avg_sentiment < -0.3 else "Neutral"
        else:
            sentiment_label = "N/A"
        st.metric(
            label="Avg Sentiment",
            value=sentiment_label,
            delta=None
        )
    
    with col3:
        st.metric(
            label="Open Action Items",
            value=data['action_items']['open_items'],
            delta=f"-{data['action_items']['closed_items']} closed"
        )
    
    with col4:
        st.metric(
            label="Unique Topics",
            value=data['topics']['total_unique_topics'],
            delta=None
        )
    
    st.markdown("---")
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Top Topics")
        if data['topics']['top_topics']:
            topic_df = pd.DataFrame(data['topics']['top_topics'][:10])
            fig = px.bar(
                topic_df,
                x='count',
                y='topic',
                orientation='h',
                title="Most Discussed Topics",
                labels={'count': 'Mentions', 'topic': 'Topic'},
                color='count',
                color_continuous_scale='Blues'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No topics data available")
    
    with col2:
        st.subheader("😊 Sentiment Over Time")
        sent_df = data['sentiment_timeline']
        if not sent_df.empty:
            fig = px.line(
                sent_df,
                x='date',
                y='sentiment_score',
                title="Sentiment Trend",
                labels={'sentiment_score': 'Sentiment Score', 'date': 'Date'},
                markers=True,
                color_discrete_sequence=['#1f77b4']
            )
            fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Neutral")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sentiment data available")
    
    st.markdown("---")
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚠️ Top Risks")
        if data['risks']['top_risks']:
            risk_df = pd.DataFrame(data['risks']['top_risks'][:8])
            fig = px.bar(
                risk_df,
                x='count',
                y='risk',
                orientation='h',
                title="Most Mentioned Risks",
                labels={'count': 'Mentions', 'risk': 'Risk'},
                color='count',
                color_continuous_scale='Reds'
            )
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No risks identified")
    
    with col2:
        st.subheader("💡 Top Opportunities")
        if data['opportunities']['top_opportunities']:
            opp_df = pd.DataFrame(data['opportunities']['top_opportunities'][:8])
            fig = px.bar(
                opp_df,
                x='count',
                y='opportunity',
                orientation='h',
                title="Most Mentioned Opportunities",
                labels={'count': 'Mentions', 'opportunity': 'Opportunity'},
                color='count',
                color_continuous_scale='Greens'
            )
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No opportunities identified")
    
    st.markdown("---")
    
    # Action Items Table
    st.subheader("📋 All Action Items")
    
    if data['action_items']['all_items']:
        action_df = pd.DataFrame(data['action_items']['all_items'])
        
        # Filter options
        col1, col2 = st.columns([1, 3])
        with col1:
            status_filter = st.selectbox("Filter by Status:", ["All", "Open", "Closed"])
        
        # Apply filter
        if status_filter == "Open":
            filtered_df = action_df[action_df['status'] == 'open']
        elif status_filter == "Closed":
            filtered_df = action_df[action_df['status'] == 'closed']
        else:
            filtered_df = action_df
        
        # Display table
        st.dataframe(
            filtered_df[['task', 'owner', 'deadline', 'status', 'source_file']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No action items found")


def page_search():
    """Semantic search page."""
    st.markdown('<p class="main-header">🔍 Semantic Search</p>', unsafe_allow_html=True)
    
    st.write("Search across all transcripts using natural language queries.")
    
    # Search input
    query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., 'discussions about hiring' or 'product roadmap concerns'",
        key="search_query"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        k_results = st.slider("Number of results:", 1, 10, 5)
    
    if st.button("🔍 Search", type="primary") and query:
        with st.spinner("Searching..."):
            try:
                results = embedding_store.search(query, k=k_results)
                
                if results:
                    st.success(f"Found {len(results)} relevant transcripts")
                    
                    for result in results:
                        with st.expander(f"📄 {result.get('filename', 'Unknown')} - Relevance: {result['score']:.2%}"):
                            col1, col2 = st.columns([1, 1])
                            
                            with col1:
                                st.write(f"**Date:** {result.get('upload_date', 'N/A')[:10]}")
                                st.write(f"**File Type:** {result.get('file_type', 'N/A')}")
                            
                            with col2:
                                st.write(f"**Relevance Score:** {result['score']:.2%}")
                                st.write(f"**Words:** {result.get('word_count', 'N/A')}")
                            
                            st.markdown("**Preview:**")
                            st.text(result.get('text_preview', 'No preview available')[:300] + "...")
                            
                            # Show insights if available
                            insights = analysis.load_insights(result.get('filename', ''))
                            if insights:
                                st.markdown("**Key Topics:**")
                                topics = insights.get('topics', [])[:5]
                                st.write(", ".join(topics) if topics else "None")
                else:
                    st.warning("No results found. Try a different query.")
                    
            except Exception as e:
                st.error(f"Search error: {str(e)}")
    
    # Show search statistics
    st.markdown("---")
    st.subheader("Search Index Statistics")
    
    try:
        stats = embedding_store.get_stats()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Indexed Documents", stats['total_documents'])
        with col2:
            st.metric("Vector Dimension", stats['dimension'])
        with col3:
            st.metric("Index Size", stats['index_size'])
    except Exception as e:
        st.warning(f"Could not load stats: {e}")


def page_intelligence():
    """Strategic Intelligence page."""
    st.markdown('<p class="main-header">🎯 Strategic Intelligence</p>', unsafe_allow_html=True)
    
    st.write("Founder-grade insights and strategic signals for leadership.")
    
    # Load data
    all_insights = trends.load_all_insights()
    
    if not all_insights:
        st.warning("No data available. Upload and process transcripts first.")
        return
    
    # Executive Summary
    st.subheader("📝 Executive Summary")
    
    exec_summary = trends.generate_executive_summary(all_insights, period="recent")
    st.markdown(exec_summary)
    
    st.markdown("---")
    
    # Repeated Risks Alert
    st.subheader("🚨 Repeated Unresolved Risks")
    
    risk_data = trends.analyze_risks(all_insights)
    repeated = risk_data.get('repeated_risks', [])
    
    if repeated:
        for risk in repeated[:5]:
            with st.expander(f"⚠️ {risk['risk']} (mentioned {risk['count']} times)"):
                st.write("**Occurrences:**")
                for occ in risk['occurrences']:
                    st.write(f"- {occ['filename']} ({occ['date'][:10]})")
                
                st.warning("**Action Required:** This risk has appeared multiple times without resolution.")
    else:
        st.success("✅ No repeated risks detected!")
    
    st.markdown("---")
    
    # Emerging Themes
    st.subheader("🔥 Emerging Themes (3+ mentions)")
    
    emerging = trends.detect_emerging_themes(all_insights, threshold=3)
    
    if emerging:
        for theme in emerging:
            st.info(f"**{theme['theme']}** - {theme['count']} mentions")
    else:
        st.info("No emerging themes detected yet. More data needed.")
    
    st.markdown("---")
    
    # Strategic Signals
    st.subheader("💼 Strategic Signals")
    
    # Calculate some strategic metrics
    topics_data = trends.analyze_topics(all_insights)
    actions_data = trends.track_action_items(all_insights)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Action Item Completion Rate",
            f"{actions_data['completion_rate']:.1f}%",
            delta="Execution health indicator"
        )
    
    with col2:
        top_topic_count = topics_data['top_topics'][0]['count'] if topics_data['top_topics'] else 0
        st.metric(
            "Focus Area Intensity",
            f"{top_topic_count} mentions",
            delta="Top theme frequency"
        )
    
    # Download report button
    st.markdown("---")
    if st.button("📥 Download Executive Report"):
        st.download_button(
            label="Download as Markdown",
            data=exec_summary,
            file_name=f"executive_summary_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )


def main():
    """Main application."""
    db.init_db()  # Ensure DB is initialized/migrated
    init_session_state()
    
    # Check authentication
    if not st.session_state.user:
        login_register()
        return

    # Load workspaces if none active
    if not st.session_state.active_workspace:
        workspaces = db.get_user_workspaces(st.session_state.user['id'])
        if workspaces:
            st.session_state.active_workspace = dict(workspaces[0])

    # Sidebar navigation
    st.sidebar.title("🎯 Navigation")
    st.sidebar.markdown(f"**User:** {st.session_state.user['name']}")
    
    # Workspace Selection in Sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏢 Workspace")
    workspaces = db.get_user_workspaces(st.session_state.user['id'])
    if workspaces:
        ws_list = [ws['name'] for ws in workspaces]
        # Find index of active workspace
        current_ws_name = st.session_state.active_workspace['name'] if st.session_state.active_workspace else ws_list[0]
        try:
            default_ix = ws_list.index(current_ws_name)
        except ValueError:
            default_ix = 0
            
        selected_ws_name = st.sidebar.selectbox("Active Workspace:", ws_list, index=default_ix)
        if st.session_state.active_workspace and selected_ws_name != st.session_state.active_workspace['name']:
            # Update active workspace
            for ws in workspaces:
                if ws['name'] == selected_ws_name:
                    st.session_state.active_workspace = dict(ws)
                    st.rerun()
    else:
        st.sidebar.warning("No workspaces found.")

    st.sidebar.markdown("---")
    pages = ["📤 Upload & Process", "📊 Dashboard", "🔍 Search", "🎯 Strategic Intelligence", "👥 Team Workspace"]
    if not st.session_state.company_info:
        pages.insert(0, "🏢 Company Setup")
    
    page = st.sidebar.radio(
        "Select Page:",
        pages
    )
    
    # System info
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ System Info")
    st.sidebar.write(f"**LLM Provider:** {config.LLM_PROVIDER}")
    st.sidebar.write(f"**Model:** {config.OPENAI_MODEL if config.LLM_PROVIDER == 'openai' else config.OLLAMA_MODEL}")
    
    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.session_state.active_workspace = None
        st.rerun()

    # Reset Company button
    if st.session_state.company_info:
        st.sidebar.markdown("---")
        if st.sidebar.button("🗑️ Reset Company Info", help="Delete company intelligence and start over"):
            if intelligence.COMPANY_INFO_PATH.exists():
                intelligence.COMPANY_INFO_PATH.unlink()
            st.session_state.company_info = None
            st.rerun()
    
    # Route to appropriate page
    if page == "🏢 Company Setup":
        page_setup()
    elif page == "📤 Upload & Process":
        page_upload()
    elif page == "📊 Dashboard":
        page_dashboard()
    elif page == "🔍 Search":
        page_search()
    elif page == "🎯 Strategic Intelligence":
        page_intelligence()
    elif page == "👥 Team Workspace":
        page_workspace()


if __name__ == "__main__":
    main()
