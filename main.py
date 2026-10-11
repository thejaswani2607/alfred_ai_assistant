import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import threading
import queue
import time
import asyncio
import speech_recognition as sr
import webbrowser
import requests
import pywhatkit
import edge_tts
import pygame
from dotenv import load_dotenv

from ai_brain import AIBrain

load_dotenv()
recognizer = sr.Recognizer()
newsapi = os.getenv("NEWS_API_KEY")

pygame.mixer.init()
brain = AIBrain()

# --- EVENT-DRIVEN AUDIO QUEUE & DUPLEX FLAG ---
audio_queue = queue.Queue()
stop_event = threading.Event()

def generate_tts_sync(text, filename):
    """Wrapper to run asynchronous edge-tts in a synchronous thread."""
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    asyncio.run(communicate.save(filename))

def audio_worker():
    """Background thread for high-speed neural TTS playback."""
    while True:
        text_to_speak = audio_queue.get()
        if text_to_speak is None:
            break 
            
        filename = f"temp_{int(time.time())}.mp3"
        try:
            # Generate high-quality audio instantly
            generate_tts_sync(text_to_speak, filename)

            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()

            # Duplex Barge-in: Check for stop event every 10ms
            while pygame.mixer.music.get_busy():
                if stop_event.is_set():
                    pygame.mixer.music.stop()
                    stop_event.clear()
                    break
                pygame.time.Clock().tick(10)
                
            pygame.mixer.music.unload()
            os.remove(filename) 
        except Exception as e:
            print(f"Audio playback error: {e}")
        finally:
            audio_queue.task_done()

threading.Thread(target=audio_worker, daemon=True).start()

def speak(text):
    """Interrupts current speech and queues the new audio."""
    if pygame.mixer.music.get_busy():
        stop_event.set()
    audio_queue.put(text)

def processCommand(c):
    if c.lower().startswith("play "):
        song = c[5:].strip()
        speak(f"Playing {song} on YouTube.")
        pywhatkit.playonyt(song)
        return

    if "news" in c.lower():
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(f"https://newsapi.org/v2/top-headlines?country=us&apiKey={newsapi}", headers=headers)
        if r.status_code == 200:
            articles = r.json().get('articles', [])
            if not articles:
                speak("I couldn't find any news articles right now.")
            else:
                speak("Here are the top headlines.")
                for i, article in enumerate(articles[:5], 1):
                    if article.get('title'):
                        print(f"[Headline {i}]: {article['title']}")
                        speak(article['title'])
        return
        
    if c.lower().startswith("open "):
        site = c[5:].strip().replace(" ", "")
        speak(f"Opening {site}")
        webbrowser.open(f"https://{site}.com")
        return

    response = brain.process_input(c)
    speak(response)

def ai_worker(command):
    processCommand(command)

if __name__ == "__main__":
    speak("Initializing Alfred with neural voice.")
    while True:
        r = sr.Recognizer()
        r.pause_threshold = 1.0 # Shortened for faster duplex listening
        
        try:
            with sr.Microphone() as source:
                print("\n[Passive Mode] Listening for wake word...")
                audio = r.listen(source, timeout=2, phrase_time_limit=3)
            
            word = r.recognize_google(audio)
            
            if word.lower().strip() == "alfred":
                # Immediately halt any currently playing audio (Duplex capability)
                stop_event.set()
                speak("Yes?")
                
                while True:
                    try:
                        with sr.Microphone() as source:
                            print("\n[Alfred Active] Listening for command...")
                            audio = r.listen(source, timeout=5, phrase_time_limit=8)
                        
                        raw_command = r.recognize_google(audio)
                        print(f"Command heard: {raw_command}") 
                        
                        if raw_command.lower().strip() == "alfred":
                            stop_event.set()
                            speak("Yes?")
                            continue
                        
                        command = raw_command.lower().replace("alfred", "").strip()
                        
                        if command in ["stop", "quiet", "shut up", "cancel"]:
                            stop_event.set()
                            continue
                        
                        if not command:
                            continue
                        
                        if command in ["sleep", "go to sleep", "stop listening"]:
                            speak("Going to sleep.")
                            break 
                            
                        if command in ["exit program", "shut down", "shutdown", "quit"]:
                            speak("Shutting down. Goodbye.")
                            audio_queue.put(None) 
                            time.sleep(2)
                            exit() 
                        
                        threading.Thread(target=ai_worker, args=(command,), daemon=True).start()

                    except sr.WaitTimeoutError:
                        pass 
                    except sr.UnknownValueError:
                        pass 

        except sr.WaitTimeoutError:
            pass 
        except sr.UnknownValueError:
            pass