# src/ui/components/code_viewer.py
import streamlit as st
from typing import Optional, List, Dict, Any
import logging

class CodeViewer:
    """Code and documentation viewer component."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def display_code(
        self,
        code: str,
        language: str = "python",
        title: Optional[str] = None,
        show_copy_button: bool = True
    ):
        """Display code with syntax highlighting."""
        container = st.container()
        
        with container:
            if title:
                st.markdown(f"**{title}**")
            
            # Display code
            st.code(code, language=language)
            
            # Add copy button
            if show_copy_button:
                if st.button("📋 Copy Code", key=f"copy_{hash(code)}"):
                    st.toast("Code copied to clipboard! ✅")

    def display_documentation(
        self,
        content: str,
        title: Optional[str] = None,
        show_toc: bool = False
    ):
        """Display documentation with formatting."""
        with st.container():
            if title:
                st.markdown(f"## {title}")
            
            if show_toc:
                toc = self._generate_toc(content)
                with st.expander("Table of Contents"):
                    st.markdown(toc)
            
            st.markdown(content)

    def display_api_reference(self, api_details: Dict[str, Any]):
        """Display API reference documentation."""
        with st.container():
            st.markdown("## API Reference")
            
            for name, details in api_details.items():
                with st.expander(f"📚 {name}"):
                    # Display docstring
                    if details.get('docstring'):
                        st.markdown(details['docstring'])
                    
                    # Display parameters
                    if details.get('parameters'):
                        st.markdown("### Parameters")
                        for param in details['parameters']:
                            st.markdown(f"- `{param['name']}`: {param.get('type', 'Any')}")
                    
                    # Display return type
                    if details.get('return_type'):
                        st.markdown(f"### Returns\n`{details['return_type']}`")
                    
                    # Display examples
                    if details.get('examples'):
                        st.markdown("### Examples")
                        for example in details['examples']:
                            st.code(example, language='python')

    def _generate_toc(self, content: str) -> str:
        """Generate table of contents from markdown content."""
        toc = []
        for line in content.split('\n'):
            if line.startswith('#'):
                level = line.count('#')
                title = line.strip('#').strip()
                indent = '  ' * (level - 1)
                toc.append(f"{indent}- [{title}](#{title.lower().replace(' ', '-')})")
        return '\n'.join(toc)

    def display_file_tree(self, files: List[Dict[str, Any]]):
        """Display repository file tree."""
        st.markdown("## Repository Structure")
        
        for file in files:
            with st.expander(f"📄 {file['path']}"):
                if file.get('content'):
                    self.display_code(file['content'])
                if file.get('documentation'):
                    st.markdown(file['documentation'])