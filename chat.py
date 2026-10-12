import numpy as np
import os
import datetime
import random
import json
import urllib.request
from collections import deque
from scipy.io import wavfile
import subprocess
import shutil
from openai import OpenAI
import siot
import time
import pygame
import socket
import edge_tts
import logging
from config import MQTT_CONFIG, API_KEYS, AUDIO_CONFIG, FILE_PATHS, AI_CONFIG, PHILOSOPHERS, REALTIME_VOICE

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化pygame
try:
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.35)  # 降低音量，避免影响其他人
    logger.info("Pygame mixer initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pygame mixer: {e}")

# 摘机拨号音: 长而不中断(450Hz 正弦，10s 整数倍周期，loops=-1 无缝循环)
DIALTONE_FILE = os.getenv("DIALTONE_AUDIO", "dialtone.wav")
# 留言开始提示滴声(拨号结束后播放)
DING_FILE = os.getenv("DING_AUDIO", "ding.wav")

# 语音信箱提示语: 启动时按哲人预合成，无人接听后由该哲人"本人"播报
VM_PROMPT_FILES = {}
def pregen_voicemail_prompts():
    for pid, p in PHILOSOPHERS.items():
        path = os.path.join(FILE_PATHS['outputs_dir'], f"voicemail_{pid}.mp3")
        if os.path.exists(path) and os.path.getsize(path) > 500:
            VM_PROMPT_FILES[pid] = path
            continue
        text = f"您拨打的电话暂时无人接听。我是{p['name']}，请在滴声后留言。"
        result = text_to_speech_eageTTS(text, voice=p["voice"])
        if result and os.path.exists(result):
            try:
                shutil.move(result, path)
                VM_PROMPT_FILES[pid] = path
            except Exception:
                VM_PROMPT_FILES[pid] = result
    logger.info(f"语音信箱提示语就绪: {list(VM_PROMPT_FILES.keys())}")

# 初始化全局变量
model_type = AUDIO_CONFIG['whisper_model_type']
duration = AUDIO_CONFIG['record_duration']
output_path = FILE_PATHS['audio_files']['idle']

# 确保输出目录存在
os.makedirs(FILE_PATHS['outputs_dir'], exist_ok=True)

global flag
flag = 9
# 消息队列：避免多条 sys 消息互相覆盖导致丢状态（如 stop 后紧跟的下一条消息）
msg_queue = deque()
# 回拨相关
called_back = False      # 本次运行是否已回拨过（只回拨一次）
_callback_active = False  # 当前 flag==3 是否为回拨接听的问候语
greeting_path = None
# 当前通话对象（哲人 id），默认苏格拉底
current_philosopher = "socrates"

# 事件回调函数：消息入队，由主循环按顺序处理
def on_message_callback(client, userdata, msg):
    if (msg.topic == "siot/sys"):
        msg_queue.append(msg.payload.decode())
        logger.info(f"sys 消息入队: {msg.payload.decode()}")
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
    # 通知板子电脑端已就绪（板子收到后才发 start）
    time.sleep(1)
    siot.publish_save(topic="siot/mess", data="ready")
    logger.info("已发送 ready 给板子")
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
        command = f"arecord -f S16_LE -r 16000 -c 1 -d {duration} -t wav {filename}"
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
    



def transcribe_audio(filename, model_type=None):
    """使用本机 voxtype (SenseVoice) 进行语音转文字

    Args:
        filename: 音频文件路径 (WAV, 16kHz, mono)
        
    Returns:
        str: 转录的文本
    """
    try:
        result = subprocess.run(
            ["voxtype", "-q", "transcribe", "--engine", "sensevoice", filename],
            capture_output=True, text=True, check=True, timeout=120
        )
        # voxtype 会在 stdout 输出日志行，转写结果为最后一个非空行
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        transcribed_text = lines[-1] if lines else ""
        logger.info(f"Audio transcribed: {transcribed_text[:50]}...")
        return transcribed_text
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        return ""

