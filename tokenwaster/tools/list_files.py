import os
import json

SCHEMA = {
    "name": "list_files",
    "description": "Allow the agent to see the sub-files or sub-folders in the given path. Note: only allow viewing of files exactly one level down.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the directory to list."
            }
        },
        "required": ["path"]
    }
}

def execute(path: str) -> str:
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return f"Error: Path not found at {path}"
    if not os.path.isdir(path):
        return f"Error: {path} is not a directory."
        
    try:
        items = []
        for entry in os.scandir(path):
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size_bytes": stat.st_size if entry.is_file() else 0
            })
            
        # Optional: Limit output size if directory is huge
        if len(items) > 500:
            truncated = items[:500]
            items_str = json.dumps(truncated, indent=2)
            return f"Showing first 500 items out of {len(items)}:\n{items_str}"
            
        return json.dumps(items, indent=2)
        
    except PermissionError:
        return f"Error: Permission denied accessing {path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"
