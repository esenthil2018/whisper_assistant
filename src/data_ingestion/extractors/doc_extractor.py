# src/data_ingestion/extractors/doc_extractor.py
import re
from pathlib import Path
from typing import List, Dict, Any
import ast
import logging
import json

class DocExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.markdown_extensions = ['.md', '.rst', '.txt']
        self.code_extensions = ['.py']

    def extract_documentation(self, file_path: Path) -> Dict[str, Any]:
        """Extract documentation from a file.
        
        Args:
            file_path: Path to the file to extract documentation from
            
        Returns:
            Dictionary containing the extracted documentation
        """
        try:
            if isinstance(file_path, str):
                file_path = Path(file_path)
                
            if file_path.suffix in self.markdown_extensions:
                return self._extract_markdown_doc(file_path)
            elif file_path.suffix in self.code_extensions:
                return self._extract_code_doc(file_path)
            else:
                self.logger.warning(f"Unsupported file type: {file_path.suffix}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error extracting documentation from {file_path}: {e}")
            return {}

    def _extract_code_doc(self, file_path: Path) -> Dict[str, Any]:
        """Extract documentation from Python code file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            # Get all class definitions in the file
            class_nodes = {
                node: None for node in ast.walk(tree) 
                if isinstance(node, ast.ClassDef)
            }

            # Extract documentation
            doc_info = {
                'file_path': str(file_path),
                'type': 'python_code',
                'content': self._format_content({
                    'module_docstring': ast.get_docstring(tree) or '',
                    'classes': [
                        {
                            'name': node.name,
                            'docstring': ast.get_docstring(node) or '',
                            'methods': self._extract_methods(node)
                        } 
                        for node in class_nodes
                    ],
                    'functions': [
                        {
                            'name': node.name,
                            'docstring': ast.get_docstring(node) or '',
                            'args': [arg.arg for arg in node.args.args],
                            'returns': self._get_return_type(node)
                        }
                        for node in ast.walk(tree)
                        if isinstance(node, ast.FunctionDef) 
                        and not any(node in ast.walk(class_def) 
                                  for class_def in class_nodes)
                    ],
                    'inline_comments': self._extract_inline_comments(content),
                    'todos': self._extract_todos(content)
                }),
                'metadata': {
                    'file_name': file_path.name,
                    'file_type': 'python',
                    'path': str(file_path)
                }
            }
            return doc_info
        except Exception as e:
            self.logger.error(f"Error extracting code documentation: {e}")
            return {}

    def _format_content(self, content_dict: Dict[str, Any]) -> str:
        """Format the documentation content into a single string."""
        sections = []
        
        # Add module docstring
        if content_dict['module_docstring']:
            sections.append(f"MODULE DOCUMENTATION:\n{content_dict['module_docstring']}\n")
        
        # Add classes and their methods
        for class_info in content_dict['classes']:
            sections.append(f"\nCLASS: {class_info['name']}")
            if class_info['docstring']:
                sections.append(f"Description:\n{class_info['docstring']}")
            
            for method in class_info['methods']:
                sections.append(f"\n  Method: {method['name']}")
                if method['docstring']:
                    sections.append(f"  Documentation:\n  {method['docstring']}")
        
        # Add standalone functions
        for func in content_dict['functions']:
            sections.append(f"\nFUNCTION: {func['name']}")
            if func['docstring']:
                sections.append(f"Documentation:\n{func['docstring']}")
        
        # Add TODOs if any
        if content_dict['todos']:
            sections.append("\nTODOs:")
            for todo in content_dict['todos']:
                sections.append(f"- {todo['content']}")
        
        return '\n'.join(sections)

    def _extract_methods(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract method documentation from a class."""
        methods = []
        for node in ast.iter_child_nodes(class_node):
            if isinstance(node, ast.FunctionDef):
                methods.append({
                    'name': node.name,
                    'docstring': ast.get_docstring(node) or '',
                    'args': [arg.arg for arg in node.args.args],
                    'returns': self._get_return_type(node)
                })
        return methods

    def _get_return_type(self, node: ast.FunctionDef) -> str:
        """Safely get return type annotation."""
        if hasattr(node, 'returns') and node.returns:
            try:
                return ast.unparse(node.returns)
            except Exception:
                pass
        return ''

    def _extract_inline_comments(self, content: str) -> List[Dict[str, Any]]:
        """Extract inline comments from code."""
        return [
            {'line': i + 1, 'content': m.group(1).strip()}
            for i, line in enumerate(content.splitlines())
            if (m := re.match(r'.*#\s*(.+)$', line))
        ]

    def _extract_todos(self, content: str) -> List[Dict[str, Any]]:
        """Extract TODO comments."""
        return [
            {'line': i + 1, 'content': line.split('TODO:', 1)[1].strip()}
            for i, line in enumerate(content.splitlines())
            if 'TODO:' in line
        ]

    def _extract_markdown_doc(self, file_path: Path) -> Dict[str, Any]:
        """Extract documentation from markdown files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return {
                'file_path': str(file_path),
                'type': 'markdown',
                'content': content,
                'metadata': {
                    'file_name': file_path.name,
                    'file_type': 'markdown',
                    'path': str(file_path)
                }
            }
        except Exception as e:
            self.logger.error(f"Error extracting markdown documentation: {e}")
            return {}