import sqlite3
from src import db

def seed():
    db.init_db()
    
    # Create Demo User
    print("Creating demo users...")
    db.create_user("Alice Admin", "alice@example.com", "password123")
    db.create_user("Bob Member", "bob@example.com", "password123")
    
    alice = db.get_user_by_email("alice@example.com")
    bob = db.get_user_by_email("bob@example.com")
    
    # Create Workspace
    print("Creating demo workspace...")
    ws_id = db.create_workspace("Merck Strategy Team", alice['id'])
    
    # Add Bob to workspace
    print("Adding members...")
    conn = sqlite3.connect(db.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO workspace_members (user_id, workspace_id, role) VALUES (?, ?, 'member')", (bob['id'], ws_id))
    conn.commit()
    conn.close()
    
    # Generate an invite code
    code = db.generate_invite_code(ws_id)
    print(f"Invite code generated: {code}")
    
    # Create some posts
    print("Adding demo posts...")
    db.create_post(ws_id, alice['id'], "update", "Just uploaded the Q3 transcript analysis.")
    db.create_post(ws_id, bob['id'], "praise", "Great work on the timeline summary @Alice!", alice['id'])
    db.create_post(ws_id, alice['id'], "credit", "Bob found those missing links for Merck KGaA.", bob['id'])
    
    print("Seeding complete!")

if __name__ == "__main__":
    seed()
