import os
# This strictly hides the Pygame welcome message.
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import speech_recognition as sr
import webbrowser
import musicLibrary
import requests
from gtts import gTTS
import pygame
from dotenv import load_dotenv

# Import our new modules
from ai_brain import AIBrain
import system_controls

# Load environment variables from .env
load_dotenv()

recognizer = sr.Recognizer()
newsapi = os.getenv("NEWS_API_KEY")

# Initialize Pygame mixer ONCE at the start
pygame.mixer.init()

# Initialize the AI Brain (this starts the memory session)
brain = AIBrain()

def speak(text):
    try:
        tts = gTTS(text)
        tts.save('temp.mp3') 

        pygame.mixer.music.load('temp.mp3')
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        pygame.mixer.music.unload()
        os.remove("temp.mp3") 
    except Exception as e:
        print(f"Audio playback error: {e}")

def processCommand(c):
    # Ask Gemini to analyze the text and route the intent
    response = brain.process_input(c)

    # Execute system commands based on Gemini's routing
    if response.startswith("CMD_PLAY:"):
        song = response.replace("CMD_PLAY:", "").strip().lower()
        if song in musicLibrary.music:
            webbrowser.open(musicLibrary.music[song])
        else:
            speak(f"I couldn't find {song} in your music library.")

    elif response == "CMD_NEWS":
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
                for i, article in enumerate(articles[:5], 1):
                    if article.get('title'):
                        print(f"[Headline {i}]: {article['title']}")
                        speak(article['title'])
        else:
            print(f"News API Error: {r.status_code} - {r.text}")
            speak("I'm sorry, I couldn't fetch the news.")

    elif response.startswith("CMD_OPEN:"):
        site = response.replace("CMD_OPEN:", "").strip().lower()
        # Remove any spaces Gemini might have included (e.g. "youtube" from "you tube")
        site = site.replace(" ", "")
        webbrowser.open(f"https://{site}.com")

    elif response == "CMD_LOCK":
        speak("Locking the computer now.")
        system_controls.lock_pc()

    elif response == "CMD_MUTE":
        speak("Toggling the system volume.")
        system_controls.mute_volume()

    else:
        # If no command prefix is found, it's a normal conversation.
        speak(response)

if __name__ == "__main__":
    speak("Initializing Alfred....")
    while True:
        r = sr.Recognizer()
        r.pause_threshold = 1.5 
        
        try:
            with sr.Microphone() as source:
                print("\n[Passive Mode] Listening for wake word...")
                audio = r.listen(source, timeout=2, phrase_time_limit=3)
            
            print("[Passive Mode] recognizing...")
            word = r.recognize_google(audio)
            print(f"Wake word interpreted as: '{word}'")
            
            if word.lower().strip() == "alfred":
                speak("Ya")
                
                while True:
                    try:
                        with sr.Microphone() as source:
                            print("\n[Alfred Active] Listening for command...")
                            audio = r.listen(source, timeout=5, phrase_time_limit=8)
                        
                        print("[Alfred Active] recognizing...")
                        raw_command = r.recognize_google(audio)
                        print(f"Command heard: {raw_command}") 
                        
                        if raw_command.lower().strip() == "alfred":
                            speak("Ya")
                            continue
                        
                        command = raw_command.lower().replace("alfred", "").strip()
                        
                        if not command:
                            continue
                        
                        if command in ["sleep", "go to sleep", "stop listening"]:
                            speak("Going to sleep.")
                            break 
                            
                        elif command in ["exit program", "shut down", "shutdown", "quit"]:
                            speak("Shutting down. Goodbye.")
                            exit() 
                        
                        # Send command to the newly structured function
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