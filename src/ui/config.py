# src/ui/config.py
from typing import Dict, Any
import streamlit as st

# UI Theme Configuration
THEME_CONFIG = {
    "primaryColor": "#FF4B4B",
    "backgroundColor": "#FFFFFF",
    "secondaryBackgroundColor": "#F0F2F6",
    "textColor": "#262730",
    "font": "sans serif"
}

# Chat Interface Configuration
CHAT_CONFIG = {
    "max_messages": 50,
    "max_message_length": 2000,
    "suggestion_count": 3,
    "typing_indicator_delay": 0.05
}

# Code Viewer Configuration
CODE_CONFIG = {
    "max_lines": 500,
    "show_line_numbers": True,
    "wrap_long_lines": False,
    "supported_languages": ["python", "bash", "json", "yaml"]
}

# Layout Configuration
LAYOUT_CONFIG = {
    "chat_column_width": 2,
    "code_column_width": 1,
    "max_content_width": "1200px"
}

def apply_custom_css():
    """Apply custom CSS styles."""
    st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .stTextInput > div > div > input {
            caret-color: #FF4B4B;
        }
        
        .stButton > button {
            background-color: #FF4B4B;
            color: white;
            border-radius: 4px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            background-color: #FF3333;
        }
        
        .code-block {
            background-color: #f6f8fa;
            border-radius: 4px;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        
        .message-container {
            margin: 1rem 0;
            padding: 1rem;
            border-radius: 4px;
        }
        
        .user-message {
            background-color: #f0f2f6;
        }
        
        .assistant-message {
            background-color: #e8f0fe;
        }
        
        .suggestion-button {
            border: 1px solid #FF4B4B;
            color: #FF4B4B;
            background-color: transparent;
            border-radius: 4px;
            padding: 0.25rem 0.5rem;
            margin: 0.25rem;
            cursor: pointer;
        }
        
        .suggestion-button:hover {
            background-color: #FF4B4B;
            color: white;
        }
        
        .error-message {
            color: #FF4B4B;
            padding: 1rem;
            border: 1px solid #FF4B4B;
            border-radius: 4px;
            margin: 1rem 0;
        }
        </style>
    """, unsafe_allow_html=True)

def get_session_config() -> Dict[str, Any]:
    """Get session-specific configuration."""
    if 'config' not in st.session_state:
        st.session_state.config = {
            'theme': THEME_CONFIG,
            'chat': CHAT_CONFIG,
            'code': CODE_CONFIG,
            'layout': LAYOUT_CONFIG
        }
    return st.session_state.config