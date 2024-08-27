# -*- coding: UTF-8 -*-

# 导入所需的库和模块
import sys
import os
import siot
from unihiker import GUI
from unihiker import Audio
from pinpong.board import Board, Pin
from pinpong.extension.unihiker import *
import time

# 设置音量的函数
def set_volume(volume):
    volume = max(0, min(100, volume))  # 限制音量值在0到100之间
    os.system("amixer -c 2 set PCM {}% > /dev/null".format(volume))

# MQTT消息回调函数，用于处理收到的MQTT消息
def on_message(client, userdata, msg):
    global communication_flag
    payload = msg.payload.decode()
    if msg.topic == "siot/mess":
        print(payload)
        if payload in ["1", "2", "3", "6"]:
            communication_flag = int(payload)

# 拨打电话按钮的事件处理函数
def handle_call_button():
    button_call.config(state="disable")
    button_continue.config(state="disable")
    text_status.config(text="正在通话中")
    siot.publish_save(topic="siot/sys", data="1")

# 继续对话按钮的事件处理函数
def handle_continue_button():
    button_call.config(state="disable")
    text_status.config(text="请说出对话内容")
    siot.publish_save(topic="siot/sys", data="2")

# 初始化GUI界面
gui = GUI()

# 初始化开发板和音频模块
Board().begin()
audio = Audio()

# 初始化MQTT客户端并连接
siot.init(client_id="32829411907149986", server="10.1.2.3", port=1883, user="siot", password="dfrobot")
siot.connect()
siot.loop()
siot.subscribe(topic="siot/mess")

# 初始化GPIO引脚
pin_out = Pin(Pin.P22, Pin.OUT)
pin_in = Pin(Pin.P21, Pin.IN)

# 设置MQTT消息回调函数
siot.set_callback(on_message)

# 绘制UI界面元素
text_title = gui.draw_text(text="遇见苏格拉底", x=120, y=30, font_size=20, color="#0000FF")
text_title.config(origin="center")
button_call = gui.add_button(text="拨打电话", x=60, y=90, w=80, h=40, onclick=handle_call_button)
button_continue = gui.add_button(text="继续对话", x=160, y=90, w=80, h=40, onclick=handle_continue_button)
button_call.config(origin="center")
button_call.config(state="disable")
button_continue.config(origin="center")
button_continue.config(state="disable")
text_status = gui.draw_text(text="", x=120, y=180, font_size=20, color="#FF6666")
text_status.config(origin="center")

# 初始化通信标志变量
communication_flag = 0
set_volume(100)  # 设置初始音量为100%
call_flag = 0

# 主循环，用于检查输入状态和响应MQTT消息
while True:
    # 检测输入引脚状态，执行相应操作 挂断把所有状态清理，音频停止播放
    if (pin_in.read_digital() == 0) and communication_flag == 9:
        pin_out.write_digital(0)
        button_call.config(state="disable")
        text_status.config(text="")
        if call_flag == 0:
            siot.publish_save(topic="siot/sys", data="stop")
        communication_flag = 0

    # 如果当前没有通信，则等待电话挂断信号，之后开始新的通信
    if communication_flag == 0:
        while (pin_in.read_digital() == 0):
            if communication_flag in [3, 2]:
                break
            else:
                pass
        if communication_flag == 0:
            siot.publish_save(topic="siot/sys", data="start")
            button_call.config(state="normal")
            communication_flag = 9
            call_flag = 0

    # 如果通信标志为1，表示正在留言
    if communication_flag == 1:
        time.sleep(1)
        text_status.config(text="请留言中")
        pin_out.write_digital(1)
        siot.publish_save(topic="siot/sys", data="2")
        communication_flag = 9
        call_flag = 1

    # 如果通信标志为2，表示留言完成
    if communication_flag == 2:
        text_status.config(text="留言完成")
        pin_out.write_digital(0)
        time.sleep(2)
        communication_flag = 9
        call_flag = 1

    # 如果通信标志为6，表示接收到来电
    if communication_flag == 6:
        time.sleep(1)
        button_call.config(state="disable")
        button_continue.config(state="normal")
        text_status.config(text="苏格拉底来电")
        audio.start_play("music.wav")
        pin_out.write_digital(1)

        while (pin_in.read_digital() == 0):
            pass
        audio.stop_play()
        siot.publish_save(topic="siot/sys", data="3")
        pin_out.write_digital(0)
        time.sleep(1)
        text_status.config(text="正在通话中")

        while (pin_in.read_digital() != 0):
            print("对话")
            if communication_flag == 3:
                siot.publish_save(topic="siot/sys", data="3")
                text_status.config(text="对话中")
                communication_flag = 99
            else:
                pass
        text_status.config(text="通话完成")
        time.sleep(1)
        text_status.config(text="")
        button_call.config(state="disable")
        button_continue.config(state="disable")
        communication_flag = 9
        call_flag = 1

    time.sleep(0.01)  # 短暂休眠以减少CPU使用率
