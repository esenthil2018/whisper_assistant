# src/ui/components/chat.py
import streamlit as st
#from typing import Literal
from typing import Literal, Dict, Any, Optional, List  # Add Optional to imports
import logging

class ChatInterface:
    """Chat interface component."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_styles()

    def _setup_styles(self):
        """Setup custom CSS styles for the chat interface."""
        st.markdown("""
        <style>
        .user-message {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        .assistant-message {
            background-color: #e8f0fe;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        .message-metadata {
            font-size: 0.8rem;
            color: #666;
            margin-top: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)

    def display_message(
        self,
        role: Literal['user', 'assistant'],
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Display a chat message."""
        message_class = f"{role}-message"
        
        with st.container():
            st.markdown(f"""
            <div class="{message_class}">
                <strong>{'You' if role == 'user' else 'Assistant'}:</strong>
                <div>{content}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if metadata:
                with st.expander("Message Details"):
                    for key, value in metadata.items():
                        st.write(f"{key}: {value}")

    def display_error(self, error_message: str):
        """Display an error message."""
        st.error(error_message)

    def display_thinking(self):
        """Display a thinking indicator."""
        with st.spinner("Thinking..."):
            st.empty()

    def display_code_preview(self, code: str):
        """Display code with syntax highlighting."""
        st.code(code, language='python')

    def display_sources(self, sources: List[Dict[str, str]]):
        """Display reference sources."""
        if sources:
            with st.expander("Sources"):
                for source in sources:
                    st.write(f"- {source['file']}")

    def clear_history(self):
        """Clear chat history."""
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.experimental_rerun()