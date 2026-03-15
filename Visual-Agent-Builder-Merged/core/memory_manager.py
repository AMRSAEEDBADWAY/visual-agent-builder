import uuid
from typing import List, Dict, Optional
from core.database import get_db_connection
from core.security import encrypt_text, decrypt_text

def save_message(project_id: str, sender: str, message: str, agent_id: Optional[str] = None) -> str:
    """
    Saves a message to the chat history.
    sender: 'user' or 'agent'
    """
    msg_id = str(uuid.uuid4())
    encrypted_msg = encrypt_text(message)
    
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO chat_history (id, project_id, sender, message, agent_id)
               VALUES (?, ?, ?, ?, ?)""",
            (msg_id, project_id, sender, encrypted_msg, agent_id)
        )
        return msg_id

def get_project_chat_history(project_id: str, limit: int = 50) -> List[Dict]:
    """
    Retrieves the chat history for a specific project.
    Ordered by timestamp ascending (oldest to newest).
    """
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM chat_history 
               WHERE project_id = ? 
               ORDER BY timestamp ASC 
               LIMIT ?""",
            (project_id, limit)
        ).fetchall()
        
        history = []
        for row in rows:
            msg_dict = dict(row)
            msg_dict['message'] = decrypt_text(msg_dict['message'])
            history.append(msg_dict)
            
        return history

def get_agent_memory_context(project_id: str, agent_id: str, limit: int = 10) -> str:
    """
    Generates a contextual string of recent history for a specific agent
    to be injected into their LP prompt as long-term memory.
    """
    history = get_project_chat_history(project_id, limit=limit)
    if not history:
        return "No previous conversation history."
        
    context_lines = []
    for msg in history:
        if msg['sender'] == 'user':
            context_lines.append(f"User: {msg['message']}")
        else:
            # If the sender is an agent, denote which one (or 'You' if it's the current agent)
            if msg['agent_id'] == agent_id:
                context_lines.append(f"You: {msg['message']}")
            else:
                context_lines.append(f"Agent {msg['agent_id']}: {msg['message']}")
                
    context_str = "\n".join(context_lines)
    return f"--- RECENT CONVERSATION HISTORY ---\n{context_str}\n-----------------------------------"

def clear_project_history(project_id: str):
    """Deletes all chat history for a project. Useful for resetting memory."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM chat_history WHERE project_id = ?", (project_id,))
