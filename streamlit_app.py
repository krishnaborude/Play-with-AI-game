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

def initialize_board():
    return ["" for _ in range(9)]

def check_winner(board):
    # Winning combinations
    lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]  # Diagonals
    ]
    for line in lines:
        if board[line[0]] and board[line[0]] == board[line[1]] == board[line[2]]:
            return board[line[0]]
    if "" not in board:
        return "Draw"
    return None

def render_tic_tac_toe():
    if 'board' not in st.session_state:
        st.session_state.board = initialize_board()
    if 'current_player' not in st.session_state:
        st.session_state.current_player = "X"

    st.write(f"Current Player: {st.session_state.current_player}")
    
    # Create the 3x3 grid using a container
    game_container = st.container()
    with game_container:
        for i in range(0, 9, 3):
            cols = st.columns(3)
            for j in range(3):
                with cols[j]:
                    cell_key = f"ttt_cell_{i+j}"  # Added prefix to make keys more unique
                    if st.button(st.session_state.board[i + j] or " ", key=cell_key):
                        if st.session_state.board[i + j] == "":
                            st.session_state.board[i + j] = st.session_state.current_player
                            winner = check_winner(st.session_state.board)
                            if winner:
                                if winner == "Draw":
                                    st.success("Game Over! It's a Draw!")
                                else:
                                    st.success(f"Player {winner} wins!")
                                if st.button("Play Again", key=f"ttt_play_again_{datetime.now().timestamp()}"):
                                    st.session_state.board = initialize_board()
                                    st.session_state.current_player = "X"
                                    st.rerun()
                            else:
                                st.session_state.current_player = "O" if st.session_state.current_player == "X" else "X"
                                st.rerun()

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
            email = st.text_input("Email", key="login_email_input")
            password = st.text_input("Password", type="password", key="login_password_input")
            if st.button("Login", key="login_submit_button"):
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
            new_email = st.text_input("Email", key="signup_email_input")
            new_password = st.text_input("Password", type="password", key="signup_password_input")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password_input")
            if st.button("Sign Up", key="signup_submit_button"):
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
        if st.sidebar.button("Logout", key="main_logout_button"):
            st.session_state.user_email = None
            st.rerun()
        
        # Game selection
        st.subheader("Select a Game")
        game_options = ["Tic Tac Toe", "Circle Game", "Memory Game", "Word Guess", "Math Challenge", "Rock Paper Scissors"]
        selected_game = st.selectbox("Choose a game", game_options, key="main_game_selector")
        
        if st.button("Play Game", key="main_play_game_button"):
            st.session_state.selected_game = selected_game
            # Reset game state when starting a new game
            if selected_game == "Tic Tac Toe":
                st.session_state.board = initialize_board()
                st.session_state.current_player = "X"
            st.rerun()
        
        if 'selected_game' in st.session_state:
            st.subheader(f"Playing {st.session_state.selected_game}")
            if st.session_state.selected_game == "Tic Tac Toe":
                render_tic_tac_toe()
            else:
                st.write("This game is not implemented yet.")

if __name__ == "__main__":
    main() 