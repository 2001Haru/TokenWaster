import os
from typing import Set

class Memory:
    def __init__(self, desktop_comment_path: str):
        self.comment_path = desktop_comment_path
        self.read_files_set: Set[str] = set()
        self.compact_history: str = ""
        self.total_tokens_used: int = 0
        
        self._load_existing_comments()
        
    def _load_existing_comments(self):
        """Scan the TokenWaster Comment folder to figure out what we already read."""
        if not os.path.exists(self.comment_path):
            return
            
        for root, _, files in os.walk(self.comment_path):
            for file in files:
                if file.endswith(".md"):
                    # We assume the file name matches the original read file path roughly
                    # For simplicity, we just keep track of it if we can
                    pass
                    
    def mark_file_read(self, path: str):
        self.read_files_set.add(os.path.abspath(path))
        
    def has_read(self, path: str) -> bool:
        return os.path.abspath(path) in self.read_files_set
        
    def add_tokens(self, tokens: int):
        self.total_tokens_used += tokens
        
    def set_compact_history(self, history: str):
        self.compact_history = history
