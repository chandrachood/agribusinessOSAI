
import os
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

async def test_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    model_id = os.environ.get("GEMINI_MODEL_ID", "gemini-flash-lite-latest")
    
    print(f"Testing Gemini API with key length: {len(api_key) if api_key else 0}")
    print(f"Model ID: {model_id}")
    
    if not api_key:
        print("Error: No API Key found")
        return

    client = genai.Client(api_key=api_key)
    
    try:
        print("Sending request...")
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="Hello, are you there?")]
            )
        ]
        
        # Test synchronous stream first as used in the app
        response_stream = client.models.generate_content_stream(
            model=model_id,
            contents=contents,
        )
        
        print("Stream started...")
        for chunk in response_stream:
            print(f"Chunk received: {chunk.text}")
            
        print("Stream finished successfully.")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini())
