from setuptools import setup, find_packages

setup(
    name="whisper-assistant",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.24.0,<2.0.0",
        "chromadb>=0.5.17",    # Keep current version
        "openai>=1.0.0",       # Allow newer versions
        "GitPython==3.1.31",
        "langchain==0.0.300",
        "python-dotenv==1.0.0",
        "beautifulsoup4==4.12.2",
        "redis==4.5.4",
        "pytest==7.3.1",
        "tenacity>=8.2.3",
        "grpcio==1.67.1",
        "chroma-hnswlib==0.7.6",
    ],
)