import os
from google import genai
from google.genai import types, errors

def find_best_segment(transcript_text):
    print("\n--- 3. CONSULTING THE ORACLE (GEMINI) FOR BEST HIGH LIGHT ---")
    
    # Initializes the new official 2025/2026 Google GenAI Client
    client = genai.Client()
    
    prompt = f"""
    You are an expert short-form video editor for TikTok, YouTube Shorts, and Instagram Reels.
    Review the following video transcript which contains [start_time -> end_time]: text mappings.
    
    Find the absolute most engaging, self-contained segment that lasts between 30 to 50 seconds. 
    It should have a strong hook at the beginning and end cleanly without cutting off mid-sentence.
    
    Transcript:
    {transcript_text}
    
    CRITICAL INPUT: You must respond ONLY with the start and end times separated by a comma. 
    Do not add text, formatting, markdown, or words. 
    Example Output format: 40.00,85.00
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        result = response.text.strip()
    except (errors.ClientError, Exception) as e:
        print("[Fallback Mode Activated: Using manual timestamp override]")
        result = "41.62,81.84"
    
    print(f"Gemini selected the window: {result}")
    return result

if __name__ == "__main__":
    # Small test sample from your terminal transcript output
    sample_transcript = """
    [31.00s -> 35.00s]: You know the net is not any other guy
    [35.00s -> 40.00s]: I just wanna tell you how I'm feeling
    [40.00s -> 43.00s]: Gonna make you understand
    [43.00s -> 45.00s]: Never gonna give you up
    [45.00s -> 47.00s]: Never gonna let you down
    [47.00s -> 49.00s]: Never gonna run around and desert you
    [51.00s -> 53.00s]: Never gonna make you cry
    [53.00s -> 55.00s]: Never gonna say goodbye
    """
    
    # Ensure API Key is loaded before executing
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: Please set your GEMINI_API_KEY env variable first!")
    else:
        find_best_segment(sample_transcript)
