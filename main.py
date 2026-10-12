# -*- coding: UTF-8 -*-
"""
行空板端：模拟"打电话 -> 无人接听 -> 语音信箱留言 -> 苏格拉底回拨"的完整流程

交互语义（真实电话叉簧）：
  - 叉簧按下 = 挂机位 = 待机
  - 空闲时松开叉簧(摘机) = 拨打苏格拉底
  - 通话中按下叉簧(挂机) = 挂断，保持按下=待机，此时可接回拨
  - 来电响铃时松开叉簧(摘机) = 接听
UI/音频对应：
  - 拨打:     电脑放等待音->拨通音, 板子LED亮, 显示"请留言"
  - 回拨:     板子USB喇叭循环铃声(music.wav), 屏幕"苏格拉底来电", 接通后电脑放问候语
"""
import sys
import os
import siot
from unihiker import GUI
from unihiker import Audio
from pinpong.board import Board, Pin
from pinpong.extension.unihiker import *
import time
import logging
import subprocess

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置音量的函数
def set_volume(volume):
    volume = max(0, min(100, volume))  # 限制音量在0到100之间
    os.system("amixer -c 2 set PCM {}% > /dev/null".format(volume))

# 铃声播放：unihiker Audio 默认走板载声卡（M10无喇叭），改用 aplay 指定 USB 喇叭(card 2)
ringer_proc = None
def start_ringer():
    global ringer_proc
    stop_ringer()
    try:
        ringer_proc = subprocess.Popen(
            "while true; do aplay -q -D plughw:2,0 music.wav; done",
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)  # 独立进程组，停止时不影响主程序
        logger.info("Ringer started (USB speaker)")
    except Exception as e:
        logger.error(f"Failed to start ringer: {e}")

