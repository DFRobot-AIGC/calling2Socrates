# calling2Socrates
A locally executed AI voice phone interaction project

## 项目简介
“给苏格拉底打电话” 是一个基于AI的项目，旨在通过模拟苏格拉底式的启发式追问来探讨哲学问题。用户可以通过语音与AI苏格拉底对话，苏格拉底将根据用户的提问进行哲学式的反问与讨论。
该项目使用两个硬件组件：LattePanda 和 行空板，它们通过物联网的方式连接。项目的AI部分运行在电脑上，而行空板负责物理交互与UI界面。

## 环境要求
在开始使用本项目之前，请确保你的环境符合以下要求：
- 请根据 requirements.txt 文件安装所需的Python依赖库。
- 支持Python 3.8+。
- 推荐使用 `uv` 管理虚拟环境和依赖。

## 硬件清单
- LattePanda（可以用你的电脑代替）
- 电源线
- 行空板
- 麦克风
- 音响
- LED灯

## 安装指南
电脑上的主程序
1. 克隆本仓库到你的本地计算机：
   
  ```git clone https://github.com/DFRobot-AIGC/calling2Socrates.git```

2. 使用 `uv` 自动部署电脑端主程序：
```bash
bash scripts/deploy_uv.sh
```

这个脚本会自动完成以下操作：
- 创建 `.venv` 虚拟环境
- 使用 `uv` 安装 `requirements.txt` 中的依赖
- 如果 `.env` 不存在，则从 `.env.example` 自动生成
- 如果本机已安装 `ollama`，自动拉取 `.env` 中配置的模型，默认是 `qwen3.5:2b`

3. 配置环境变量（可选）：
将 `.env.example` 文件复制为 `.env` 并根据需要修改其中的配置项：
```
cp .env.example .env
```
然后编辑 `.env` 文件，设置你的API密钥和其他配置项。

4. 激活虚拟环境并运行主程序 chat.py：
```bash
source .venv/bin/activate
python chat.py
```

### 手动使用 uv（可选）
如果你不想使用自动部署脚本，也可以手动执行：
```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env
source .venv/bin/activate
python chat.py
```

## 行空板上的程序
1. 将 main.py 上传到行空板并运行。

## 使用说明
接打电话的过程
1. 启动：运行电脑上的主程序 chat.py 和行空板上的 main.py。
2. 拨打电话：在行空板的UI界面中点击“拨打电话”按钮，苏格拉底将开始与用户对话。
3. 继续对话：点击“继续对话”按钮，用户可以继续与苏格拉底对话。
4. 通话结束：当用户完成对话后，系统会自动结束通话。

## 项目演示
在运行项目后，用户可以体验与AI苏格拉底的对话。项目通过物联网技术将用户的语音转化为文本，苏格拉底AI将会基于用户的提问给出反问或回答，并通过音响播放生成的语音。

## wav文件说明
项目中包含多个wav文件，这些文件用于不同的状态提示和音频播放：
- 5s.wav：通话结束的背景音乐。
- idel.wav：系统闲置状态时的背景音乐。
- waitingforcalling.wav：用户开始拨打电话时的等待提示音。
- start.wav：用户成功拨通电话时的提示音。
- music.wav：苏格拉底来电时播放的音乐。

## 许可证
本项目使用 [CC0 1.0 Universal](LICENSE) 许可证，这意味着你可以自由使用、修改和分发本项目，无需获得原作者的许可。

## 代码结构说明

### 配置管理系统
项目新增了集中式配置管理系统，主要包括：

- **环境变量配置**：通过 `.env` 文件管理敏感信息和可变配置
- **config.py**：集中管理所有配置项，包括：
  - MQTT连接参数
  - API密钥
  - 音频设置
  - 文件路径
  - AI模型参数

使用配置系统的好处：
- 便于维护和修改配置
- 提高代码安全性，避免硬编码敏感信息
- 支持不同环境下的灵活配置

### 代码优化

#### 模块化设计
- 将功能分离为独立模块，提高代码可维护性
- 使用函数封装重复逻辑，减少代码冗余

#### 错误处理机制
- 增强了异常捕获和处理
- 添加了详细的日志记录，便于调试和问题追踪

#### 安全性提升
- API密钥通过环境变量管理，避免硬编码
- 增加了输入验证和安全检查

### 日志系统
项目集成了Python标准日志库，提供以下功能：
- 不同级别的日志记录（INFO, WARNING, ERROR）
- 时间戳和模块信息
- 便于调试和问题追踪的详细输出

使用示例：
```python
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("操作成功")
logger.error("发生错误")
```

## 参考
- LattePanda 官网: https://www.lattepanda.com/
- 行空板 官网: https://www.unihiker.com.cn/
- Python dotenv: https://github.com/theskumar/python-dotenv
- Edge TTS: https://github.com/rany2/edge-tts
