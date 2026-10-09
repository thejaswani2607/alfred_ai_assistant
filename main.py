import os
# This strictly hides the Pygame welcome message.
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import speech_recognition as sr
import webbrowser
import musicLibrary
import requests
from google import genai
from google.genai import types
from gtts import gTTS
import pygame
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

recognizer = sr.Recognizer()
newsapi = os.getenv("NEWS_API_KEY")

# Initialize Pygame mixer ONCE at the start to prevent file locking issues
pygame.mixer.init()

def speak(text):
    try:
        tts = gTTS(text)
        tts.save('temp.mp3') 

        # Load the MP3 file
        pygame.mixer.music.load('temp.mp3')

        # Play the MP3 file
        pygame.mixer.music.play()

        # Keep the program running until the music stops playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        pygame.mixer.music.unload()
        os.remove("temp.mp3") 
    except Exception as e:
        print(f"Audio playback error: {e}")

def aiProcess(command):
    print("\n[Alfred is thinking...]")
    # Initialize the new Gemini client
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Generate the response using the updated 3.8 model
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=command,
        config=types.GenerateContentConfig(
            # TIGHTENED SYSTEM INSTRUCTION: Forces 1-2 sentence answers to prevent massive delays
            system_instruction="You are a helpful virtual assistant named Alfred. ALWAYS answer in 1 or 2 short sentences. Do not use asterisks or formatting."
        )
    )

    print(f"[Alfred generated]: {response.text}")
    return response.text

def processCommand(c):
    if "open google" in c.lower():
        webbrowser.open("https://google.com")
    elif "open facebook" in c.lower():
        webbrowser.open("https://facebook.com")
    elif "open youtube" in c.lower():
        webbrowser.open("https://youtube.com")
    elif "open linkedin" in c.lower():
        webbrowser.open("https://linkedin.com")
        
    elif c.lower().startswith("play"):
        song = " ".join(c.lower().split(" ")[1:])
        
        if song in musicLibrary.music:
            link = musicLibrary.music[song]
            webbrowser.open(link)
        else:
            speak(f"I couldn't find {song} in your music library.")

    elif "news" in c.lower():
        # Add a User-Agent header so News API doesn't block the Python request
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={newsapi}"
        
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            data = r.json()
            articles = data.get('articles', [])
            
            if not articles:
                print("\n[Alfred generated]: I couldn't find any news articles right now.")
                speak("I couldn't find any news articles right now.")
            else:
                print("\n[Alfred generated]: Here are the top headlines.")
                speak("Here are the top headlines.")
                # Limit to the first 5 articles so it doesn't talk forever
                for i, article in enumerate(articles[:5], 1):
                    if article.get('title'):
                        print(f"[Headline {i}]: {article['title']}")
                        speak(article['title'])
        else:
            print(f"News API Error: {r.status_code} - {r.text}")
            speak("I'm sorry, I couldn't fetch the news. Please check your API key.")

    else:
        output = aiProcess(c)
        speak(output) 

if __name__ == "__main__":
    speak("Initializing Alfred....")
    while True:
        r = sr.Recognizer()
        
        # INCREASED PAUSE THRESHOLD
        r.pause_threshold = 1.5 
        
        try:
            with sr.Microphone() as source:
                print("\n[Passive Mode] Listening for wake word...")
                audio = r.listen(source, timeout=2, phrase_time_limit=3)
            
            print("[Passive Mode] recognizing...")
            word = r.recognize_google(audio)
            print(f"Wake word interpreted as: '{word}'")
            
            # Reverted to strictly check for exactly "alfred"
            if word.lower().strip() == "alfred":
                speak("Ya")
                
                # --- CONTINUOUS ACTIVE LOOP ---
                while True:
                    try:
                        with sr.Microphone() as source:
                            print("\n[Alfred Active] Listening for command...")
                            audio = r.listen(source, timeout=5, phrase_time_limit=8)
                        
                        print("[Alfred Active] recognizing...")
                        raw_command = r.recognize_google(audio)
                        print(f"Command heard: {raw_command}") 
                        
                        # If you just say "Alfred" while it is already active, say "Ya" again
                        if raw_command.lower().strip() == "alfred":
                            speak("Ya")
                            continue
                        
                        # Clean the command: remove "alfred" and extra spaces so it doesn't break logic
                        command = raw_command.lower().replace("alfred", "").strip()
                        
                        # If the command is empty after cleaning, just keep listening
                        if not command:
                            continue
                        
                        if command in ["sleep", "go to sleep", "stop listening"]:
                            speak("Going to sleep.")
                            break 
                            
                        elif command in ["exit program", "shut down", "shutdown", "quit"]:
                            speak("Shutting down. Goodbye.")
                            exit() 
                        
                        # Process normal commands using the cleaned string
                        processCommand(command)

                    except sr.WaitTimeoutError:
                        pass 
                    except sr.UnknownValueError:
                        pass 
                    except Exception as e:
                        print("Command Error: {0}".format(e))

        except sr.WaitTimeoutError:
            pass 
        except sr.UnknownValueError:
            pass 
        except Exception as e:
            print("Wake Word Error: {0}".format(e))