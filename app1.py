import os
from dotenv import load_dotenv
import streamlit as st
import psycopg2
import hashlib
from openai import OpenAI

# ----------------------
# LOAD ENV
# ----------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------
# DATABASE
# ----------------------
conn = psycopg2.connect(
    os.getenv("DATABASE_URL"),
    sslmode="require"
)
cursor = conn.cursor()

# ----------------------
# TABLES
# ----------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT,
    email TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    email TEXT,
    chat_name TEXT,
    sender TEXT,
    message TEXT
)
""")
conn.commit()

# ----------------------
# HASH
# ----------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ----------------------
# AUTH
# ----------------------
def register_user(username, email, password):
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hash_password(password))
        )
        conn.commit()
        return True
    except:
        return False

def check_login(email, password):
    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, hash_password(password))
    )
    return cursor.fetchone()

# ----------------------
# CHAT DB
# ----------------------
def save_message(email, chat_name, sender, message):
    cursor.execute(
        "INSERT INTO chats (email, chat_name, sender, message) VALUES (%s, %s, %s, %s)",
        (email, chat_name, sender, message)
    )
    conn.commit()

def load_chats(email):
    cursor.execute(
        "SELECT DISTINCT chat_name FROM chats WHERE email=%s",
        (email,)
    )
    return [row[0] for row in cursor.fetchall()]

def load_chat_messages(email, chat_name):
    cursor.execute(
        "SELECT sender, message FROM chats WHERE email=%s AND chat_name=%s ORDER BY id ASC",
        (email, chat_name)
    )
    return cursor.fetchall()

def clear_chat(email, chat_name):
    cursor.execute(
        "DELETE FROM chats WHERE email=%s AND chat_name=%s",
        (email, chat_name)
    )
    conn.commit()

# ----------------------
# TITLE GENERATOR
# ----------------------
def generate_chat_title(text):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Generate a short 3-5 word chat title."},
            {"role": "user", "content": text}
        ],
        temperature=0.5
    )
    return res.choices[0].message.content.strip()

# ----------------------
# AI INTENT DETECTION
# ----------------------
def is_mental_health_related(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
You are a strict but intelligent classifier.

Return ONLY "YES" or "NO".

Return YES if:
- The message expresses or implies emotions, stress, pressure, or mental state
- The user is talking about exams, studies, or work WITH stress, tiredness, fear, or feelings
- The message is indirectly emotional (example: "I have exams", "I'm busy with studies", "I didn't sleep")

Return NO if:
- The message is purely factual or informational (example: "What is FIFO?", "Explain Java", "Who is PM of India")
- No emotional or personal context is present

IMPORTANT:
If there is even slight emotional context or real-life struggle → return YES
"""
                },
                {"role": "user", "content": text}
            ],
            temperature=0
        )

        result = response.choices[0].message.content.strip().upper()
        return result == "YES"

    except:
        return False

# ----------------------
# SESSION
# ----------------------
if "page" not in st.session_state:
    st.session_state.page = "login"
if "user" not in st.session_state:
    st.session_state.user = None
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "New Chat"

# ----------------------
# STYLES
# ----------------------
def auth_style():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #E6D6F5, #D8BFD8);
        color: black;
    }
    h1 {text-align:center; color:#4B0082;}
    .stButton>button {
        background-color:#9370DB;
        color:white;
        border-radius:10px;
        width:100%;
    }
    </style>
    """, unsafe_allow_html=True)

def chat_style():
    st.markdown("""
    <style>
    .stApp {background:#0f0f0f; color:white;}
    section[data-testid="stSidebar"] {background:#111;}
    .user-msg {
        background:#7c3aed;
        padding:12px;
        border-radius:15px;
        margin:5px;
        text-align:right;
    }
    .bot-msg {
        background:#262626;
        padding:12px;
        border-radius:15px;
        margin:5px;
        text-align:left;
    }
    </style>
    """, unsafe_allow_html=True)

# ----------------------
# LOGIN
# ----------------------
def login():
    auth_style()
    st.title("💜 VibeLift")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_login(email, password):
            st.session_state.user = email
            st.session_state.page = "chat"
            st.rerun()
        else:
            st.error("Invalid login")

    if st.button("Signup"):
        st.session_state.page = "signup"
        st.rerun()

# ----------------------
# SIGNUP
# ----------------------
def signup():
    auth_style()
    st.title("Create Account")

    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        if register_user(username, email, password):
            st.success("Account created")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("Email exists")

    if st.button("Back"):
        st.session_state.page = "login"
        st.rerun()

# ----------------------
# CHATBOT
# ----------------------
def chatbot():
    chat_style()
    st.title("💜 VibeLift Chat")

    email = st.session_state.user

    # Sidebar
    with st.sidebar:
        st.markdown("### 💬 Chats")
        chats = load_chats(email)

        for c in chats:
            if st.button(c, key=c):
                st.session_state.current_chat = c
                st.rerun()

        if st.button("➕ New Chat"):
            st.session_state.current_chat = "New Chat"
            st.rerun()

        if st.button("🗑 Clear Chat"):
            clear_chat(email, st.session_state.current_chat)

        if st.button("🚪 Logout"):
            st.session_state.page = "login"
            st.session_state.user = None
            st.rerun()

    # Load messages
    messages = load_chat_messages(email, st.session_state.current_chat)

    for sender, msg in messages:
        if sender == "You":
            st.markdown(f"<div class='user-msg'>{msg}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-msg'>{msg}</div>", unsafe_allow_html=True)

    user_input = st.chat_input("Type your thoughts...")

    if user_input:

        greetings = ["hi", "hello", "hey"]

        is_current_mental = is_mental_health_related(user_input)

        # STRICT FILTER
        if user_input.lower() not in greetings and not is_current_mental:
            reply = (
                "Hey 💜 I'm a mental health support chatbot. "
                "I may not be the best for topics like politics, education, or general knowledge. "
                "But I'm always here to listen if you want to talk about your feelings."
            )

            save_message(email, st.session_state.current_chat, "You", user_input)
            save_message(email, st.session_state.current_chat, "Bot", reply)
            st.rerun()

        # 🚨 CRISIS HANDLING
        if "die" in user_input.lower():
            reply = (
                "I'm really sorry you're feeling this way 💜. "
                "You don’t have to go through this alone. "
                "Please consider reaching out to someone you trust."
            )

            save_message(email, st.session_state.current_chat, "You", user_input)
            save_message(email, st.session_state.current_chat, "Bot", reply)
            st.rerun()

        # Title
        if st.session_state.current_chat == "New Chat":
            title = generate_chat_title(user_input)

            if title in load_chats(email):
                title += f" {len(load_chats(email))}"
            st.session_state.current_chat = title
        else:
            title = st.session_state.current_chat

        # SYSTEM PROMPT
        chat_history = [
            {
                "role": "system",
                "content": """
You are VibeLift, a caring mental health assistant.

- Be empathetic
- Be supportive
- Keep responses human-like
- Focus only on emotional support
"""
            }
        ]

        for sender, msg in messages[-20:]:
            role = "user" if sender == "You" else "assistant"
            chat_history.append({"role": role, "content": msg})

        chat_history.append({"role": "user", "content": user_input})

        # AI RESPONSE
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_history,
            temperature=0.9
        )

        reply = response.choices[0].message.content

        # Save
        save_message(email, title, "You", user_input)
        save_message(email, title, "Bot", reply)

        st.rerun()

# ----------------------
# ROUTER
# ----------------------
if st.session_state.page == "login":
    login()
elif st.session_state.page == "signup":
    signup()
else:
    chatbot()