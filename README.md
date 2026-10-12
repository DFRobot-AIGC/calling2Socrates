# calling2Socrates
一个本地运行的 AI 语音电话交互项目 —— 给哲人打电话

## 项目简介

"给苏格拉底打电话" 是一个完全本地化的 AI 语音电话项目：把行空板（UNIHIKER M10）当成一部
"真电话"，接通电脑上的 AI 哲人。摘机、拨号、无人接听、语音信箱、留言、回拨接听——
整套电话流程与真实电话一致，通话内容则由本地 LLM 生成。

内置 **六位哲人**，每人有独立的人设（LLM system prompt）与独立音色（TTS 语音）：

| 按钮 | 哲人 | TTS 音色 (edge-tts) | 风格 |
|------|------|----------------------|------|
| 打给苏格拉底 | 苏格拉底 | zh-CN-YunyangNeural | 启发式追问，先反问再给角度 |
| 打给孔子 | 孔子 | zh-CN-YunxiNeural (子) | 克己复礼，讲仁义与修身 |
| 打给老子 | 老子 | zh-CN-YunjianNeural | 道法自然，短句，留白 |
| 打给王阳明 | 王阳明 | zh-CN-YunxiNeural | 知行合一，讲心即理 |
| 打给费曼 | 费曼 | zh-CN-YunfengNeural | 大白话，生活类比，讲清本质 |
| 打给黑格尔 | 黑格尔 | zh-CN-YunhaoNeural | 辩证法：正题/反题/合题 |

