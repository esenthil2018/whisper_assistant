# src/data_ingestion/code_parser.py
import ast
from typing import Dict, List, Any
from pathlib import Path
import logging
import tokenize
import io

class CodeParser:  # Keep the original name for backward compatibility
    """Enhanced code parser with improved extraction capabilities."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a Python file and extract comprehensive information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Store raw content for context
            raw_content = content
            
            # Parse AST
            tree = ast.parse(content)
            
            return {
                'raw_content': raw_content,
                'file_path': str(file_path),
                'functions': self._extract_functions(tree),
                'classes': self._extract_classes(tree),
                'imports': self._extract_imports(tree),
                'docstring': ast.get_docstring(tree),
                'comments': self._extract_comments(content),
                'structure': self._extract_structure(tree)
            }
        except Exception as e:
            self.logger.error(f"Error parsing file {file_path}: {e}")
            return {}

    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract function definitions with enhanced context."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                try:
                    source_lines = ast.get_source_segment(tree.body[0], node)
                except:
                    source_lines = None
                    
                functions.append({
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'args': [arg.arg for arg in node.args.args],
                    'returns': self._get_return_annotation(node),
                    'body': source_lines,
                    'decorators': [ast.unparse(d) for d in node.decorator_list],
                    'line_number': node.lineno,
                    'context': self._get_function_context(node)
                })
        return functions

    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract class definitions with enhanced context."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'methods': self._extract_methods(node),
                    'bases': [ast.unparse(base) for base in node.bases],
                    'decorators': [ast.unparse(d) for d in node.decorator_list],
                    'attributes': self._extract_class_attributes(node)
                })
        return classes

    def _extract_methods(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract methods from a class with implementation details."""
        methods = []
        for node in ast.walk(class_node):
            if isinstance(node, ast.FunctionDef):
                try:
                    source_lines = ast.get_source_segment(class_node, node)
                except:
                    source_lines = None
                    
                methods.append({
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'args': [arg.arg for arg in node.args.args],
                    'returns': self._get_return_annotation(node),
                    'body': source_lines,
                    'decorators': [ast.unparse(d) for d in node.decorator_list]
                })
        return methods

    def _extract_comments(self, content: str) -> List[Dict[str, str]]:
        """Extract comments with their context."""
        comments = []
        try:
            for token in tokenize.generate_tokens(io.StringIO(content).readline):
                if token.type == tokenize.COMMENT:
                    comments.append({
                        'text': token.string.lstrip('#').strip(),
                        'line': token.start[0],
                        'context': self._get_comment_context(content, token.start[0])
                    })
        except Exception as e:
            self.logger.error(f"Error extracting comments: {e}")
        return comments

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements with full context."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(n.name for n in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                imports.extend(f"{module}.{n.name}" for n in node.names)
        return imports

    def _get_return_annotation(self, node: ast.FunctionDef) -> str:
        """Get the return type annotation if it exists."""
        if node.returns:
            return ast.unparse(node.returns)
        return None

    def _get_function_context(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Get the context surrounding a function definition."""
        return {
            'line_start': node.lineno,
            'line_end': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            'col_offset': node.col_offset,
            'is_method': isinstance(node.parent, ast.ClassDef) if hasattr(node, 'parent') else False
        }

    def _get_comment_context(self, content: str, line_number: int, context_lines: int = 2) -> str:
        """Get context around a comment."""
        lines = content.split('\n')
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        return '\n'.join(lines[start:end])

    def _extract_class_attributes(self, node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract class attributes including type annotations."""
        attributes = []
        for body_item in node.body:
            if isinstance(body_item, ast.AnnAssign):
                attributes.append({
                    'name': ast.unparse(body_item.target),
                    'type': ast.unparse(body_item.annotation) if body_item.annotation else None,
                    'value': ast.unparse(body_item.value) if body_item.value else None
                })
        return attributes

    def _extract_structure(self, tree: ast.AST) -> Dict[str, Any]:
        """Extract the overall structure of the code."""
        return {
            'functions': self._extract_functions(tree),
            'classes': self._extract_classes(tree),
            'imports': self._extract_imports(tree),
            'module_docstring': ast.get_docstring(tree)
        }