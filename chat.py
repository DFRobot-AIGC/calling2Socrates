from ChatTTS.experimental.llm import llm_api
import numpy as np
import os
import datetime
import random
from scipy.io import wavfile
import ChatTTS
import subprocess
import torch
import whisper
from openai import OpenAI
import siot
import time
import pygame
import socket
import edge_tts

# 初始化pygame
pygame.mixer.init()

#init ChatTTS
# chat = ChatTTS.Chat()
# chat.load_models()
model_type="small"# base small large medium
duration=10
#wait for 10 secend

global flag
flag = 9
# 事件回调函数
def on_message_callback(client, userdata, msg):
    global flag 
    if (msg.topic =="siot/sys" ):

        if (msg.payload.decode() == "start"):
            flag = 0
        if (msg.payload.decode() == "1"):
            flag = 1
        if (msg.payload.decode() == "2"):
            flag = 2
        if (msg.payload.decode() == "3"):
            flag = 3
        if (msg.payload.decode() == "stop"):
            flag = 4
try:

    siot.init(client_id="7194728385057718",server="10.1.2.3",port=1883,user="siot",password="dfrobot")
    siot.connect()
    siot.loop()
    siot.set_callback(on_message_callback)
    siot.getsubscribe(topic="siot/sys")
except:
    print("disconnect")

def record_audio(duration, filename):
    """使用arecord命令录音"""
    command = f"arecord -f cd -d {duration} -t wav {filename}"
    subprocess.run(command, shell=True)
    return filename

# is connected to internet
def is_connected():
    try:
        socket.create_connection(("www.baidu.com", 80))
        return True
    except OSError:
        return False
    



def transcribe_audio(filename, model_type):
    """使用Whisper模型进行语音转文字"""
    model = whisper.load_model(model_type)
    result = model.transcribe(filename)
    return result["text"]

def text_to_speech_sub(text):
    """using chattts-fork to tts"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # random_number = random.randint(1000, 9999)
    random_number=1996
    # fix voice 
    command = f"chattts '{text}' -s {random_number} -o outputs/{timestamp}-{random_number}.wav"
    subprocess.run(command, shell=True)
    output_file=f'outputs/{timestamp}-{random_number}.wav'
    # subprocess.run(['aplay', output_file])
    print(f"WAV 文件已保存为 '{output_file}'")
    return output_file

def text_to_speech_eageTTS(text):
    #using eage-tts to tts
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    VOICE = "zh-CN-YunxiaNeural"
    output_file=f'outputs/{timestamp}-{VOICE}.mp3'
    command =f"edge-tts --voice '{VOICE}' --text '{text}' --write-media '{output_file}'"
    subprocess.run(command, shell=True)
    
    # subprocess.run(['aplay', output_file])
    print(f"WAV 文件已保存为 '{output_file}'")
    return output_file


def answer_the_question_deepseek(user_question):
    API_KEY = 'sk-efef2be62a99432b8f3fa5272df98a0b'
    client = llm_api(api_key=API_KEY,
            base_url="https://api.deepseek.com",
            model="deepseek-chat")
    text = client.call(user_question, prompt_version = 'deepseek')
    text = client.call(text, prompt_version = 'deepseek_TN')
    print("answer is :"+text)
    return text

def answer_the_question_ollama(user_question):
    client = OpenAI(
    base_url = 'http://localhost:11434/v1',
    api_key='ollama', # required, but unused
    )
    response = client.chat.completions.create(
    model="deepseek-v2",
    messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "请扮演苏格拉底和我对话，用反问的方式来回答我的问题，只需要3个问题，不需要解释.你的回复将会后续用TTS模型转为语音，并且请把回答控制在30字以内。并且标点符号仅包含逗号和句号，将数字等转为文字回答。我的问题是："+user_question}
    ]
    )
    text=response.choices[0].message.content
   #你的回复将会后续用TTS模型转为语音，并且请把回答控制在30字以内。并且标点符号仅包含逗号和句号，将数字等转为文字回答。"},
    
    print("answer is :"+text)
    return text

def check_flag_and_stop():
    global flag
    if flag == 4:
        pygame.mixer.music.stop()
        return True  # 返回一个标记表示需要停止后续操作
    return False  # 返回一个标记表示可以继续执行

# 播放音乐并检查flag的函数
def play_with_flag_check(file):
    
    pygame.mixer.music.load(file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
        if check_flag_and_stop():  # 检查flag是否为4，并在需要时停止
            return True
    return False



while 1:
    if flag== 4:#空闲状态
        pygame.mixer.music.stop()
        # subprocess.run(['aplay', '5s.wav'])#搞个无声音乐
        pygame.mixer.music.load('5s.wav')
        pygame.mixer.music.play()
        flag= 9

    if flag== 0:
        pygame.mixer.music.stop()
        # subprocess.run(['aplay', 'idel.wav'])
        pygame.mixer.music.load('idel.wav')
        pygame.mixer.music.play()
        flag= 9

    if flag == 1:
        pygame.mixer.music.stop()
        if play_with_flag_check('waitingforcalling.wav'):
            flag = 9
        else:
            # 只有当flag不为4时才会执行以下代码
            pygame.mixer.music.stop()
            if not play_with_flag_check('start.wav'):
                siot.publish_save(topic="siot/mess", data="1")
            flag = 9

    if flag == 2:
        # siot.publish_save(topic="siot/mess", data="2")  
        audio=record_audio(10,"question.wav")
        siot.publish_save(topic="siot/mess", data="2")  
        speech_to_text=transcribe_audio(audio,model_type)

        user_input = speech_to_text
    
        print("user question:"+user_input)
        if is_connected():
            output_path = text_to_speech_eageTTS(answer_the_question_deepseek(user_input))
            print('网络已连接，执行edge-tts。')
            # 在这里执行在线功能
            # 使用edge-tts
        else:
            output_path = text_to_speech_sub(answer_the_question_ollama(user_input)) 
        siot.publish_save(topic="siot/mess", data="3") 
        flag =9
        
    if flag == 3:
       # # subprocess.run(['aplay', output_path]) 
        pygame.mixer.music.stop()
        pygame.mixer.music.load(output_path)
        # wait for 2 sec
        time.sleep(2)
        pygame.mixer.music.play()
        flag =9







