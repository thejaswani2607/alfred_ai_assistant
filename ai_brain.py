import os
from google import genai
from google.genai import types

class AIBrain:
    def __init__(self):
        # Initialize the client with automatic retry logic for 503 and 429 errors
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY"),
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=4,
                    initial_delay=1.0,
                    http_status_codes=[429, 500, 503, 504]
                )
            )
        )
        
        # Establish a continuous memory session with our updated client
        self.chat_session = self.client.chats.create(
            model="gemini-3.8-flash",
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are Alfred, a helpful AI assistant. "
                    "Analyze the user's prompt and determine their intent.\n"
                    "1. If they want to play a specific song, respond EXACTLY with: CMD_PLAY: <song name>\n"
                    "2. If they want to hear the news, respond EXACTLY with: CMD_NEWS\n"
                    "3. If they want to open a website, respond EXACTLY with: CMD_OPEN: <website name>\n"
                    "4. If they want to lock the computer, respond EXACTLY with: CMD_LOCK\n"
                    "5. If they want to mute or unmute the volume, respond EXACTLY with: CMD_MUTE\n"
                    "6. If it is none of the above, answer their question naturally in 1 or 2 short sentences. Do not use asterisks or formatting."
                )
            )
        )

    def process_input(self, user_input):
        print("\n[Alfred is thinking...]")
        try:
            response = self.chat_session.send_message(user_input)
            reply = response.text.strip()
            print(f"[Alfred generated]: {reply}")
            return reply
        except Exception as e:
            # Print the exact error to the terminal, but return a friendly vocal string
            print(f"AI Error: {e}")
            return "I'm sorry, the Google servers are currently overloaded. Please try again in a moment."