另有 **打给画框** 按钮（预留）：用于接入 realtime 实时语音模型服务的实时双向对话
（见 [画框 / 实时语音](#画框--实时语音框架预留) 一节）。

## 系统架构

```
┌─────────────────────────┐        USB RNDIS (10.1.2.2/24 ↔ 10.1.2.3/24)
│  电脑端 (chat.py)        │◄────────────────────────────────────────────┐
│  · 拨号音/提示音/响铃     │                                                │
│  · 留言录音 (arecord)     │        MQTT (broker: 行空板 10.1.2.3:1883)   │
│  · ASR: voxtype(SenseVoice)│       siot/sys  板子→电脑                    │
│  · LLM: Ollama 本地      │──►  siot/mess  电脑→板子                    │
│  · TTS: edge-tts → gTTS   │◄────────────────────────────────────────────┤
│  · 回答语音播放 (pygame)   │                                                │
└─────────────────────────┘    行空板 (main.py, UNIHIKER M10)               ┘
                                   · 叉簧: 真电话摘机/挂机按键
                                   · 屏幕: 标题 + 7 个按钮 + 状态/倒计时
                                   · USB 扬声器: 响铃/提示 (aplay card 2)
                                   · LED: 留言提示
```

## 呼叫流程

```
按下叉簧(挂机位) → 屏幕"待机"
  → 松开叉簧(摘机)          电脑开始放 450Hz 拨号音（长而不中断）
  → 点击哲人按钮             拨号音停止
  → 无人接听等待 2 秒         （期间挂断则取消）
  → 该哲人"本人"播报语音信箱提示: "您拨打的电话暂时无人接听。我是孔子，请在滴声后留言。"
  → 滴一声
  → 留言 10 秒（屏幕倒计时 + LED，麦克风录音）
  → 按下叉簧(挂机)
  → 电脑处理: ASR(voxtype/SenseVoice) → LLM(Ollama, 哲人人设) → TTS(哲人音色)
  → 回拨: 行空板响铃
  → 松开叉簧(摘机)接听        电脑播放哲人对问题的回答
  → 按下叉簧(挂机)            通话结束，不再二次回拨
```

> **叉簧语义**（与真实电话一致）：叉簧**按下 = 挂机/待机**，**松开 = 摘机/通话中**。
> 按键均做 1 秒去抖，开机 3 秒为硬件稳定保护期。

## 硬件清单

| 部件 | 说明 |
|------|------|
| 电脑 | 运行 chat.py（原 LattePanda，任意 Linux 电脑均可） |
| 行空板 UNIHIKER M10 | Python 3.7 + SIoT 固件，运行 main.py |
| USB 声卡/扬声器 | 接行空板 USB 口，作为响铃/提示音输出（`aplay -D plughw:2,0`） |
| 叉簧按键 | 接行空板 P21（模拟电话摘机开关） |
| 麦克风 | 电脑端录音 |
| 音响 | 电脑端播放拨号音/提示音/回答 |
| USB 数据线 | 电脑 ↔ 行空板，同时供网（RNDIS）与数据 |

## 电脑端部署

### 1. 克隆仓库

```bash
git clone https://github.com/DFRobot-AIGC/calling2Socrates.git
cd calling2Socrates
```

### 2. 安装 ASR：voxtype (SenseVoice)

voxtype 提供 SenseVoice 中文语音识别，**无需 PyTorch**：

```bash
# Debian/Ubuntu (apt 源) 或 pip 安装后，确认可执行文件存在:
voxtype --help
```

### 3. 安装 LLM：Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:2b
```

> 注意：程序使用 Ollama **原生 `/api/chat` 接口**（带 `"think": false`），
> 不要走 `/v1` OpenAI 兼容端点（会挂起）。

### 4. 部署 Python 环境并运行

```bash
bash scripts/deploy_uv.sh
# 脚本自动: 建 .venv、装依赖、生成 .env、拉取 Ollama 模型

source .venv/bin/activate
python chat.py
```

或手动：

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env   # 按实际修改 MQTT/Ollama/DeepSeek 配置
source .venv/bin/activate
python chat.py
```

### 5. 网络（电脑 ↔ 行空板）

USB 线连接后，电脑端 USB RNDIS 网卡配置固定地址：

```bash
ip addr add 10.1.2.2/24 dev enp0s20u8c2   # 网卡名以 ip link 为准
```

行空板 SIoT 默认 10.1.2.3。MQTT broker 即行空板自带的 mosquitto（10.1.2.3:1883，
账号 `siot`，见 `.env`）。

## 行空板部署

1. 刷 SIoT 固件（行空板 M10）。
2. 将 `main.py` 上传到板子 `/root/calling2Socrates/`（或任意目录）。
3. 连接 USB 扬声器、叉簧按键（P21）。
4. 运行：

```bash
cd /root/calling2Socrates
DISPLAY=:0 XAUTHORITY=/var/run/lightdm/root/:0 python3 -u main.py
```

> 板子扬声器使用 USB 声卡（`aplay -D plughw:2,0`，音量 40%），行空板自带 Audio 无喇叭输出。

## 使用说明

1. 先后运行电脑端 `chat.py` 与板端 `main.py`（顺序无关，双方自动握手）。
2. **松开叉簧**（摘机）→ 电脑放拨号音，屏幕提示"已摘机，请选择哲人拨打"。
3. 点击任意哲人按钮 → 2 秒后该哲人的语音信箱提示 → 滴声 → 对着麦克风留言 10 秒。
4. **按下叉簧**（挂机）→ 哲人思考（ASR→LLM→TTS）。
5. 板子响铃 = 哲人来电话了，**松开叉簧**接听 → 电脑播放回答。
6. 听完**按下叉簧**挂机 → 回到待机。

## 画框 / 实时语音（框架预留）

"打给画框"按钮预留 realtime 实时语音模型服务接入（低延迟双向语音对话，替代留言-回拨模式）。

当前 `config.py` 中 `REALTIME_VOICE["enabled"] = False`：点击按钮后电脑端记录请求并回复
`mess=7`，板子显示"画框实时对话尚未接入"后自动回待机。

接入步骤（服务就绪后）：

1. `config.py`：填入 `REALTIME_VOICE` 的 `server_ip` / `port` / `protocol`，置 `enabled = True`。
2. `chat.py`：实现 `RealtimeVoiceSession`（`connect` / `send_audio` / `on_audio` / `close`）：
   - 麦克风 PCM → 模型服务；模型返回 PCM → pygame 播放。
3. 主循环中 `huakuang` 分支的 TODO 处启用会话。

## 协议说明（MQTT）

| Topic | 方向 | 消息 | 含义 |
|-------|------|------|------|
| siot/sys | 板→电脑 | `start` | 板子上线，请求电脑就绪 |
| | | `d` | 摘机（电脑开始拨号音） |
| | | `h` | 摘机后未拨号又挂机（电脑停拨号音） |
| | | `{哲人id}` | 拨号：socrates/confucius/laozi/wangyangming/feynman/hegel |
| | | `huakuang` | 拨号：画框（realtime，未接入时电脑回 7） |
| | | `2` | 开始留言录音 |
| | | `3` | 接听回拨（电脑播放回答） |
| | | `stop` | 挂机 |
| siot/mess | 电脑→板 | `ready` | 电脑就绪（每 5 秒重发，板子重启可自愈） |
| | | `1` | 开始留言（语音信箱提示+滴声已由电脑播完） |
| | | `2` | 留言结束 |
| | | `3` | 回答就绪 |
| | | `6` | 回拨来电（携带回答） |
| | | `7` | 画框实时语音尚未接入 |

## 配置文件

- `.env`（由 `.env.example` 复制生成）：MQTT 连接、Ollama/DeepSeek 地址与模型。
- `config.py`：
  - `PHILOSOPHERS`：六位哲人的名字、TTS 音色、LLM system prompt；
  - `REALTIME_VOICE`：画框/实时语音接入配置；
  - 音频路径、音量、留言时长等。

## 音频文件说明

| 文件 | 用途 |
|------|------|
| dialtone.wav | 450Hz 正弦拨号音（10s 整数倍周期，无缝循环），电脑端播放 |
| ding.wav | 语音信箱"请留言"提示滴声，电脑端播放 |
| music.wav | 回拨响铃声，板子 USB 扬声器播放 |
| waitingforcalling.wav | 无人接听等待音（最多播 2 秒） |
| start.wav | 预留（旧版拨通音） |
| 5s.wav / idel.wav | 预留 |
| question.wav | 留言录音输出（运行时生成） |
| outputs/*.mp3 | TTS 合成输出，含启动时预合成的 6 位哲人语音信箱提示语 |

## 项目结构

```
calling2Socrates/
├── chat.py            # 电脑端: MQTT + 拨号音 + 录音/ASR/LLM/TTS + 回拨调度
├── main.py            # 板端: GUI + 叉簧状态机 + 响铃/留言倒计时
├── config.py          # 哲人配置 / 实时语音框架配置 / 音频与 AI 参数
├── .env.example       # 环境变量模板 (MQTT/Ollama/DeepSeek)
├── scripts/deploy_uv.sh
└── *.wav              # 拨号音/提示音/响铃
```

## 许可证

本项目使用 [CC0 1.0 Universal](LICENSE) 许可证，你可以自由使用、修改和分发本项目。

## 参考

- 行空板 官网: https://www.unihiker.com.cn/
- voxtype (SenseVoice ASR)
- Ollama: https://ollama.com/
- Edge TTS: https://github.com/rany2/edge-tts
- gTTS: https://github.com/pndurette/gTTS
- Python dotenv: https://github.com/theskumar/python-dotenv
