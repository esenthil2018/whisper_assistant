# Copy this content into src/data_ingestion/extractors/api_extractor.py
from pathlib import Path
import ast
from typing import List, Dict
import logging

class APIExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_apis(self, file_path: Path) -> List[Dict]:
        """Extract API-like functions and methods from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            apis = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Look for public methods and functions
                    if not node.name.startswith('_'):
                        api = self._process_function(node)
                        if api:
                            apis.append(api)
            return apis
        except Exception as e:
            self.logger.error(f"Error extracting APIs from {file_path}: {e}")
            return []

    def _process_function(self, node: ast.FunctionDef) -> Dict:
        """Process a function node and extract API-relevant information."""
        return {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'parameters': self._get_parameters(node),
            'return_type': self._get_return_type(node),
            'decorators': self._get_decorators(node)
        }

    def _get_parameters(self, node: ast.FunctionDef) -> List[Dict]:
        """Extract parameter information from function."""
        params = []
        for arg in node.args.args:
            param = {
                'name': arg.arg,
                'type': ast.unparse(arg.annotation) if arg.annotation else None
            }
            params.append(param)
        return params

    def _get_return_type(self, node: ast.FunctionDef) -> str:
        """Get return type annotation if it exists."""
        if node.returns:
            return ast.unparse(node.returns)
        return None

    def _get_decorators(self, node: ast.FunctionDef) -> List[str]:
        """Extract decorator information."""
        return [ast.unparse(dec) for dec in node.decorator_list]