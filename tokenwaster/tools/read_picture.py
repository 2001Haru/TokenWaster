import os
import base64

SCHEMA = {
    "name": "read_picture",
    "description": "Allow the agent to read pictures. Converts to base64 for vision-capable models.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the image file."
            }
        },
        "required": ["path"]
    }
}

def execute(path: str, multimodal: bool = True) -> str:
    if not multimodal:
        return "Error: Current model configuration does not support image reading (multimodal = false)."
        
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return f"Error: File not found at {path}"
        
    try:
        from PIL import Image
        import io
        
        # Verify it's an image
        with Image.open(path) as img:
            format = img.format.lower() if img.format else "jpeg"
            # Ensure format is supported by standard APIs
            if format not in ["jpeg", "jpg", "png", "webp", "gif"]:
                format = "jpeg"
                
            # Resize if too large to save tokens / payload size
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format=format)
            img_byte = buffered.getvalue()
            b64_str = base64.b64encode(img_byte).decode("utf-8")
            
            # Note: The tool shouldn't return the raw base64 string to the LLM as text output,
            # because the LLM would just see a massive string instead of an image.
            # Instead, we should ideally inject this into the message history as an image content.
            # However, standard function calling returns a string. 
            # We return a special token/marker and the agent logic can intercept this and inject the image.
            
            # Here we return a JSON wrapper that the agent main loop will intercept.
            import json
            payload = {
                "__type__": "image",
                "mime_type": f"image/{format}",
                "base64_data": b64_str,
                "info": f"Loaded image {img.width}x{img.height}"
            }
            return json.dumps(payload)
            
    except Exception as e:
        return f"Error reading picture: {str(e)}"