def text_to_speech_edgeTTS_once(text, output_file, voice=None):
    """edge-tts 单次尝试，成功返回 True"""
    edge_tts_bin = shutil.which("edge-tts") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv", "bin", "edge-tts")
    voice = voice or AUDIO_CONFIG['tts_voice']
    try:
        r = subprocess.run([edge_tts_bin, "--voice", voice,
                              "--text", text, "--write-media", output_file],
                             capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 500:
            return True
        logger.error(f"edge-tts 失败: rc={r.returncode} {r.stderr.strip()[:150]}")
    except Exception as e:
        logger.error(f"edge-tts 异常: {e}")
    return False

def text_to_speech_gtts_once(text, output_file):
    """gTTS(Google 通道) 单次尝试，作为 edge-tts 被限流(403)时的兑底，成功返回 True"""
    try:
        from gtts import gTTS
        gTTS(text, lang='zh-cn').save(output_file)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 500:
            return True
    except Exception as e:
        logger.error(f"gTTS 失败: {e}")
    return False

def text_to_speech_eageTTS(text, voice=None):
    """TTS: 优先 edge-tts，被微软限流(403)等失败时自动切 gTTS(Google 语音)
    
    Args:
        text: 要转换的文本
        voice: edge-tts 音色（默认用当前哲人的音色）
        
    Returns:
        str: 生成的音频文件路径；全部失败返回 None
    """
    if voice is None:
        voice = PHILOSOPHERS.get(current_philosopher, PHILOSOPHERS["socrates"])["voice"]
    output_dir = FILE_PATHS['outputs_dir']
    # edge-tts 最多试 2 次（限流期间快速失败，尽早切兑底）
    for attempt in range(2):
        output_file = f'{output_dir}/{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}-{voice}.mp3'
        if text_to_speech_edgeTTS_once(text, output_file):
            logger.info(f"Edge TTS file saved: {output_file}")
            return output_file
        time.sleep(0.5)
    # edge-tts 不可用 → gTTS 兑底
    output_file = f'{output_dir}/{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}-gtts.mp3'
    if text_to_speech_gtts_once(text, output_file):
        logger.warning(f"edge-tts 不可用，已切换 gTTS 兑底语音: {output_file}")
        return output_file
    return None


def answer_the_question_deepseek(user_question, system_prompt):
    """使用DeepSeek API回答问题"""
    try:
        client = OpenAI(
            api_key=API_KEYS['deepseek'],
            base_url=AI_CONFIG['deepseek']['base_url']
        )
        response = client.chat.completions.create(
            model=AI_CONFIG['deepseek']['model'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ]
        )
        text = response.choices[0].message.content
        logger.info(f"DeepSeek answer: {text}")
        return text
    except Exception as e:
        logger.error(f"Failed to get answer from DeepSeek: {e}")
        return "我现在无法回答你的问题，请稍后再试。"

def answer_the_question_ollama(user_question, system_prompt):
    """使用本地Ollama模型回答问题"""
    try:
        # Ollama 0.40.x 的 /v1 OpenAI兼容接口对 qwen3.5 会挂死，改用原生 /api/chat 接口
        import json as _json
        import urllib.request as _urllib
        base = AI_CONFIG['ollama']['base_url'].rstrip('/').removesuffix('/v1')
        payload = _json.dumps({
            "model": AI_CONFIG['ollama']['model'],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            "stream": False,
            "think": False,
            # qwen3.5:2b 在本机不会自动输出结束符，必须限制生成长度，否则会生成几千token卡死
            "options": {"num_predict": 150}
        }).encode('utf-8')
        req = _urllib.Request(base + "/api/chat", data=payload,
                              headers={"Content-Type": "application/json"})
        with _urllib.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read())
        text = data["message"]["content"].strip()
        logger.info(f"Ollama answer: {text}")
        return text
    except Exception as e:
        logger.error(f"Failed to get answer from Ollama: {e}")
        return "我现在无法回答你的问题，请稍后再试。"

def check_flag_and_stop():
    if msg_queue:
        pygame.mixer.music.stop()
        return True  # 有新消息（如叉簧动作），立即打断当前音频
    return False

