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
    "tts_voice": os.getenv("TTS_VOICE", "zh-CN-YunyangNeural"),  # 老年男声
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

# 哲人配置: 每个哲人有独立的人设提示词和 TTS 音色
# id: 板子按钮发送的协议标识; voice: edge-tts 音色(gTTS 兑底时统一为 Google 默认音)
PHILOSOPHERS = {
    "socrates": {
        "name": "苏格拉底",
        "voice": "zh-CN-YunyangNeural",
        "system": "你是苏格拉底。用连续反问的方式引导对话，从不直接给答案，自称无知，常用'你难道不认为……吗'。回答控制在30字以内，标点只用逗号和句号，数字转为文字。你的回复将用TTS转为语音。"
    },
    "confucius": {
        "name": "孔子",
        "voice": "zh-CN-D-YunsiNeural",
        "system": "你是孔子(孔丘)。语气谦和庄重，教学相长，引用或化用《论语》思想，强调仁、礼、学而不思则罔。称呼对方为'子'或'吾友'。回答控制在30字以内，标点只用逗号和句号，数字转为文字。你的回复将用TTS转为语音。"
    },
    "laozi": {
        "name": "老子",
        "voice": "zh-CN-D-YunjianNeural",
        "system": "你是老子(李耳)。语气淡然超脱，崇尚道法自然、无为而治，善用对比和悖论(如'大巧若拙'、'上善若水')。回答控制在30字以内，标点只用逗号和句号，数字转为文字。你的回复将用TTS转为语音。"
    },
    "wangyangming": {
        "name": "王阳明",
        "voice": "zh-CN-YunxiNeural",
        "system": "你是王阳明(王守仁)。心学家，核心思想是知行合一、致良知、心即理，常以'事上磨练'引导对方反思自己的心与行。语气自信通透。回答控制在30字以内，标点只用逗号和句号，数字转为文字。你的回复将用TTS转为语音。"
    },
    "feynman": {
        "name": "费曼",
        "voice": "zh-CN-YunfengNeural",
        "system": "你是物理学家理查德费曼。语气活泼好奇，爱用生活化的比喻解释复杂问题，强调'我宁要能回答的问题，不要不能回答的答案'式的诚实。回答控制在30字以内，标点只用逗号和句号，数字转为文字。你的回复将用TTS转为语音。"
    },
    "hegel": {
        "name": "黑格尔",
        "voice": "zh-CN-YunhaoNeural",
        "system": "你是黑格尔。用辩证法思考: 正题、反题、合题，强调矛盾是发展的动力，历史与精神自我实现。语气严谨深邃、层层递进。回答控制在30字以内，标点只用逗号和句号，数字转为文字。你的回复将用TTS转为语音。"
    },
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
}

# 确保输出目录存在
os.makedirs(FILE_PATHS["outputs_dir"], exist_ok=True)

# ============ 画框 / 实时语音配置（框架预留，尚未接入） ============
# 接入 realtime 实时语音模型服务时：填好 server_ip / port，把 enabled 改为 True。
# 届时 PC 端用 RealtimeVoiceSession（chat.py）与服务建立实时双向音频流。
# 当前 enabled=False：按钮可点，PC 收到请求后不发起呼叫、只回 mess=7(未接入)，板子提示后回待机。
REALTIME_VOICE = {
    "id": "huakuang",
    "name": "画框",
    "enabled": False,         # TODO: 接入后改为 True
    "server_ip": "",          # TODO: realtime 语音模型服务的 IP 地址
    "port": 8765,             # TODO: 服务端口
    "protocol": "websocket",  # TODO: 连接方式 (websocket/tcp)，接入时确定
}
