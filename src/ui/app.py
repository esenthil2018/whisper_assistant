# src/ui/app.py
import streamlit as st
import asyncio
import logging
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv
from src.storage import StorageManager
from src.ai_processing import AIProcessor
from src.ui.components.chat import ChatInterface
from src.ui.components.code_viewer import CodeViewer
from src.ui.utils.formatting import format_response
from pathlib import Path

class WhisperAssistantUI:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._verify_data_exists()
        self._initialize_session_state()
        self._setup_components()

    def _verify_data_exists(self):
        """Verify if the required data exists."""
        try:
            metadata_path = Path('./data/metadata.db')
            embeddings_path = Path('./data/embeddings')
            
            if not metadata_path.exists() or not embeddings_path.exists():
                st.error("""
                    Required data files not found. Please run setup first:
                    ```bash
                    python setup_whisper_assistant.py
                    ```
                """)
                st.stop()
        except Exception as e:
            self.logger.error(f"Error verifying data: {e}")
            raise

    def _initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'current_response' not in st.session_state:
            st.session_state.current_response = None
        if 'processor' not in st.session_state:
            st.session_state.processor = self._initialize_processor()

    def _setup_components(self):
        """Initialize UI components."""
        self.chat_interface = ChatInterface()
        self.code_viewer = CodeViewer()

    def _initialize_processor(self) -> AIProcessor:
        """Initialize the AI processor with storage manager."""
        try:
            load_dotenv()
            
            # Initialize storage without Redis
            storage = StorageManager(
                persist_directory='./data/embeddings',
                metadata_db_path='./data/metadata.db',
                preserve_data=True  # Simplified initialization without Redis
            )
            
            # Verify storage has data
            repo_info = storage.get_repository_info()
            if not repo_info:
                self.logger.warning("No repository data found in storage")
            else:
                self.logger.info(f"Found repository data: {repo_info}")
            
            return AIProcessor(
                storage_manager=storage,
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
        except Exception as e:
            self.logger.error(f"Error initializing processor: {e}")
            st.error("Error initializing the application. Please check your configuration.")
            raise

    def render(self):
        """Render the main UI."""
        st.title("Whisper Repository Assistant 🤖")
        
        # Add data status indicator
        if hasattr(st.session_state, 'processor') and st.session_state.processor:
            try:
                repo_info = st.session_state.processor.storage.get_repository_info()
                if repo_info:
                    st.success("Repository data loaded successfully")
            except Exception as e:
                st.warning("Repository data may not be fully loaded")
        
        # Create two columns
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Chat interface
            self._render_chat_interface()
            
        with col2:
            # Code and documentation viewer
            self._render_code_viewer()

    def _render_chat_interface(self):
        """Render the chat interface."""
        # Display chat history
        for message in st.session_state.chat_history:
            self.chat_interface.display_message(
                message['role'],
                message['content']
            )

        # Query input
        query = st.text_input(
            "Ask a question about the Whisper repository:",
            key="query_input"
        )

        if st.button("Submit", key="submit_button"):
            if query:
                self._handle_query(query)

        # Display suggested queries
        if st.session_state.current_response:
            self._display_suggestions()

    def _render_code_viewer(self):
        """Render the code and documentation viewer."""
        if st.session_state.current_response:
            response = st.session_state.current_response
            
            # Display code snippets if available
            if 'code_snippets' in response:
                st.subheader("Code Snippets")
                for snippet in response['code_snippets']:
                    self.code_viewer.display_code(snippet)

            # Display sources
            if 'sources' in response:
                st.subheader("Sources")
                for source in response['sources']:
                    st.write(f"- {source['file']}")

    async def _process_query(self, query: str) -> Dict[str, Any]:
        """Process a query using the AI processor."""
        try:
            return await st.session_state.processor.process_query(query)
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return {
                'answer': "Sorry, I encountered an error processing your query. Please try again.",
                'error': str(e)
            }

    def _handle_query(self, query: str):
        """Handle a new query from the user with enhanced debugging."""
        try:
            # Verify processor and storage are initialized
            if not st.session_state.processor:
                st.error("Application not properly initialized. Please refresh the page.")
                return

            # Add user message to chat history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': query
            })

            # Create debug container
            with st.expander("Debug Information", expanded=True):
                # Process query with debug output
                with st.spinner('Processing your question...'):
                    response = asyncio.run(self._process_query(query))
                    
                    # Display debug info
                    if 'debug_info' in response:
                        st.write("Query Processing Information:")
                        st.json(response['debug_info'])
                    
                    if 'metadata' in response:
                        st.write("\nResponse Metadata:")
                        st.json(response['metadata'])
                    
                    if 'sources' in response:
                        st.write("\nSources Used:")
                        for source in response['sources']:
                            st.write(f"- {source['file']}")
                
                # Add assistant response to chat history
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response['answer']
                })
                
                # Store current response
                st.session_state.current_response = response

            # Rerun to update UI
            st.rerun()
            
        except Exception as e:
            self.logger.error(f"Error handling query: {e}")
            st.error("An error occurred while processing your query. Please try again.")
            st.write("Error details:", str(e))

    def _display_suggestions(self):
        """Display suggested follow-up questions."""
        try:
            if len(st.session_state.chat_history) < 2:
                return

            suggestions = st.session_state.processor.get_suggested_queries(
                st.session_state.chat_history[-2]['content']  # Get last user query
            )
            
            if suggestions:
                st.subheader("Suggested Questions")
                for suggestion in suggestions:
                    if st.button(suggestion, key=f"suggestion_{suggestion}"):
                        self._handle_query(suggestion)
        except Exception as e:
            self.logger.error(f"Error displaying suggestions: {e}")
            # Don't show error to user as this is not critical functionality