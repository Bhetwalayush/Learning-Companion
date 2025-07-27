"""
Install the Google AI Python SDK

$ pip install google-generativeai

See the getting started guide for more information:
https://ai.google.dev/gemini-api/docs/get-started/python
"""

import os
import google.generativeai as genai
from main import text_to_speech

from dotenv import load_dotenv
load_dotenv()


# Configure the API key without printing it
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create the model
# See https://ai.google.dev/api/python/google/generativeai/GenerativeModel
generation_config = {
  "temperature": 0.9,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2000,
  "response_mime_type": "text/plain",
}
safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE",
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
  },
]

model = genai.GenerativeModel(
  model_name="gemini-2.5-flash",
  safety_settings=safety_settings,
  generation_config=generation_config,
  system_instruction="You are an AI learning companion for children aged 5 to 16. Your job is to make learning fun, personalized, and easy to understand .You engage in conversations on topics like science, math, reading, and problem-solving. Use friendly, age-appropriate language, analogies, and interactive questions to explain concepts.Encourage curiosity, provide emotional support when kids are frustrated, and celebrate their progress with praise. If a child gets confused, explain things in different ways until they understand.Always keep things fun, supportive, and helpful! Explain scientific concepts so that they are easily understandable. Use analogies and examples that are relatable. Use humor and make the conversation both educational and interesting. Ask questions so that you can better understand the user and improve the educational experience. Suggest way that these concepts can be related to the real world with observations and experiments.",
)



chat_session = model.start_chat(
    history=[]
)

print("Bot: Hello, how can I help you?")
print()
text_to_speech("Hello, how can I help you?")
import re

def clean_text_for_speech(text):
    # Remove emojis and special characters using regex
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002700-\U000027BF"  # Dingbats
        u"\U000024C2-\U0001F251"  # Enclosed characters
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

while True:

    user_input = input("You: ")
    print()

    response = chat_session.send_message(user_input)

    model_response = response.text

    print(f'Bot: {model_response}')
    print()
    clean_response = clean_text_for_speech(model_response)
    text_to_speech(clean_response)

    # These lines are correctly commented out, preventing the rate-limit error.
    # chat_session.history.append({"role": "user", "parts": [user_input]})
    # chat_session.history.append({"role": "model", "parts": [model_response]})