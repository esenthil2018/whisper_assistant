# src/ui/main.py
import os
import streamlit as st
from pathlib import Path
import logging
from dotenv import load_dotenv
from src.ui.app import WhisperAssistantUI

# Set page configuration first
st.set_page_config(
    page_title="Whisper Repository Assistant",
    page_icon="🤖",
    layout="wide"
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('whisper_assistant.log')
    ]
)

logger = logging.getLogger(__name__)

def setup_environment():
    """Setup necessary environment and directories."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Create necessary directories
        directories = [
            './data/embeddings',
            './data/raw',
            './data/processed',
            './logs'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
        # Verify required environment variables
        required_vars = ['OPENAI_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        logger.info("Environment setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up environment: {e}")
        return False

def main():
    """Main application entry point."""
    try:
        # Setup environment
        if not setup_environment():
            raise RuntimeError("Failed to setup environment")
        
        # Initialize and run the UI
        app = WhisperAssistantUI()
        app.render()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error("An error occurred while starting the application. Please check the logs.")
        raise

if __name__ == "__main__":
    main()