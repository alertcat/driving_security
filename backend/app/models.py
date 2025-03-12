from flask import current_app
import struct
import wave
import pyaudio
import sys
from pydub import AudioSegment
from pydub.playback import play

from .functions import get_air_quality, get_navigation, get_nearby, get_weather
import json

def set_client(new_client):
    global client
    client = new_client

def set_session(rag_object):
    global session
    assistants = rag_object.list_chats(name="Tesla")
    assistant = assistants[0]
    sessions = assistant.list_sessions()
    session = sessions[0]
    # print("\n===== Miss R ====\n")
    # print("Hello. What can I do for you?")

    # while True:
    #     question = input("\n===== User ====\n> ")
    #     print("\n==== Miss R ====\n")
        
    #     cont = ""
    #     for ans in session.ask(question, stream=True):
    #         print(ans.content[len(cont):], end='', flush=True)
    #         cont = ans.content

def set_picovoice(new_porcupine):
    global porcupine, pa, stream_in
    porcupine = new_porcupine
    pa = pyaudio.PyAudio()
    stream_in = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=porcupine.sample_rate,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )

def set_orca(new_orca):
    global orca
    orca = new_orca
    # stream_out = orca.stream_open()

def intent_detect(user_prompt):
    if client is None:
        raise ValueError("Client not initialized!")
    system_prompt = current_app.config['INTENT_DETECT_PROMPT']
    response = client.chat.completions.create(
        model=current_app.config['LLM_NAME'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={'type': 'json_object'},
    )
    return response.choices[0].message.content

def json_summarize(json_response):
    if client is None:
        raise ValueError("Client not initialized!")
    system_prompt = current_app.config['JSON_SUMMARIZE_PROMPT']
    response = client.chat.completions.create(
        model=current_app.config['LLM_NAME'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json_response}
        ],
        # stream = True
    )
    content = response.choices[0].message.content
    return content
    # for chunk in response:
    #     if chunk.choices:
    #         yield chunk.choices[0].delta.get("content", "")

def manual_refer(user_prompt):
    cont = "" 
    for ans in session.ask(user_prompt, stream=True):
        new_text = ans.content[len(cont):]
        cont += new_text
    answer = cont.split('#')[0]
    answer = answer.replace("*", "")
    return answer

def record_audio(filename="input.wav", duration=5):
    frames = []
    try:
        num_frames = int(porcupine.sample_rate / porcupine.frame_length * duration) # duration defines how many seconds the agent will listen.
        
        for _ in range(num_frames):
            pcm = stream_in.read(porcupine.frame_length, exception_on_overflow=False)
            frames.append(pcm)
        
        # save audio file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(porcupine.sample_rate)
            wf.writeframes(b''.join(frames))
    except Exception as e:
        print(f"Error during audio recording: {str(e)}")
        sys.exit(1)

def transcribe_audio(filename="./input.wav"):
    # use "whisper" to do Speech-to-text
    with open(filename, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            language="en"
        )
    return transcription.text

def STT():
    try:
        record_audio() 
        transcription_text = transcribe_audio()
        return transcription_text
    except KeyboardInterrupt:
        print("exit...")
    # finally:
    #     stream_in.close()
    #     pa.terminate()
    #     porcupine.delete()

def TTS(text):
    output_path = './output.wav'
    orca.synthesize_to_file(text=text, output_path=output_path)
    # orca.delete()
    audio = AudioSegment.from_wav(output_path)
    play(audio)  # play audio
    return output_path

def ai_agent(lat, lon):
    print("Agent is ready...")
    while True:
        try:
            pcm = stream_in.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
            keyword_index = porcupine.process(pcm_unpacked)
            if keyword_index >= 0:  # Detected wake word
                print("Wake words detected, start recording...")
                # start recording
                # user_prompt = STT()  # Speech-to-text
                user_prompt = "go to clementi mall"
                message = f"User: {user_prompt}"
                print(message)

                yield message # show user prompt
                
                if user_prompt.strip().lower() in ["exit.", "quit.", "stop.", "bye."]:  # if user wants to exit
                    print("Exiting conversation...")
                    break  # exit conversation
                
                # intent detection
                intent = json.loads(intent_detect(user_prompt))
                print(f"Detected intent: {intent}")

                # process different intents
                if intent["intent"] == "adjust_facilities":
                    response = "Get it."
                elif intent["intent"] == "navigation":
                    result = get_navigation(lat, lon, intent["destination"])
                    print(result)
                    response = json_summarize(json.dumps(result))
                elif intent["intent"] == "poi_search":
                    result = get_nearby(lat, lon, intent["categories"])
                    print(result)
                    response = json_summarize(json.dumps(result))
                elif intent["intent"] == "query":
                    if intent["type"] == "weather":
                        result = get_weather(lat, lon)
                        print(result)
                        response = json_summarize(json.dumps(result))
                    elif intent["type"] == "air_quality":
                        result = get_air_quality(lat, lon)
                        print(result)
                        response = json_summarize(json.dumps(result))
                    elif intent["type"] == "car":
                        response = manual_refer(user_prompt)
                    else:
                        response = "I'm sorry, I don't understand this query."
                else:
                    response = "I'm sorry, I don't understand this request."
                
                message = f"Agent: {response}"
                print(message)

                yield message

                TTS(response) # Text-to-speech
                    

        except Exception as e:
            print(f"Error: {str(e)}")
            continue