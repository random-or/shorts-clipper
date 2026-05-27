import os
import re

from google import genai
from google.genai import errors


def find_best_segment(transcript_text):
    print("\n--- 3. CONSULTING THE ORACLE (GEMINI) FOR BEST HIGH LIGHT ---")
    
    # Initializes the official Google GenAI Client
    client = genai.Client()
    
    prompt = (
        f"Analyze the following video transcript:\n\n{transcript_text}\n\n"
        "Your task: Identify the single highest-energy, most viral-worthy "
        "30-to-45 second hook suitable for Instagram Reels. "
        "Focus on sections with high engagement potential, clear emotional "
        "peaks, or self-contained interesting stories. "
        "Evaluate the transcript context and choose the most engaging framing "
        "strategy from these options: 'crop_center', 'crop_left', "
        "'crop_right', 'split_screen'. "
        "Return ONLY the start timestamp, end timestamp, and the framing "
        "strategy in raw, comma-separated format (e.g., 580.0,615.0,crop_center). "
        "Do NOT include any other text, labels, or formatting."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        result = response.text.strip()
        # Ensure we only have the numbers and layout, comma-separated
        match = re.search(r"(\d+\.?\d*,\s*\d+\.?\d*,\s*[a-zA-Z_]+)", result)
        if match:
            result = match.group(1).replace(" ", "")
        else:
            raise ValueError(f"Invalid format returned: {result}")
            
    except (errors.ClientError, ValueError, Exception) as e:
        print(f"[Fallback Mode Activated due to error: {e}]")
        # Use a sensible fallback window and layout if Gemini fails
        result = "60.0,95.0,crop_center"
    
    print(f"Gemini selected the window and layout: {result}")
    return result

if __name__ == "__main__":
    # Ensure API Key is loaded before executing
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: Please set your GEMINI_API_KEY env variable first!")
    else:
        test_transcript = (
            "[10.0s - 15.0s] Hello world. "
            "[60.0s - 100.0s] This is a viral moment that everyone should see."
        )
        print(find_best_segment(test_transcript))
