import os
import json
from typing import Set

class Memory:
    def __init__(self, desktop_comment_path: str):
        self.comment_path = desktop_comment_path
        self.memory_file = os.path.join(desktop_comment_path, ".tokenwaster_memory.json")
        self.read_files_set: Set[str] = set()
        self.compact_history: str = ""
        self.total_tokens_used: int = 0
        
        self._load_memory()
        
    def _load_memory(self):
        """Load memory from JSON file if it exists."""
        if not os.path.exists(self.comment_path):
            os.makedirs(self.comment_path, exist_ok=True)
            
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.read_files_set = set(data.get("read_files", []))
                    self.compact_history = data.get("compact_history", "")
                    self.total_tokens_used = data.get("total_tokens_used", 0)
            except Exception:
                pass

    def _save_memory(self):
        """Save current memory state to JSON."""
        if not os.path.exists(self.comment_path):
            os.makedirs(self.comment_path, exist_ok=True)
            
        data = {
            "read_files": list(self.read_files_set),
            "compact_history": self.compact_history,
            "total_tokens_used": self.total_tokens_used
        }
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
                    
    def mark_file_read(self, path: str):
        self.read_files_set.add(os.path.abspath(path))
        self._save_memory()
        
    def has_read(self, path: str) -> bool:
        return os.path.abspath(path) in self.read_files_set
        
    def add_tokens(self, tokens: int):
        self.total_tokens_used += tokens
        self._save_memory()
        
    def set_compact_history(self, history: str):
        self.compact_history = history
        self._save_memory()
