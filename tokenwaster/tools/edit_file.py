import os

SCHEMA = {
    "name": "edit_file",
    "description": "Allow the agent to edit the files under the folder 'TokenWaster Comment' on the user's desktop. Need a path and content to operate. If there's no such file to be operated, create one.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file to create or edit."
            },
            "content": {
                "type": "string",
                "description": "The Markdown string content to write."
            }
        },
        "required": ["path", "content"]
    }
}

def execute(path: str, content: str) -> str:
    from tokenwaster.config import get_desktop_path
    
    desktop_comment_path = get_desktop_path()
    
    # Ensure the comment folder exists
    os.makedirs(desktop_comment_path, exist_ok=True)
    
    target_path = os.path.abspath(path)
    
    # Secure check: only allow writing inside the TokenWaster Comment folder
    if not target_path.startswith(desktop_comment_path):
        return f"SECURITY ERROR: You are ONLY allowed to write files inside '{desktop_comment_path}'. Access to '{target_path}' denied."
        
    try:
        # Create subdirectories if needed
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Successfully wrote {len(content)} characters to {target_path}"
        
    except Exception as e:
        return f"Error editing file: {str(e)}"
