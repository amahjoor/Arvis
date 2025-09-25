import speech_recognition as sr
import pyttsx3
from openai import OpenAI

client = OpenAI()

r = sr.Recognizer()
engine = pyttsx3.init()

while True:
    with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source)
        try:
            text = r.recognize_google(audio)
            print("You said:", text)

            # Send to GPT
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": text}]
            )

            reply = response.choices[0].message.content
            print("Jarvis:", reply)
            engine.say(reply)
            engine.runAndWait()
        except Exception as e:
            print("Error:", e)
