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
import logging
from config import MQTT_CONFIG, API_KEYS, AUDIO_CONFIG, FILE_PATHS, AI_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化pygame
try:
    pygame.mixer.init()
    logger.info("Pygame mixer initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pygame mixer: {e}")

# 初始化全局变量
model_type = AUDIO_CONFIG['whisper_model_type']
duration = AUDIO_CONFIG['record_duration']
output_path = FILE_PATHS['audio_files']['idle']

# 确保输出目录存在
os.makedirs(FILE_PATHS['outputs_dir'], exist_ok=True)

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
    siot.init(
        client_id=MQTT_CONFIG['client_id'],
        server=MQTT_CONFIG['server'],
        port=MQTT_CONFIG['port'],
        user=MQTT_CONFIG['user'],
        password=MQTT_CONFIG['password']
    )
    siot.connect()
    siot.loop()
    siot.set_callback(on_message_callback)
    siot.getsubscribe(topic="siot/sys")
    logger.info("MQTT connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MQTT server: {e}")

def record_audio(duration, filename):
    """使用arecord命令录音
    
    Args:
        duration: 录音时长（秒）
        filename: 保存的文件名
        
    Returns:
        filename: 录音文件路径
    """
    try:
        command = f"arecord -f cd -d {duration} -t wav {filename}"
        subprocess.run(command, shell=True, check=True)
        logger.info(f"Audio recorded successfully: {filename}")
        return filename
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to record audio: {e}")
        return None

# is connected to internet
def is_connected():
    try:
        socket.create_connection(("www.baidu.com", 80))
        return True
    except OSError:
        return False
    



def transcribe_audio(filename, model_type):
    """使用Whisper模型进行语音转文字
    
    Args:
        filename: 音频文件路径
        model_type: Whisper模型类型
        
    Returns:
        str: 转录的文本
    """
    try:
        model = whisper.load_model(model_type)
        result = model.transcribe(filename)
        transcribed_text = result["text"]
        logger.info(f"Audio transcribed: {transcribed_text[:50]}...")
        return transcribed_text
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        return ""

def text_to_speech_sub(text):
    """使用chattts-fork进行文本到语音转换
    
    Args:
        text: 要转换的文本
        
    Returns:
        str: 生成的音频文件路径
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        random_number = AUDIO_CONFIG['tts_random_number']
        output_dir = FILE_PATHS['outputs_dir']
        output_file = f'{output_dir}/{timestamp}-{random_number}.wav'
        
        command = f"chattts '{text}' -s {random_number} -o {output_file}"
        subprocess.run(command, shell=True, check=True)
        
        logger.info(f"TTS file saved: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Failed to convert text to speech: {e}")
        return FILE_PATHS['audio_files']['idle']  # 返回默认音频文件

def text_to_speech_eageTTS(text):
    """使用Edge TTS进行文本到语音转换
    
    Args:
        text: 要转换的文本
        
    Returns:
        str: 生成的音频文件路径
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        voice = AUDIO_CONFIG['tts_voice']
        output_dir = FILE_PATHS['outputs_dir']
        output_file = f'{output_dir}/{timestamp}-{voice}.mp3'
        
        command = f"edge-tts --voice '{voice}' --text '{text}' --write-media '{output_file}'"
        subprocess.run(command, shell=True, check=True)
        
        logger.info(f"Edge TTS file saved: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Failed to convert text to speech with Edge TTS: {e}")
        return FILE_PATHS['audio_files']['idle']  # 返回默认音频文件


def answer_the_question_deepseek(user_question):
    """使用DeepSeek API回答问题
    
    Args:
        user_question: 用户问题
        
    Returns:
        str: AI回答
    """
    try:
        client = llm_api(
            api_key=API_KEYS['deepseek'],
            base_url=AI_CONFIG['deepseek']['base_url'],
            model=AI_CONFIG['deepseek']['model']
        )
        text = client.call(user_question, prompt_version='deepseek')
        text = client.call(text, prompt_version='deepseek_TN')
        logger.info(f"DeepSeek answer: {text}")
        return text
    except Exception as e:
        logger.error(f"Failed to get answer from DeepSeek: {e}")
        return "我现在无法回答你的问题，请稍后再试。"

def answer_the_question_ollama(user_question):
    """使用本地Ollama模型回答问题
    
    Args:
        user_question: 用户问题
        
    Returns:
        str: AI回答
    """
    try:
        client = OpenAI(
            base_url=AI_CONFIG['ollama']['base_url'],
            api_key='ollama'  # required, but unused
        )
        
        prompt = AI_CONFIG['prompt_template'].format(user_question)
        
        response = client.chat.completions.create(
            model=AI_CONFIG['ollama']['model'],
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        text = response.choices[0].message.content
        logger.info(f"Ollama answer: {text}")
        return text
    except Exception as e:
        logger.error(f"Failed to get answer from Ollama: {e}")
        return "我现在无法回答你的问题，请稍后再试。"

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



# 主循环
while True:
    try:
        if flag == 4:  # 空闲状态
            pygame.mixer.music.stop()
            pygame.mixer.music.load(FILE_PATHS['audio_files']['end'])
            pygame.mixer.music.play()
            logger.info("Playing end sound")
            flag = 9

        if flag == 0:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(FILE_PATHS['audio_files']['idle'])
            pygame.mixer.music.play()
            logger.info("Playing idle sound")
            flag = 9

        if flag == 1:
            try:
                pygame.mixer.music.stop()
                logger.info("Starting call process")
                if play_with_flag_check(FILE_PATHS['audio_files']['waiting']):
                    flag = 9
                else:
                    # 只有当flag不为4时才会执行以下代码
                    pygame.mixer.music.stop()
                    if not play_with_flag_check(FILE_PATHS['audio_files']['start']):
                        siot.publish_save(topic="siot/mess", data="1")
                    flag = 9
            except Exception as e:
                logger.error(f"Error in flag 1 processing: {e}")

        if flag == 2:
            audio = record_audio(duration, FILE_PATHS['question_audio'])
            siot.publish_save(topic="siot/mess", data="2")
            speech_to_text = transcribe_audio(audio, model_type)

            user_input = speech_to_text
            print("user question:" + user_input)
            if is_connected():
                output_path = text_to_speech_eageTTS(answer_the_question_deepseek(user_input))
                print('网络已连接，执行edge-tts。')
            else:
                output_path = text_to_speech_sub(answer_the_question_ollama(user_input))
            siot.publish_save(topic="siot/mess", data="3")
            flag = 9

        if flag == 3:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(output_path)
            time.sleep(2)
            pygame.mixer.music.play()
            flag = 9
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        time.sleep(0.1)






