# Copy this content into src/data_ingestion/extractors/env_extractor.py
import re
from pathlib import Path
from typing import List, Dict
import logging

class EnvExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.env_patterns = [
            r'os\.environ\.get\(["\']([^"\']+)["\']',
            r'os\.getenv\(["\']([^"\']+)["\']',
            r'env\[["\']([^"\']+)["\']',
            r'ENV\[["\']([^"\']+)["\']',
            r'load_dotenv\(["\']([^"\']+)["\']'
        ]

    def extract_env_vars(self, file_path: Path) -> List[Dict]:
        """Extract environment variables from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            env_vars = []
            line_number = 0
            
            for line in content.split('\n'):
                line_number += 1
                for pattern in self.env_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        env_var = match.group(1)
                        env_vars.append({
                            'name': env_var,
                            'line_number': line_number,
                            'context': self._get_context(content, line_number),
                            'file_path': str(file_path),
                            'is_required': self._is_required(line),
                            'default_value': self._extract_default_value(line)
                        })

            # Also check for .env file references
            self._extract_env_file_vars(file_path, env_vars)
            
            return env_vars
        except Exception as e:
            self.logger.error(f"Error extracting env vars from {file_path}: {e}")
            return []

    def _get_context(self, content: str, line_number: int, context_lines: int = 2) -> str:
        """Get surrounding context for an environment variable usage."""
        lines = content.split('\n')
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        
        context_lines = lines[start:end]
        return '\n'.join(context_lines)

    def _is_required(self, line: str) -> bool:
        """Determine if the environment variable is required."""
        # Check for common patterns indicating required variables
        required_patterns = [
            r'required=True',
            r'raise\s+\w*Error',
            r'sys\.exit',
            r'assert'
        ]
        return any(re.search(pattern, line) for pattern in required_patterns)

    def _extract_default_value(self, line: str) -> str:
        """Extract default value if specified."""
        # Match common default value patterns
        default_match = re.search(r'get\([^,]+,\s*["\']([^"\']+)["\']\)', line)
        if default_match:
            return default_match.group(1)
        return None

    def _extract_env_file_vars(self, file_path: Path, env_vars: List[Dict]):
        """Extract variables from referenced .env files."""
        try:
            # Check for .env file in the same directory
            env_file = file_path.parent / '.env'
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key = line.split('=')[0].strip()
                                env_vars.append({
                                    'name': key,
                                    'source': '.env file',
                                    'file_path': str(env_file),
                                    'is_required': True,
                                    'default_value': None
                                })
        except Exception as e:
            self.logger.warning(f"Error reading .env file: {e}")

    def analyze_env_usage(self, env_vars: List[Dict]) -> Dict:
        """Analyze how environment variables are used."""
        analysis = {
            'total_vars': len(env_vars),
            'required_vars': len([var for var in env_vars if var['is_required']]),
            'vars_with_defaults': len([var for var in env_vars if var['default_value']]),
            'unique_vars': len(set(var['name'] for var in env_vars)),
            'files_with_env_vars': len(set(var['file_path'] for var in env_vars))
        }
        return analysis