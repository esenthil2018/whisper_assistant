# Whisper Repository AI Assistant

An intelligent AI assistant that helps developers understand and navigate code repositories, with a specific focus on OpenAI's Whisper project. This tool combines RAG (Retrieval Augmented Generation), vector storage, and GPT-4 to provide accurate, context-aware responses about repository content.

## 🚀 Features

### Core Capabilities
- **Intelligent Code Analysis**: Advanced parsing and understanding of Python codebases
- **Documentation Processing**: Handles markdown, docstrings, and inline comments
- **Smart Query Resolution**: Context-aware response generation using RAG
- **Interactive Interface**: User-friendly chat interface with code highlighting

### Technical Features
- **Advanced RAG Implementation**: Ensures accurate, context-based responses
- **Efficient Vector Storage**: Optimized semantic search using ChromaDB
- **Metadata Management**: SQLite-based structured data storage
- **Performance Optimization**: Smart caching and resource management

## 🛠️ Technology Stack

- **Python**: Core implementation language
- **OpenAI GPT-4**: Advanced language model for response generation
- **ChromaDB**: Vector storage for semantic search
- **SQLite**: Metadata and structured data storage
- **Streamlit**: User interface framework

## 📋 Prerequisites

- Python 3.8 or higher
- 4GB RAM minimum
- OpenAI API key
- Git (for repository cloning)

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/whisper-assistant.git
cd whisper-assistant

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Unix/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your OpenAI API key
```

## ⚙️ Configuration

1. Configure your OpenAI API key in `.env`:
```
OPENAI_API_KEY=your_api_key_here
```

2. Adjust application settings in `config/default.yaml`:
```yaml
app:
  name: "Whisper Repository AI Assistant"
  environment: "development"

storage:
  vector_store:
    path: "./data/embeddings"
  metadata_store:
    path: "./data/metadata.db"
```

## 🚀 Usage

```bash
# Run the setup script
python setup_whisper_assistant.py

# Start the application
streamlit run run.py
```

### Example Queries
- "Explain how the audio processing pipeline works"
- "Show me the main model architecture"
- "What environment variables are required?"
- "How does the tokenizer work?"

## 📁 Project Structure

```
whisper-assistant/
├── src/
│   ├── ai_processing/     # AI and RAG implementation
│   ├── data_ingestion/    # Repository processing
│   ├── storage/           # Data storage management
│   └── ui/               # User interface
├── config/               # Configuration files
├── data/                # Data storage
├── tests/               # Test suites
└── scripts/             # Utility scripts
```

## 🔍 Key Components

1. **Data Ingestion System**
   - Repository cloning and analysis
   - Code parsing and structure analysis
   - Documentation extraction

2. **Storage System**
   - Vector storage for semantic search
   - Metadata management
   - Caching system

3. **AI Processing Pipeline**
   - Query processing
   - Context retrieval
   - Response generation

4. **User Interface**
   - Chat interface
   - Code visualization
   - Response formatting

