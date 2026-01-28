import sqlite3
import os
import bcrypt

DB_PATH = "data/app.db"

def init_db():
    if not os.path.exists("data"):
        os.makedirs("data")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')
    
    # Workspaces table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workspaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        admin_id INTEGER,
        FOREIGN KEY (admin_id) REFERENCES users (id)
    )
    ''')
    
    # WorkspaceMembers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workspace_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        workspace_id INTEGER,
        role TEXT DEFAULT 'member',
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
    )
    ''')
    
    # Invitations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS invitations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER,
        invite_code TEXT UNIQUE NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
    )
    ''')
    
    # Posts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER,
        author_id INTEGER,
        type TEXT NOT NULL,
        content TEXT NOT NULL,
        custom_emoji TEXT,
        target_user_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (workspace_id) REFERENCES workspaces (id),
        FOREIGN KEY (author_id) REFERENCES users (id),
        FOREIGN KEY (target_user_id) REFERENCES users (id)
    )
    ''') 
    
    # Post Reactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS post_reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        emoji TEXT NOT NULL,
        FOREIGN KEY (post_id) REFERENCES posts (id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(post_id, user_id, emoji)
    )
    ''')
    
    # WorkNotes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS work_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER,
        workspace_id INTEGER,
        raw_note_text TEXT,
        generated_description TEXT,
        final_accepted_description TEXT,
        status TEXT DEFAULT 'draft',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (author_id) REFERENCES users (id),
        FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
    )
    ''')
    
    conn.commit()
    
    # Migrations
    cursor.execute("PRAGMA table_info(posts)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'custom_emoji' not in columns:
        print("Migrating: Adding custom_emoji to posts table...")
        cursor.execute("ALTER TABLE posts ADD COLUMN custom_emoji TEXT")
        conn.commit()
        
    conn.close()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(name, email, password):
    hashed = hash_password(password)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_workspace(name, admin_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Create workspace
        cursor.execute("INSERT INTO workspaces (name, admin_id) VALUES (?, ?)", (name, admin_id))
        workspace_id = cursor.lastrowid
        
        # Add admin as member
        cursor.execute("INSERT INTO workspace_members (user_id, workspace_id, role) VALUES (?, ?, ?)", 
                       (admin_id, workspace_id, 'admin'))
        
        conn.commit()
        return workspace_id
    except Exception as e:
        print(f"Error creating workspace: {e}")
        return None
    finally:
        conn.close()

def get_user_workspaces(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.*, wm.role 
        FROM workspaces w
        JOIN workspace_members wm ON w.id = wm.workspace_id
        WHERE wm.user_id = ?
    """, (user_id,))
    workspaces = cursor.fetchall()
    conn.close()
    return workspaces

def get_workspace_members(workspace_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.name, u.email, wm.role
        FROM users u
        JOIN workspace_members wm ON u.id = wm.user_id
        WHERE wm.workspace_id = ?
    """, (workspace_id,))
    members = cursor.fetchall()
    conn.close()
    return members

def generate_invite_code(workspace_id):
    import uuid
    code = str(uuid.uuid4())[:8].upper()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO invitations (workspace_id, invite_code) VALUES (?, ?)", (workspace_id, code))
        conn.commit()
        return code
    except Exception as e:
        print(f"Error generating invite: {e}")
        return None
    finally:
        conn.close()

def get_workspace_invites(workspace_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invitations WHERE workspace_id = ? AND is_active = 1", (workspace_id,))
    invites = cursor.fetchall()
    conn.close()
    return invites

def join_workspace_by_invite(user_id, invite_code):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Validate invite
        cursor.execute("SELECT workspace_id FROM invitations WHERE invite_code = ? AND is_active = 1", (invite_code,))
        row = cursor.fetchone()
        if not row:
            return False, "Invalid or inactive invite code."
        
        workspace_id = row[0]
        
        # Check if already a member
        cursor.execute("SELECT id FROM workspace_members WHERE user_id = ? AND workspace_id = ?", (user_id, workspace_id))
        if cursor.fetchone():
            return False, "You are already a member of this workspace."
        
        # Add as member
        cursor.execute("INSERT INTO workspace_members (user_id, workspace_id, role) VALUES (?, ?, 'member')", (user_id, workspace_id))
        conn.commit()
        return True, "Successfully joined workspace!"
    except Exception as e:
        print(f"Error joining workspace: {e}")
        return False, "An error occurred while joining."
    finally:
        conn.close()

def create_post(workspace_id, author_id, post_type, content, target_user_id=None, custom_emoji=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO posts (workspace_id, author_id, type, content, target_user_id, custom_emoji)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (workspace_id, author_id, post_type, content, target_user_id, custom_emoji))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating post: {e}")
        return False
    finally:
        conn.close()

def get_workspace_posts(workspace_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u_author.name as author_name, u_target.name as target_name
        FROM posts p
        JOIN users u_author ON p.author_id = u_author.id
        LEFT JOIN users u_target ON p.target_user_id = u_target.id
        WHERE p.workspace_id = ?
        ORDER BY p.timestamp DESC
    """, (workspace_id,))
    posts = cursor.fetchall()
    conn.close()
    return posts

def toggle_reaction(post_id, user_id, emoji):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Check if exists
        cursor.execute("SELECT id FROM post_reactions WHERE post_id=? AND user_id=? AND emoji=?", (post_id, user_id, emoji))
        existing = cursor.fetchone()
        
        if existing:
            # Remove
            cursor.execute("DELETE FROM post_reactions WHERE id=?", (existing[0],))
            result = "removed"
        else:
            # Add
            cursor.execute("INSERT INTO post_reactions (post_id, user_id, emoji) VALUES (?, ?, ?)", (post_id, user_id, emoji))
            result = "added"
            
        conn.commit()
        return True, result
    except Exception as e:
        print(f"Error toggling reaction: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_post_reactions(post_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.emoji, u.name as user_name, u.id as user_id
        FROM post_reactions pr
        JOIN users u ON pr.user_id = u.id
        WHERE pr.post_id = ?
    """, (post_id,))
    rows = cursor.fetchall()
    conn.close()
    
    # Aggegate results: {'👍': {'count': 2, 'users': ['Alice', 'Bob'], 'user_ids': [1, 2]}}
    reactions = {}
    for emoji, name, uid in rows:
        if emoji not in reactions:
            reactions[emoji] = {'count': 0, 'users': [], 'user_ids': []}
        reactions[emoji]['count'] += 1
        reactions[emoji]['users'].append(name)
        reactions[emoji]['user_ids'].append(uid)
    return reactions

def get_user_stats(user_id, workspace_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Counts
    cursor.execute("SELECT count(*) FROM posts WHERE target_user_id = ? AND workspace_id = ? AND type = 'praise'", (user_id, workspace_id))
    praise_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(*) FROM posts WHERE target_user_id = ? AND workspace_id = ? AND type = 'credit'", (user_id, workspace_id))
    credit_count = cursor.fetchone()[0]
    
    # Recent mentions
    cursor.execute("""
        SELECT p.*, u.name as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id
        WHERE p.target_user_id = ? AND p.workspace_id = ? 
        ORDER BY p.timestamp DESC LIMIT 3
    """, (user_id, workspace_id))
    cursor.row_factory = sqlite3.Row
    recent_mentions = cursor.fetchall()
    
    conn.close()
    return {
        "praise_count": praise_count,
        "credit_count": credit_count,
        "recent_mentions": recent_mentions
    }

def create_work_note(workspace_id, author_id, raw_note_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO work_notes (workspace_id, author_id, raw_note_text)
            VALUES (?, ?, ?)
        """, (workspace_id, author_id, raw_note_text))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error creating work note: {e}")
        return None
    finally:
        conn.close()

def update_work_note(note_id, generated_description=None, final_accepted_description=None, status=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if generated_description is not None:
            cursor.execute("UPDATE work_notes SET generated_description = ? WHERE id = ?", (generated_description, note_id))
        if final_accepted_description is not None:
            cursor.execute("UPDATE work_notes SET final_accepted_description = ? WHERE id = ?", (final_accepted_description, note_id))
        if status is not None:
            cursor.execute("UPDATE work_notes SET status = ? WHERE id = ?", (status, note_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating work note: {e}")
        return False
    finally:
        conn.close()

def get_user_work_notes(user_id, workspace_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM work_notes 
        WHERE author_id = ? AND workspace_id = ?
        ORDER BY created_at DESC
    """, (user_id, workspace_id))
    notes = cursor.fetchall()
    conn.close()
    return notes

def get_workspace_published_notes(workspace_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.*, u.name as author_name
        FROM work_notes n
        JOIN users u ON n.author_id = u.id
        WHERE n.workspace_id = ? AND n.status = 'published'
        ORDER BY n.created_at DESC
    """, (workspace_id,))
    notes = cursor.fetchall()
    conn.close()
    return notes

def get_work_note_by_id(note_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM work_notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    conn.close()
    return note

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
