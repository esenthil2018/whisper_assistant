# src/data_ingestion/repo_crawler.py
import os
import git
from pathlib import Path
from typing import Optional, List
import logging

class RepoCrawler:
    """Handle repository cloning and file crawling."""
    
    def __init__(self, repo_url: str, local_path: str):
        self.repo_url = repo_url
        self.local_path = Path(local_path)
        self.logger = logging.getLogger(__name__)

    def clone_repo(self) -> Optional[git.Repo]:
        """Clone the repository if it doesn't exist."""
        try:
            if not self.local_path.exists():
                self.logger.info(f"Cloning repository from {self.repo_url}")
                self.local_path.parent.mkdir(parents=True, exist_ok=True)
                return git.Repo.clone_from(self.repo_url, str(self.local_path))
            else:
                self.logger.info("Repository already exists locally")
                return git.Repo(str(self.local_path))
        except git.GitCommandError as e:
            self.logger.error(f"Git command error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error cloning repository: {e}")
            return None

    def update_repo(self) -> bool:
        """Update the local repository to the latest version."""
        try:
            repo = git.Repo(str(self.local_path))
            current = repo.head.commit
            repo.remotes.origin.pull()
            if current != repo.head.commit:
                self.logger.info("Repository updated successfully")
                return True
            self.logger.info("Repository already up to date")
            return True
        except Exception as e:
            self.logger.error(f"Error updating repository: {e}")
            return False

    def get_file_list(self, file_types: Optional[List[str]] = None) -> List[str]:
        """Get list of files in the repository."""
        if file_types is None:
            file_types = ['.py''.md', '.txt']
            
        try:
            files = []
            for file_type in file_types:
                files.extend(
                    str(f.relative_to(self.local_path))
                    for f in self.local_path.rglob(f"*{file_type}")
                    if not any(part.startswith('.') for part in f.parts)
                )
            return files
        except Exception as e:
            self.logger.error(f"Error getting file list: {e}")
            return []