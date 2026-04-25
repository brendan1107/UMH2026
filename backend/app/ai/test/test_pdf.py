# app/ai/test/test_pdf.py
import asyncio, sys
from pathlib import Path
import PyPDF2

# Setup paths and environment variables
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

async def test_pdf_analysis():
    from app.ai.glm_client import glm_call
    
    print("═══ TESTING GEMINI PDF ANALYSIS (LOCAL FILE) ═══")
    
    # 1. READ A LOCAL PDF FILE
    pdf_path = "test_doc.pdf" 
    
    try:
        print(f"Reading local PDF file: {pdf_path}...")
        reader = PyPDF2.PdfReader(pdf_path)
        # Extract text from all pages
        extracted_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except FileNotFoundError:
        print(f"❌ ERROR: I cannot find '{pdf_path}'! Please save a dummy PDF with that name in your backend folder.")
        return
    except Exception as e:
        print(f"❌ ERROR reading PDF: {e}")
        return
        
    print(f"Successfully extracted {len(extracted_text)} characters from the PDF. Sending to AI...\n")
    
    # 2. Package the message using the extracted text
    messages = [
        {
            "role": "user",
            "content": f"Task completed. Here is the text extracted from the uploaded PDF document. Please analyze it, summarize the key points, and look for any financial numbers (like rent, costs, or prices).\n\n[Extracted Text]:\n{extracted_text[:10000]}"
        }
    ]
    
    # 3. Use our ultra-strict system prompt to prevent Pydantic crashes
    system_prompt = """You are F&B Genie's Document Agent. 
    You MUST output valid JSON only. 
    You are STRICTLY REQUIRED to include all 4 of these exact keys in your JSON response. Do not miss any:
    
    1. "type" (must be exactly "field_task")
    2. "title" (must be exactly "PDF Document Analysis")
    3. "instruction" (your detailed analysis of the document text)
    4. "evidence_type" (must be exactly "text")
    """
    
    try:
        output = await glm_call(messages, system_prompt)
        
        print("✅ PDF TEST PASSED!")
        print("Here is what the AI extracted and analyzed from your PDF:\n")
        print(f"\"{output.instruction}\"")
        
    except Exception as e:
        print(f"❌ PDF TEST FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_pdf_analysis())