def stop_ringer():
    global ringer_proc
    if ringer_proc is not None:
        try:
            os.killpg(os.getpgid(ringer_proc.pid), 9)  # 杀整个进程组(含循环中的 aplay 子进程)
        except Exception:
            try:
                ringer_proc.kill()
            except Exception:
                pass
        ringer_proc = None
    # 兜底：确保所有铃声 aplay 进程都被杀掉
    subprocess.run(["pkill", "-f", "aplay -q -D plughw:2,0 music.wav"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info("Ringer stopped")

def play_beep():
    """(已废弃) 滴声提示已移到电脑端播放"""
    pass

# 哲人名单: (协议 id, 显示名) —— 与 PC 端 config.py 的 PHILOSOPHERS 保持一致
PHILOSOPHERS = [
    ("socrates", "苏格拉底"),
    ("confucius", "孔子"),
    ("laozi", "老子"),
    ("wangyangming", "王阳明"),
    ("feynman", "费曼"),
    ("hegel", "黑格尔"),
]
# 画框 = realtime 实时语音（framework 预留，尚未接入；协议 id 与 PC 端 config.py 的 REALTIME_VOICE 一致）
REALTIME_VOICE_ID = "huakuang"
REALTIME_VOICE_NAME = "画框"
PHIL_NAMES = dict(PHILOSOPHERS)
PHIL_NAMES[REALTIME_VOICE_ID] = REALTIME_VOICE_NAME

def phil_name(pid):
    return PHIL_NAMES.get(pid, "苏格拉底")

# ---------------- 全局状态 ----------------
# communication_flag: 0=空闲  1=PC开始留言  2=PC留言结束  3=PC回答就绪  6=哲人来电
communication_flag = 0
pc_ready = False          # 电脑端 chat.py 已连接（收到 mess=ready）
dialed = False             # 是否正在通话中
start_sent = False         # start 只发一次，避免挂断后立即重拨
current_philosopher = "socrates"  # 当前通话对象（哲人 id）

# 留言倒计时（与 PC 端 RECORD_DURATION=10 保持一致）
VM_SECONDS = 10
vm_deadline = None          # 留言截止时刻；None=无留言进行中

# ---------------- MQTT ----------------
def on_message(client, userdata, msg):
    global communication_flag, pc_ready
    payload = msg.payload.decode()
    if msg.topic == "siot/mess":
        print(f"收到 mess: {payload}")
        if payload == "ready":
            pc_ready = True
        elif payload in ["1", "2", "3", "6"]:
            communication_flag = int(payload)
        # "7": 画框实时语音尚未接入（PC 端框架通知，主循环里提示后回待机）
        elif payload == "7":
            communication_flag = 7

def handle_call(pid):
    """点击哲人按钮: 呼叫指定哲人（电脑端收到哲人 id 后自行停止拨号音）"""
    global dialed, current_philosopher
    if pid not in PHIL_NAMES:
        return
    current_philosopher = pid
    for w, _ in phil_buttons:
        w.config(state="disable")
    set_status(f"正在呼叫{phil_name(pid)}...")
    siot.publish_save(topic="siot/sys", data=pid)
    dialed = True

def handle_continue_button():
    """(已废弃，原"继续对话"按钮改为"打给孔子")"""
    pass

def set_phil_btns(state):
    """6 个哲人按钮同进同出，只在实际变化时更新，避免每帧刷新"""
    global _call_btn_state
    if _call_btn_state != state:
        _call_btn_state = state
        for w, _ in phil_buttons:
            w.config(state=state)

def set_status(text):
    """只在实际变化时更新状态文字，避免每帧刷新"""
    global _status_text
    if _status_text != text:
        _status_text = text
        text_status.config(text=text)

# ---------------- 初始化 ----------------
gui = GUI()
Board().begin()
audio = Audio()

try:
    siot.init(client_id="32829411907149986", server="10.1.2.3", port=1883, user="siot", password="dfrobot")
    siot.connect()
    siot.loop()
    siot.set_callback(on_message)
    siot.getsubscribe("siot/mess")
    logger.info("MQTT connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MQTT server: {e}")

pin_out = Pin(Pin.P22, Pin.OUT)
pin_in = Pin(Pin.P21, Pin.IN)
set_volume(40)  # 降低音量，避免影响其他人

# ---------------- UI ----------------
text_title = gui.draw_text(text="遇见苏格拉底", x=120, y=30, font_size=20, color="#0000FF")
text_title.config(origin="center")

# 六个哲人按钮 2 列 x 3 行 + 画框按钮第 4 行整宽
# 注意: unihiker GUI 的 add_button 以 (x,y) 为按钮中心点放置(canvas 240x320 竖屏)
# 左列中心 x=65 (10..120), 右列中心 x=175 (120..230); 行中心 y=72/120/168 (h=42); 画框行中心 y=222 整宽
_btn_defs = [("socrates", 65, 72), ("confucius", 175, 72),
             ("laozi", 65, 120), ("wangyangming", 175, 120),
             ("feynman", 65, 168), ("hegel", 175, 168)]
phil_buttons = []
for _pid, _x, _y in _btn_defs:
    _b = gui.add_button(text=f"打给{PHIL_NAMES[_pid]}", x=_x, y=_y, w=110, h=42,
                         onclick=lambda p=_pid: handle_call(p))  # 字体用系统默认 style(11pt 中文)
    _b.config(origin="center")
    _b.config(state="disable")
    phil_buttons.append((_b, _pid))

# 画框按钮（realtime 实时语音，框架预留，尚未接入）
_rt_btn = gui.add_button(text=f"打给{REALTIME_VOICE_NAME}", x=120, y=222, w=210, h=42,
                         onclick=lambda: handle_call(REALTIME_VOICE_ID))
_rt_btn.config(origin="center")
_rt_btn.config(state="disable")
phil_buttons.append((_rt_btn, REALTIME_VOICE_ID))

text_status = gui.draw_text(text="等待电脑端连接...", x=120, y=278, font_size=18, color="#FF6666")
text_status.config(origin="center")

def idle_ui():
    """回到空闲状态（叉簧已按下=挂机位）"""
    global dialed, vm_deadline
    dialed = False
    vm_deadline = None
    pin_out.write_digital(0)
    set_status("待机")

def test_call_button():
    """测试钩子: /tmp/call_btn 文件 = 模拟点击哲人按钮
    文件内容为哲人 id(如 confucius)，为空/不存在时为苏格拉底；用后即删"""
    pid = "socrates"
    try:
        with open("/tmp/call_btn") as f:
            pid = f.read().strip() or "socrates"
        os.remove("/tmp/call_btn")
    except FileNotFoundError:
        return False
    except Exception:
        return False
    if pid in PHIL_NAMES:
        return pid
    return False

def read_fork():
    """读叉簧状态: 1=松开 0=按下
    测试钩子: 若存在 /tmp/fork_test 文件则从文件读值(0/1)，否则读真实 GPIO P21
    """
    try:
        with open("/tmp/fork_test") as f:
            return int(f.read().strip() or 1)
    except Exception:
        return pin_in.read_digital()

# ---------------- 去抖 ----------------
# 摘机/挂机都是持续状态(非瞬按)，去抖可放宽：
# 连续 DEBOUNCE_TICKS 次一致(0.05s*20=1s)才确认切换，过滤引脚抖动和按键弹跳
DEBOUNCE_TICKS = 20
_status_text = None         # 状态文字缓存
_call_btn_state = None     # 按钮状态缓存
sw_stable = read_fork()   # 以启动时首次读数为基线，避免上电浮动/残留按下被误判为边沿
last_sw = sw_stable        # 上一帧稳定值，用于边沿检测
_debounce_cnt = 0
boot_t = time.time()       # 开机 3 秒内忽略叉簧边沿（等硬件稳定）
def read_fork_debounced():
    global sw_stable, _debounce_cnt
    sw = read_fork()
    if sw != sw_stable:
        _debounce_cnt += 1
        if _debounce_cnt >= DEBOUNCE_TICKS:
            sw_stable = sw
            _debounce_cnt = 0
    else:
        _debounce_cnt = 0
    return sw_stable

# ---------------- 主循环 ----------------
while True:
    # ---- 0. UI 按钮状态与叉簧同步: 只有摘机(叉簧松开)且未拨号才可拨打 ----
    set_phil_btns("normal" if (sw_stable == 1 and not dialed and pc_ready) else "disable")

    # ---- 1. 来电响铃（哲人回拨）：叉簧保持按下(待机)时响铃，松开叉簧(摘机)=接听 ----
    if communication_flag == 6:
        communication_flag = 9
        set_phil_btns("disable")
        set_status(f"{phil_name(current_philosopher)}来电")
        pin_out.write_digital(1)
        start_ringer()
        # 等待用户松开叉簧（摘机接听）
        while read_fork() == 0:
            time.sleep(0.05)
        stop_ringer()
        # 接听成功：通知电脑播放问候语
        siot.publish_save(topic="siot/sys", data="3")
        dialed = True
        pin_out.write_digital(0)
        time.sleep(1)
        set_status("正在通话中")
        last_sw = read_fork_debounced()  # 同步边沿基线，避免摘机瞬间被误判
        communication_flag = 9
        continue

    # ---- 2. 叉簧边沿检测（已去抖）----
    # 真实电话叉簧: 按下(0)=挂机/待机, 松开(1)=摘机/通话中
    sw = read_fork_debounced()
    if sw != last_sw:
        last_sw = sw
        if time.time() - boot_t < 3.0:
            pass  # 开机保护期内只同步基线，不触发动作
        elif sw == 1:
            # 松开叉簧(摘机): 待机状态下通知电脑端开始拨号音(长且不中断)
            if communication_flag == 0 and not dialed:
                siot.publish_save(topic="siot/sys", data="d")
        else:
            # 按下叉簧(挂机): 通话中 -> 挂断（必须通知电脑端 stop）
            if dialed:
                stop_ringer()
                siot.publish_save(topic="siot/sys", data="stop")
                idle_ui()
                communication_flag = 0
            elif communication_flag == 0:
                # 摘机后未拨号又放回挂机位: 通知电脑端停止拨号音
                siot.publish_save(topic="siot/sys", data="h")

    # ---- 3. 电脑端消息驱动的状态 ----
    if communication_flag == 1:
        # PC 已开始留言(滴声已由电脑端播放)：LED亮 + 10秒倒计时，并通知电脑开始录音
        vm_deadline = time.time() + VM_SECONDS
        set_status(f"留言中 {VM_SECONDS}秒，请说话")
        pin_out.write_digital(1)
        siot.publish_save(topic="siot/sys", data="2")
        communication_flag = 9

    if communication_flag == 2:
        # PC 通知留言结束(未识别到语音)
        vm_deadline = None
        set_status("留言完成，思考中...")
        communication_flag = 9

    if communication_flag == 3:
        # PC 回答就绪（或回拨接通问候语就绪）
        # 只在摘机状态下回发 sys=3 触发电脑播放；待机(已挂机)时先挂起，
        # 用户再次摘机后立即播放，避免待机状态下电脑放音错位
        if sw_stable == 1:
            vm_deadline = None
            set_status("对话中")
            pin_out.write_digital(0)
            siot.publish_save(topic="siot/sys", data="3")
            communication_flag = 9

    # ---- 4. 空闲：电脑端就绪后发起呼叫（start 只发一次）----
    if communication_flag == 0 and not dialed:
        if not pc_ready:
            set_status("等待电脑端连接...")
        elif sw_stable == 1:
            # 已摘机: 电脑端正在播放拨号音，等待点击哲人按钮
            set_status("已摘机，请选择哲人拨打")
            _pid = test_call_button()  # 自动化测试钩子: /tmp/call_btn 内容 = 哲人 id
            if _pid:
                handle_call(_pid)
        else:
            if not start_sent:
                siot.publish_save(topic="siot/sys", data="start")
                start_sent = True
            set_status("待机")

    # ---- 4b. 画框实时语音未接入（PC 端回 mess=7，框架通知）----
    if communication_flag == 7:
        communication_flag = 9
        set_status(f"{REALTIME_VOICE_NAME}实时对话尚未接入")
        time.sleep(2.5)
        idle_ui()  # 回待机（含叉簧/拨号状态复位）
        communication_flag = 0

    # ---- 5. 留言 10 秒倒计时显示（set_status 内部去重，每秒才真正刷新）----
    if vm_deadline is not None:
        remaining = vm_deadline - time.time()
        if remaining > 0:
            set_status(f"留言中 {int(remaining) + 1}秒，请说话")
        else:
            set_status("留言完成，苏格拉底思考中...")

    time.sleep(0.05)
    # 调试: 追踪主循环状态
    try:
        with open("/tmp/loop_dbg", "w") as _f:
            _f.write(f"flag={communication_flag} sw={sw_stable} sw_raw={read_fork()} dialed={dialed} pc_ready={pc_ready}\n")
    except Exception:
        pass
