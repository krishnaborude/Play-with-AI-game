import streamlit as st
import requests
import json
from datetime import datetime

# Configure the page
st.set_page_config(
    page_title="Game Interface",
    page_icon="🎮",
    layout="wide"
)

# API endpoint
API_URL = "http://localhost:8000"

def main():
    st.title("Game Interface")
    
    # Session state for user authentication
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    
    # Login/Signup section
    if st.session_state.user_email is None:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.subheader("Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                try:
                    response = requests.post(
                        f"{API_URL}/login",
                        data={"email": email, "password": password}
                    )
                    if response.status_code == 200:
                        st.session_state.user_email = email
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        with tab2:
            st.subheader("Sign Up")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            if st.button("Sign Up"):
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/register",
                            data={"email": new_email, "password": new_password}
                        )
                        if response.status_code == 200:
                            st.success("Registration successful! Please login.")
                        else:
                            st.error("Registration failed")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    # Main content when logged in
    else:
        st.sidebar.title(f"Welcome, {st.session_state.user_email}")
        if st.sidebar.button("Logout"):
            st.session_state.user_email = None
            st.rerun()
        
        # Game selection
        st.subheader("Select a Game")
        game_options = ["Tic Tac Toe", "Circle Game", "Memory Game", "Word Guess", "Math Challenge", "Rock Paper Scissors"]
        selected_game = st.selectbox("Choose a game", game_options)
        
        if st.button("Play Game"):
            st.session_state.selected_game = selected_game
            st.rerun()
        
        if 'selected_game' in st.session_state:
            st.subheader(f"Playing {st.session_state.selected_game}")
            # Add game-specific content here
            st.write("Game content will be displayed here")

if __name__ == "__main__":
    main() 