import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def generate_caption(video_info, user_keyword=None):
    """
    Generates a viral caption for a short video using the Gemini API.
    
    Args:
        video_info (dict): A dictionary containing video details like duration.
        user_keyword (str, optional): A keyword provided by the user.
    
    Returns:
        str: The generated caption.
    """
    duration = video_info.get("duration", "30")
    
    prompt = f"""
    You're an AI shorts caption creator. The user sent a {duration}-second clip. 
    Give a viral caption under 80 characters, emotional and trendy. 
    """
    
    if user_keyword:
        prompt += f"Include this keyword if relevant: {user_keyword}."
    
    prompt += " Respond only with the final caption."
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating caption with Gemini: {e}")
        return "Check out this awesome short!"

if __name__ == '__main__':
    # Example usage
    example_video_info = {"duration": 30}
    caption = generate_caption(example_video_info)
    print(f"Generated Caption: {caption}")
  
