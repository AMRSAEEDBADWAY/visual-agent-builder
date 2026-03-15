import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_user_by_username, update_user_password, get_all_users, get_recent_activity
from core.auth import hash_password

st.set_page_config(page_title="Profile & Settings", page_icon="👤", layout="wide")

# Ensure user is logged in
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("Please log in from the Login page first.")
    st.stop()
    
def main():
    st.title(f"👤 Profile: {st.session_state.username}")
    
    user_data = get_user_by_username(st.session_state.username)
    if not user_data:
        st.error("User data not found!")
        return

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Your Information")
        st.write(f"**Username:** {user_data['username']}")
        st.write(f"**Email:** {user_data['email']}")
        st.write(f"**Role:** {user_data['role'].capitalize()}")
        st.write(f"**Joined:** {user_data['created_at']}")
        
    with col2:
        st.subheader("Change Password")
        with st.form("change_password_form"):
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if new_password and new_password == confirm_password and len(new_password) >= 6:
                    update_user_password(user_data['username'], hash_password(new_password))
                    st.success("Password updated successfully!")
                else:
                    st.error("Invalid password or passwords do not match. Must be 6+ chars.")
                    
    # Admin Dashboard
    if user_data['role'] == 'admin':
        st.divider()
        st.subheader("🛠️ Admin Dashboard")
        
        tab_users, tab_logs = st.tabs(["Users List", "Activity Logs"])
        
        with tab_users:
            st.info("As an admin, you can view the list of all registered users.")
            all_users = get_all_users()
            st.dataframe(
                all_users, 
                column_config={
                    "id": "User ID",
                    "username": "Username",
                    "email": "Email",
                    "role": "Role",
                    "created_at": "Joined At"
                },
                hide_index=True,
                use_container_width=True
            )
            
        with tab_logs:
            st.info("Recent system activity (Logins, Registration, etc.)")
            logs = get_recent_activity(limit=100)
            st.dataframe(
                logs,
                column_config={
                    "id": "Log ID",
                    "username": "User",
                    "action": "Action",
                    "details": "Details",
                    "timestamp": "Time"
                },
                hide_index=True,
                use_container_width=True
            )

if __name__ == "__main__":
    main()
