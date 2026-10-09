import speech_recognition as sr
import webbrowser
import musicLibrary
import requests
from openai import OpenAI
from gtts import gTTS
import pygame
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

recognizer = sr.Recognizer()
newsapi = os.getenv("NEWS_API_KEY")

def speak(text):
    tts = gTTS(text)
    tts.save('temp.mp3') 

    # Initialize Pygame mixer
    pygame.mixer.init()

    # Load the MP3 file
    pygame.mixer.music.load('temp.mp3')

    # Play the MP3 file
    pygame.mixer.music.play()

    # Keep the program running until the music stops playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    
    pygame.mixer.music.unload()
    os.remove("temp.mp3") 

def aiProcess(command):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a virtual assistant named xyro skilled in general tasks like Alexa and Google Cloud. Give short responses please"},
        {"role": "user", "content": command}
    ]
    )

    return completion.choices[0].message.content

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
        # Multi-word music fix: grabs everything after "play"
        song = " ".join(c.lower().split(" ")[1:])
        
        if song in musicLibrary.music:
            link = musicLibrary.music[song]
            webbrowser.open(link)
        else:
            speak(f"I couldn't find {song} in your music library.")

    elif "news" in c.lower():
        r = requests.get(f"https://newsapi.org/v2/top-headlines?country=in&apiKey={newsapi}")
        if r.status_code == 200:
            data = r.json()
            articles = data.get('articles', [])
            for article in articles:
                speak(article['title'])

    else:
        # Let OpenAI handle the request
        output = aiProcess(c)
        speak(output) 

if __name__ == "__main__":
    speak("Initializing Xyro....")
    while True:
        r = sr.Recognizer()
         
        try:
            with sr.Microphone() as source:
                # Reverted phrase_time_limit back to 3, kept timeout at 2
                audio = r.listen(source, timeout=2, phrase_time_limit=3)
            
            word = r.recognize_google(audio)
            
            if(word.lower() == "xyro"):
                speak("Ya")
                
                with sr.Microphone() as source:
                    print("Xyro Active... Listening for command:")
                    audio = r.listen(source, timeout=5, phrase_limit=5) if hasattr(r, 'phrase_limit') else r.listen(source, timeout=5, phrase_time_limit=5)
                    command = r.recognize_google(audio)
                    print(f"Command heard: {command}") 
                    
                    processCommand(command)

        # Silently ignore expected timeouts and background noise
        except sr.WaitTimeoutError:
            pass 
        except sr.UnknownValueError:
            pass 
        except Exception as e:
            print("Error: {0}".format(e))