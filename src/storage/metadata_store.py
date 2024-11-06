import sqlite3
from typing import Dict, List, Any
import logging
import json

class MetadataStore:
    def __init__(self, db_path: str, preserve_data: bool = True):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.preserve_data = preserve_data
        self._initialize_db()

    def _initialize_db(self):
        """Initialize the SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create tables if they don't exist (but don't drop them!)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS api_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        docstring TEXT,
                        parameters TEXT,
                        return_type TEXT,
                        file_path TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS env_variables (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE,
                        description TEXT,
                        is_required BOOLEAN,
                        default_value TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS repository_info (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # New table for setup info
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS setup_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE,
                        value TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                self.logger.info(f"Initialized database with tables: {[t[0] for t in tables]}")
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    def store_repository_data(self, data: Dict[str, Any]) -> bool:
        """Store complete repository data including all metadata."""
        try:
            # Store API metadata
            if 'apis' in data:
                self.store_api_metadata(data['apis'])
            
            # Store environment variables
            if 'env_vars' in data:
                self.store_env_variables(data['env_vars'])
            
            # Store repository info
            if 'repo_info' in data:
                repo_info = {
                    'stats': data['repo_info'].get('stats', {}),
                    'summaries': data['repo_info'].get('summaries', []),
                    'qa_pairs': data['repo_info'].get('qa_pairs', []),
                    'technical_concepts': data['repo_info'].get('technical_concepts', []),
                    'analysis_metadata': data['repo_info'].get('analysis_metadata', {})
                }
                self.store_repository_info(repo_info)
            
            # Store setup-specific info if available
            setup_info = self._extract_setup_info(data)
            if setup_info:
                self._store_setup_info(setup_info)
            
            return True
        except Exception as e:
            self.logger.error(f"Error storing repository data: {e}")
            raise

    def _extract_setup_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract setup-related information from repository data."""
        setup_info = {}
        try:
            if 'files' in data:
                for file in data['files']:
                    if file.get('path', '').endswith('setup.py'):
                        setup_info['setup_file'] = file
                        break
            
            if 'repo_info' in data and 'stats' in data['repo_info']:
                setup_info['repo_stats'] = data['repo_info']['stats']
            
            return setup_info
        except Exception as e:
            self.logger.error(f"Error extracting setup info: {e}")
            return {}

    def _store_setup_info(self, setup_info: Dict[str, Any]) -> bool:
        """Store setup-specific information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for key, value in setup_info.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO setup_info (key, value)
                        VALUES (?, ?)
                    """, (key, json.dumps(value)))
                
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error storing setup info: {e}")
            return False

    def store_api_metadata(self, apis: List[Dict[str, Any]]) -> bool:
        """Store API metadata in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for api in apis:
                    cursor.execute("""
                        INSERT INTO api_metadata (name, docstring, parameters, return_type, file_path)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        api.get('name', ''),
                        api.get('docstring', ''),
                        json.dumps(api.get('parameters', [])),
                        api.get('return_type', ''),
                        api.get('file_path', '')
                    ))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error storing API metadata: {e}")
            raise

    def store_env_variables(self, env_vars: List[Dict[str, Any]]) -> bool:
        """Store environment variables in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for var in env_vars:
                    cursor.execute("""
                        INSERT OR REPLACE INTO env_variables 
                        (name, description, is_required, default_value)
                        VALUES (?, ?, ?, ?)
                    """, (
                        var.get('name', ''),
                        var.get('description', ''),
                        var.get('is_required', False),
                        var.get('default_value', '')
                    ))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error storing env variables: {e}")
            raise

    def store_repository_info(self, info: Dict[str, Any]) -> bool:
        """Store repository information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clear existing data
                cursor.execute("DELETE FROM repository_info")
                
                # Store each piece of information
                for key, value in info.items():
                    self.logger.info(f"Storing repository info: {key}")
                    cursor.execute("""
                        INSERT INTO repository_info (key, value)
                        VALUES (?, ?)
                    """, (key, json.dumps(value)))
                
                conn.commit()
                
                # Verify storage
                cursor.execute("SELECT COUNT(*) FROM repository_info")
                count = cursor.fetchone()[0]
                self.logger.info(f"Stored {count} repository info entries")
                return True
        except Exception as e:
            self.logger.error(f"Error storing repository info: {e}")
            raise

    def get_repository_info(self) -> Dict[str, Any]:
        """Retrieve all repository information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM repository_info")
                results = {}
                for key, value in cursor.fetchall():
                    try:
                        results[key] = json.loads(value)
                    except Exception:
                        results[key] = value
                
                # Also get setup info
                cursor.execute("SELECT key, value FROM setup_info")
                setup_results = {}
                for key, value in cursor.fetchall():
                    try:
                        setup_results[key] = json.loads(value)
                    except Exception:
                        setup_results[key] = value
                
                if setup_results:
                    results['setup_info'] = setup_results
                
                return results
        except Exception as e:
            self.logger.error(f"Error retrieving repository info: {e}")
            return {}

    def get_api_metadata(self) -> List[Dict[str, Any]]:
        """Retrieve all API metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM api_metadata")
                rows = cursor.fetchall()
                return [{k: row[k] for k in row.keys()} for row in rows]
        except Exception as e:
            self.logger.error(f"Error retrieving API metadata: {e}")
            return []

    def get_env_variables(self) -> List[Dict[str, Any]]:
        """Retrieve all environment variables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM env_variables")
                rows = cursor.fetchall()
                return [{k: row[k] for k in row.keys()} for row in rows]
        except Exception as e:
            self.logger.error(f"Error retrieving env variables: {e}")
            return []

    def search_metadata(self, query: str) -> Dict[str, Any]:
        """Search through metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Search API metadata
                cursor.execute("""
                    SELECT * FROM api_metadata 
                    WHERE name LIKE ? OR docstring LIKE ?
                """, (f"%{query}%", f"%{query}%"))
                api_results = [{k: row[k] for k in row.keys()} for row in cursor.fetchall()]
                
                # Search setup info
                cursor.execute("""
                    SELECT * FROM setup_info 
                    WHERE value LIKE ?
                """, (f"%{query}%",))
                setup_results = [{k: row[k] for k in row.keys()} for row in cursor.fetchall()]
                
                return {
                    'apis': api_results,
                    'setup': setup_results
                }
        except Exception as e:
            self.logger.error(f"Error searching metadata: {e}")
            return {}