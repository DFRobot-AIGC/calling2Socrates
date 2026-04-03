# -*- coding: UTF-8 -*-

"""
配置文件，集中管理项目的所有配置项
"""

import os
from dotenv import load_dotenv

# 尝试加载.env文件中的环境变量
load_dotenv()

# MQTT配置
MQTT_CONFIG = {
    "client_id": os.getenv("MQTT_CLIENT_ID", "7194728385057718"),
    "server": os.getenv("MQTT_SERVER", "10.1.2.3"),
    "port": int(os.getenv("MQTT_PORT", "1883")),
    "user": os.getenv("MQTT_USER", "siot"),
    "password": os.getenv("MQTT_PASSWORD", "dfrobot")
}

# API密钥配置
API_KEYS = {
    "deepseek": os.getenv("DEEPSEEK_API_KEY", "sk-xxx")
}

# 音频配置
AUDIO_CONFIG = {
    "record_duration": int(os.getenv("RECORD_DURATION", "10")),
    "whisper_model_type": os.getenv("WHISPER_MODEL_TYPE", "small"),  # base, small, medium, large
    "tts_voice": os.getenv("TTS_VOICE", "zh-CN-YunxiaNeural"),
    "tts_random_number": int(os.getenv("TTS_RANDOM_NUMBER", "1996"))
}

# 文件路径配置
FILE_PATHS = {
    "outputs_dir": os.getenv("OUTPUTS_DIR", "outputs"),
    "audio_files": {
        "idle": os.getenv("IDLE_AUDIO", "idel.wav"),
        "waiting": os.getenv("WAITING_AUDIO", "waitingforcalling.wav"),
        "start": os.getenv("START_AUDIO", "start.wav"),
        "end": os.getenv("END_AUDIO", "5s.wav"),
        "question": os.getenv("QUESTION_AUDIO", "question.wav"),
        "music": os.getenv("MUSIC_AUDIO", "music.wav")
    }
}

# AI模型配置
AI_CONFIG = {
    "ollama": {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "model": os.getenv("OLLAMA_MODEL", "qwen3.5:2b")
    },
    "deepseek": {
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    },
    "prompt_template": "请扮演苏格拉底和我对话，用反问的方式来回答我的问题，只需要3个问题，不需要解释.你的回复将会后续用TTS模型转为语音，并且请把回答控制在30字以内。并且标点符号仅包含逗号和句号，将数字等转为文字回答。我的问题是：{}"
}

# 确保输出目录存在
os.makedirs(FILE_PATHS["outputs_dir"], exist_ok=True)
