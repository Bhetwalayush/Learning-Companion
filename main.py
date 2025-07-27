import pyttsx3

def text_to_speech(text, rate=150, voice_gender="female"):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    # Select male or female voice
    for voice in voices:
        if voice_gender.lower() in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break

    engine.setProperty('rate', rate)
    engine.say(text)
    engine.runAndWait()