# 播放音乐并检查flag的函数
def play_with_flag_check(file):
    
    pygame.mixer.music.load(file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
        if check_flag_and_stop():  # 检查flag是否为4，并在需要时停止
            return True
    return False



# 预合成 6 位哲人的语音信箱提示语（gTTS 兑底，每个约 0.5 秒）
try:
    pregen_voicemail_prompts()
except Exception as e:
    logger.error(f"预合成语音信箱提示语失败: {e}")

# ============ 画框 / 实时语音框架（尚未接入，占位实现） ============
# 未来接入路径: REALTIME_VOICE.enabled=True 后，用下面的会话类与 realtime
# 实时语音模型服务建立实时双向音频流：
#   板子麦克风(USB音频) -> PC(录音) -> 模型服务 -> PC(播放) -> 板子扬声器
class RealtimeVoiceSession:
    """实时语音对话会话（框架占位，现在不做任何动作）"""

    def __init__(self, server_ip: str, port: int):
        self.server_ip = server_ip
        self.port = port
        self.active = False
        logger.info(f"[画框] RealtimeVoiceSession 创建: {server_ip or 'TODO'}:{port}（未接入）")

    def connect(self) -> bool:
        """TODO: 与模型服务建立连接(websocket/tcp)并启动双向音频流，返回是否成功"""
        logger.warning("[画框] 实时语音尚未接入: connect() 为占位实现")
        return False

    def send_audio(self, pcm: bytes) -> None:
        """TODO: 把麦克风 PCM 数据(16k/16bit/单声道)发给模型服务"""
        pass

    def on_audio(self, pcm: bytes) -> None:
        """TODO: 播放模型服务返回的音频(PCM, 如 pygame.mixer.Sound)"""
        pass

    def close(self) -> None:
        """TODO: 结束会话、释放资源"""
        self.active = False
        logger.info("[画框] RealtimeVoiceSession 结束(占位)")

# 主循环
_last_ready_t = time.time()
while True:
    try:
        # 周期性重发 ready：板子重启后可自动恢复 pc_ready 状态
        if time.time() - _last_ready_t > 5:
            _last_ready_t = time.time()
            siot.publish_save(topic="siot/mess", data="ready")
        # 从队列取一条消息转为 flag（一次只处理一条，防覆盖丢状态）
        if msg_queue:
            m = msg_queue.popleft()
            if m == "start":
                flag = 0
            elif m in PHILOSOPHERS:
                # 新通话开始(板子发来哲人 id): 切换人设，复位回拨状态
                current_philosopher = m
                called_back = False
                _callback_active = False
                greeting_path = None
                logger.info(f"呼叫对象: {PHILOSOPHERS[m]['name']}")
                flag = 1
            elif m == REALTIME_VOICE["id"]:
                # 画框(realtime 实时语音，框架预留，尚未接入): 现在不做任何动作
                logger.info(f"[画框] 收到实时语音呼叫请求 (enabled={REALTIME_VOICE['enabled']}, "
                            f"server={REALTIME_VOICE['server_ip'] or 'TODO'}:{REALTIME_VOICE['port']}, "
                            f"protocol={REALTIME_VOICE['protocol']})")
                if not REALTIME_VOICE["enabled"]:
                    siot.publish_save(topic="siot/mess", data="7")  # 通知板子: 尚未接入
                # TODO: 接入后改为:
                #     rt_session = RealtimeVoiceSession(REALTIME_VOICE["server_ip"], REALTIME_VOICE["port"])
                #     if rt_session.connect():
                #         flag = 1  # 或直接新的实时通话 flag
            elif m == "1":
                # 兼容旧协议: 未指定哲人时默认苏格拉底
                current_philosopher = "socrates"
                called_back = False
                _callback_active = False
                greeting_path = None
                flag = 1
            elif m == "2":
                flag = 2
            elif m == "3":
                flag = 3
            elif m == "d":
                flag = 10  # 板子摘机: 开始拨号音
            elif m == "h":
                flag = 11  # 板子放回挂机位(未拨号): 停止拨号音
            elif m == "stop":
                flag = 4

        if flag == 10:
            # 摘机拨号音: 长且不中断（无缝循环），拨号(sys=1)/放回(sys=h)时停止
            pygame.mixer.music.stop()
            pygame.mixer.music.load(DIALTONE_FILE)
            pygame.mixer.music.play(loops=-1)
            logger.info("Dial tone started")
            flag = 9

        if flag == 11:
            # 放回挂机位: 停止拨号音
            pygame.mixer.music.stop()
            logger.info("Dial tone stopped")
            flag = 9

        if flag == 4:  # 叉簧挂断：放挂机音；若本次还未回拨过(如留言未识别到语音)则问候语回拨
            pygame.mixer.music.stop()
            pygame.mixer.music.load(FILE_PATHS['audio_files']['end'])
            pygame.mixer.music.play()
            logger.info("Playing end sound")
            if not called_back:
                # 生成接通问候语（当前哲人音色），3秒后来电；
                # 若问候语合成失败，回拨接通后改播回答内容，保证一定有语音回复
                pname = PHILOSOPHERS.get(current_philosopher, PHILOSOPHERS["socrates"])["name"]
                greeting_path = text_to_speech_eageTTS(f"你好，我是{pname}，我们继续刚才的对话吧。")
                if greeting_path is None:
                    logger.warning("问候语合成失败，回拨接通后将改播回答内容")
                    greeting_path = output_path
                _callback_active = True
                time.sleep(3)
                siot.publish_save(topic="siot/mess", data="6")
                called_back = True
                logger.info("Socrates is calling back...")
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
                logger.info("Starting call process: 无人接听 2 秒 -> 留言")
                # 无人接听等待: 播放等待音，最多 2 秒（期间收到新消息则立即中断）
                pygame.mixer.music.load(FILE_PATHS['audio_files']['waiting'])
                pygame.mixer.music.play()
                interrupted = False
                for _ in range(20):
                    time.sleep(0.1)
                    if msg_queue:
                        interrupted = True
                        break
                pygame.mixer.music.stop()
                if interrupted:
                    flag = 9  # 等待期间已挂断，取消留言
                    continue
                # 留言提示: 先播当前哲人的语音信箱提示语，再滴一声，然后通知板子开始录音
                vm_prompt = VM_PROMPT_FILES.get(current_philosopher) or VM_PROMPT_FILES.get("socrates")
                if vm_prompt and os.path.exists(vm_prompt):
                    if play_with_flag_check(vm_prompt):
                        flag = 9  # 提示语播放期间被挂断，取消留言
                        continue
                if not play_with_flag_check(DING_FILE):
                    siot.publish_save(topic="siot/mess", data="1")
                flag = 9
            except Exception as e:
                logger.error(f"Error in flag 1 processing: {e}")

        if flag == 2:
            # 叉簧拿起留言：录音 -> 转写 -> AI回答 -> TTS -> 回拨（接通时播放对问题的回答）
            audio = record_audio(duration, FILE_PATHS['audio_files']['question'])
            siot.publish_save(topic="siot/mess", data="2")
            speech_to_text = transcribe_audio(audio, model_type)

            user_input = speech_to_text.strip()
            if not user_input or user_input in ("No speech detected, skipping transcription.",) or set(user_input) <= set(" "):
                user_input = ""
            if user_input:
                print("user question:" + user_input)
                system_prompt = PHILOSOPHERS.get(current_philosopher, PHILOSOPHERS["socrates"])["system"]
                has_deepseek_key = bool(API_KEYS['deepseek']) and API_KEYS['deepseek'] != "sk-xxx"
                if is_connected() and has_deepseek_key:
                    answer = answer_the_question_deepseek(user_input, system_prompt)
                    print('网络已连接且配置了DeepSeek密钥，使用DeepSeek回答。')
                else:
                    answer = answer_the_question_ollama(user_input, system_prompt)
                    print('使用本地Ollama回答。')
                output_path = text_to_speech_eageTTS(answer)
                if output_path is None:
                    logger.warning("回答语音合成失败，本次不发起回拨")
                    flag = 9
                    continue
                # 回答就绪：直接发起回拨，用户接通后听到的就是对自己问题的回答
                logger.info("回答就绪，苏格拉底回拨")
                siot.publish_save(topic="siot/mess", data="6")
                called_back = True
                _callback_active = True
                flag = 9
            else:
                logger.warning("未识别到语音内容，跳过AI回答")
                flag = 9
                time.sleep(0.1)
                continue

        if flag == 3:
            pygame.mixer.music.stop()
            play_file = greeting_path if (_callback_active and greeting_path) else output_path
            _callback_active = False
            greeting_path = None
            if not play_file or not os.path.exists(play_file):
                play_file = FILE_PATHS['audio_files']['idle']
            pygame.mixer.music.load(play_file)
            time.sleep(2)
            pygame.mixer.music.play()
            flag = 9
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        time.sleep(0.1)






