# app/ai/test/test_vision.py
import asyncio, sys, base64
from pathlib import Path

# Setup paths and environment variables
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

async def test_image_analysis():
    from app.ai.glm_client import glm_call
    
    print("═══ TESTING GEMINI VISION (LOCAL FILE) ═══")
    
    # 1. READ A LOCAL FILE INSTEAD OF THE INTERNET
    image_path = "test_photo.jpg" 
    
    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
    except FileNotFoundError:
        print(f"❌ ERROR: I cannot find '{image_path}'! Please save an image with that name in your backend folder.")
        return
        
    # 2. Convert to Base64 Data URI
    base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
    data_uri = f"data:image/jpeg;base64,{base64_encoded}"
    
    print("Local image converted to Base64. Sending directly to AI's eyes...\n")
    
    # 3. Package the message using the Data URI
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": "Look closely at this photo. Describe the setting, the items, and the general vibe. Return your analysis inside the 'instruction' field."
                },
                {
                    "type": "image_url", 
                    "image_url": {"url": data_uri}
                }
            ]
        }
    ]
    
    # 4. Strict system prompt forcing all 4 required fields
    system_prompt = """You are F&B Genie's Vision Agent. 
    You MUST output valid JSON only. 
    You are STRICTLY REQUIRED to include all 4 of these exact keys in your JSON response. Do not miss any:
    
    1. "type" (must be exactly "field_task")
    2. "title" (must be exactly "Vision Analysis")
    3. "instruction" (your detailed description of the image)
    4. "evidence_type" (must be exactly "text")

    Example Perfect Output:
    {"type": "field_task", "title": "Vision Analysis", "instruction": "I see a modern bakery...", "evidence_type": "text"}
    """
    
    try:
        output = await glm_call(messages, system_prompt)
        
        print("✅ VISION TEST PASSED!")
        print("Here is what the AI saw in your local photo:\n")
        print(f"\"{output.instruction}\"")
        
    except Exception as e:
        print(f"❌ VISION TEST FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_image_analysis())