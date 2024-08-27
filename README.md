# calling2Socrates
A locally executed AI voice phone interaction project

## 项目简介
“给苏格拉底打电话” 是一个基于AI的项目，旨在通过模拟苏格拉底式的启发式追问来探讨哲学问题。用户可以通过语音与AI苏格拉底对话，苏格拉底将根据用户的提问进行哲学式的反问与讨论。
该项目使用两个硬件组件：LattePanda 和 行空板，它们通过物联网的方式连接。项目的AI部分运行在电脑上，而行空板负责物理交互与UI界面。

## 环境要求
在开始使用本项目之前，请确保你的环境符合以下要求：
- 请根据 requirements.txt 文件安装所需的Python依赖库。

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
git clone https://github.com/DFRobot-AIGC/calling2Socrates.git
2. 创建虚拟环境（可选）
建议使用conda虚拟环境来隔离项目的依赖库。你可以使用以下命令创建和激活虚拟环境：
### 创建虚拟环境
conda create -n socrates python=3.12

### 激活虚拟环境
conda activate socrates

3. 进入项目目录并安装依赖：
pip install -r requirements.txt
4. 运行主程序 chat.py：
python chat.py

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

## 参考
- LattePanda 官网: https://www.lattepanda.com/
- 行空板 官网: https://www.unihiker.com.cn/