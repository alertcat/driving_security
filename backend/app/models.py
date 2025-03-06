from flask import current_app
import struct
import wave
import time
import pyaudio
from pydub import AudioSegment
from pydub.playback import play

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
    )
    print(response)
    content = response.choices[0].message.content
    return content

def manual_refer(user_prompt):
    cont = ""  # 确保每次新问题时清空
    for ans in session.ask(user_prompt, stream=True):
        new_text = ans.content[len(cont):]  # 只获取增量部分
        cont += new_text  # 仅累积新部分
    answer = cont.rstrip('##0$$').strip()
    answer = answer.replace("*", "")
    return answer

def record_audio(filename="audio.wav"):
    print("Start listening...")
    frames = []
    while True:
        pcm = stream_in.read(porcupine.frame_length, exception_on_overflow=False)
        pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
        
        keyword_index = porcupine.process(pcm_unpacked)
        if keyword_index >= 0:  # 检测到唤醒词
            print("Wake words detected, start recording...")

            # 录音，直到没有声音
            for _ in range(0, int(porcupine.sample_rate / porcupine.frame_length * 5)):  # 录制 5 秒
                pcm = stream_in.read(porcupine.frame_length, exception_on_overflow=False)
                frames.append(pcm)
                
            # 保存录音
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(porcupine.sample_rate)
                wf.writeframes(b''.join(frames))
            break

def transcribe_audio(filename="audio.wav"):
    with open(filename, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
    return transcription.text

def STT():
    try:
        record_audio()  # 开始录音
        transcription_text = transcribe_audio()  # 转录音频
        return transcription_text
    except KeyboardInterrupt:
        print("exit...")
    finally:
        stream_in.close()
        pa.terminate()
        porcupine.delete()

def TTS(text):
    output_path = './output.wav'
    orca.synthesize_to_file(text=text, output_path=output_path)
    orca.delete()
    audio = AudioSegment.from_wav(output_path)
    play(audio)  # 直接播放音频
    return output_path