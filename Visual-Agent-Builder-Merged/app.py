import streamlit as st
import sqlite3
import uuid
import sys
import os

# Add the parent directory to sys.path to resolve 'core' imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.auth import authenticate_user, hash_password, generate_session_token, verify_security_answer
from core.database import create_user, get_user_by_username, init_db, get_user_by_session_token, update_session_token, update_user_password, log_activity
from streamlit_cookies_controller import CookieController

# Ensure DB is initialized
init_db()

st.set_page_config(page_title="Visual Agent Builder - Login", page_icon="🤖", layout="centered")

# Initialize controller before any layout uses it
controller = CookieController()

def init_session_state():
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None
        
    # Auto-login via cookie
    if not st.session_state.user_id:
        # Wait until session_token is checked
        session_token = controller.get('session_token')
        if session_token:
            user = get_user_by_session_token(session_token)
            if user:
                st.session_state.user_id = user['id']
                st.session_state.username = user['username']
                st.session_state.role = user['role']

def main():
    init_session_state()

    # If already logged in, show welcome / redirect
    if st.session_state.user_id:
        role_badge = f" ({st.session_state.role.capitalize()})" if st.session_state.role else ""
        st.success(f"Welcome back, {st.session_state.username}!{role_badge}")
        st.info("Please navigate to the Dashboard to manage your projects.")
        
        if st.button("Logout"):
            if st.session_state.user_id:
                # Log logout
                log_activity(st.session_state.username, "LOGOUT", "User logged out manually")
                # Remove session token from DB
                update_session_token(st.session_state.user_id, None)
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.role = None
            try:
                controller.remove('session_token')
            except KeyError:
                pass # Cookie might not exist if Remember Me wasn't checked
            st.rerun()
        return

    st.title("🤖 Visual Agent Builder")
    st.markdown("### Build AI Multi-Agent Teams Visually")

    tab_login, tab_register, tab_forgot = st.tabs(["Login", "Register", "Forgot Password"])

    with tab_login:
        with st.form("login_form"):
            login_username = st.text_input("Username")
            login_password = st.text_input("Password", type="password")
            remember_me = st.checkbox("Remember Me")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                if not login_username or not login_password:
                    st.error("Please fill in both fields.")
                else:
                    user = authenticate_user(login_username, login_password)
                    if user:
                        st.session_state.user_id = user['id']
                        st.session_state.username = user['username']
                        st.session_state.role = user['role']
                        
                        if remember_me:
                            token = generate_session_token()
                            update_session_token(user['id'], token)
                            controller.set('session_token', token, max_age=86400*30) # 30 days
                            
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

    with tab_register:
        with st.form("register_form"):
            reg_username = st.text_input("Username")
            reg_email = st.text_input("Email")
            reg_password = st.text_input("Password", type="password")
            reg_password_confirm = st.text_input("Confirm Password", type="password")
            st.markdown("#### سؤال الأمان (لاستعادة كلمة المرور)")
            security_question = st.selectbox("اختر سؤالاً", [
                "ما هو لونك المفضل؟", 
                "ما هو اسم أول حيوان أليف ربيته؟", 
                "في أي مدينة ولدت؟",
                "ما هو اسم مدرستك الابتدائية؟"
            ])
            security_answer = st.text_input("Answer")
            reg_submitted = st.form_submit_button("Create Account", use_container_width=True)

            if reg_submitted:
                if not reg_username or not reg_email or not reg_password or not security_answer:
                    st.error("Please fill in all fields.")
                elif reg_password != reg_password_confirm:
                    st.error("Passwords do not match.")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    existing_user = get_user_by_username(reg_username)
                    if existing_user:
                        st.error("Username already exists. Please choose another one.")
                    else:
                        user_id = str(uuid.uuid4())
                        hashed_pw = hash_password(reg_password)
                        hashed_answer = hash_password(security_answer.strip().lower())
                        
                        try:
                            create_user(user_id, reg_username, reg_email, hashed_pw, security_question, hashed_answer)
                            log_activity(reg_username, "REGISTER", "New account created")
                            st.success("Account created successfully! You can now log in.")
                        except sqlite3.IntegrityError:
                            st.error("Email already in use. Try logging in.")
                        except Exception as e:
                            st.error(f"Error creating account: {e}")

    with tab_forgot:
        st.markdown("### Recover Password")
        forgot_username = st.text_input("Enter your Username", key="forgot_user")
        
        if forgot_username:
            user_data = get_user_by_username(forgot_username)
            if user_data and user_data['security_question']:
                st.info(f"Security Question: **{user_data['security_question']}**")
                forgot_answer = st.text_input("Your Answer", type="password")
                new_password = st.text_input("New Password", type="password")
                new_password_confirm = st.text_input("Confirm New Password", type="password")
                
                if st.button("Reset Password", key="reset_btn"):
                    if not forgot_answer or not new_password:
                        st.error("Please fill in all fields.")
                    elif new_password != new_password_confirm:
                        st.error("Passwords do not match.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        if verify_security_answer(forgot_answer, user_data['security_answer_hash']):
                            update_user_password(forgot_username, hash_password(new_password))
                            st.success("Password reset successfully! You can now log in.")
                        else:
                            st.error("Incorrect answer to security question.")
            elif user_data:
                st.error("This user did not set a security question.")
            else:
                st.error("User not found.")

if __name__ == "__main__":
    main()
