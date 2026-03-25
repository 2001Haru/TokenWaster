import os

SCHEMA = {
    "name": "read_files",
    "description": "Allow the agent to read any file, allowing to specify the starting line and the ending line.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file to read."
            },
            "start_line": {
                "type": "integer",
                "description": "The line number to start reading from (1-indexed). Optional."
            },
            "end_line": {
                "type": "integer",
                "description": "The line number to stop reading at (1-indexed). Optional."
            }
        },
        "required": ["path"]
    }
}

def execute(path: str, start_line: int | None = None, end_line: int | None = None) -> str:
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return f"Error: File not found at {path}"
    if not os.path.isfile(path):
        return f"Error: {path} is not a file."
        
    try:
        # Prevent reading huge files completely at once if no lines specified
        # or binary files
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        start_idx = max(0, start_line - 1) if start_line else 0
        end_idx = min(total_lines, end_line) if end_line else total_lines
        
        # Limit max lines to prevent token explosion
        MAX_LINES = 2000
        if end_idx - start_idx > MAX_LINES:
            end_idx = start_idx + MAX_LINES
            truncation_msg = f"\n[Output truncated at {MAX_LINES} lines to preserve tokens]"
        else:
            truncation_msg = ""
            
        selected_lines = lines[start_idx:end_idx]
        content = "".join(selected_lines)
        return f"Showing lines {start_idx + 1} to {end_idx} of {total_lines}:\n\n{content}{truncation_msg}"
        
    except UnicodeDecodeError:
        return f"Error: File at {path} appears to be binary or not utf-8 encoded."
    except Exception as e:
        return f"Error reading file: {str(e)}"
