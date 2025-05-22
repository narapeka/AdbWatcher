# ADB Watcher

## 项目简介

ADB Watcher 是一个用于监控 Android 设备活动的全栈应用。它通过 ADB（Android Debug Bridge）实时监听设备日志，并通过 Web 前端界面进行展示和配置。适用于需要自动化监控、事件通知和设备状态管理的场景。

## 主要功能

- **设备连接监控**：自动检测并维护与 Android 设备的 ADB 连接。
- **日志实时采集**：后台服务自动拉取并分析设备 logcat 日志，支持事件过滤与去重。
- **事件通知**：可配置事件触发后通过 HTTP 通知外部系统。
- **Web 管理界面**：基于 Vue3 + Vuetify 的现代化前端，支持设备状态、日志、配置等可视化管理。
- **配置灵活**：支持通过 YAML 文件和前端界面灵活配置监控参数、通知端点等。

## 目录结构

```
AdbWatcher/
├── backend/         # FastAPI 后端服务
│   ├── main.py      # FastAPI 应用入口
│   ├── services/    # 设备监控与ADB操作核心逻辑
│   ├── routers/     # API 路由
│   ├── core/        # 配置、日志、工具模块
│   └── config/      # 配置文件
├── frontend/        # Vue3 + Vite 前端项目
│   └── src/         # 前端源码
├── run_app.py       # 一键启动前后端脚本
├── requirements.txt # Python依赖
└── adbwatcher.service # 可选的 systemd 服务文件
```

## 快速启动

### 0. 前提条件：安装 ADB (Android Debug Bridge)

在运行 ADB Watcher 之前，您需要在您的计算机（运行后端服务的机器）上安装 Android Debug Bridge (ADB) 命令行工具。ADB Watcher 后端服务会使用此工具与您的 Android 设备进行通信。

**安装方法:**

- **Linux:**
  ```bash
  # Debian/Ubuntu
  sudo apt update
  sudo apt install android-tools-adb

  # Fedora
  sudo dnf install android-tools

  # Arch Linux
  sudo pacman -S android-tools
  ```
  (请根据您的 Linux 发行版选择合适的命令)

- **macOS:**
  通常可以通过 Homebrew 安装:
  ```bash
  brew install --cask android-platform-tools
  ```

- **Windows:**
  从官方 Android 开发者网站下载 SDK Platform Tools:
  [https://developer.android.com/studio/releases/platform-tools](https://developer.android.com/studio/releases/platform-tools)
  下载后解压，并将 `platform-tools` 目录添加到系统的 `PATH` 环境变量中。

安装完成后，请打开终端或命令提示符，输入 `adb version` 并回车，确保 ADB 已正确安装并可以运行。

### 1. 安装依赖

#### 后端

```bash
pip install -r requirements.txt
```

#### 前端

```bash
cd frontend
npm install
```

### 2. 启动项目

在项目根目录下运行：

```bash
python run_app.py
```

- 后端服务默认监听 `7700` 端口，前端开发服务器监听 `7708` 端口。
- 前端通过代理自动转发 API 请求到后端。

### 3. 访问前端

浏览器访问 [http://localhost:7708](http://localhost:7708) 即可使用 Web 管理界面。

## 主要依赖

### 后端

- FastAPI
- Uvicorn
- Pydantic
- adb-shell
- PyYAML
- requests

### 前端

- Vue 3
- Vuetify 3
- Vite
- Axios

## 配置说明

- 后端配置文件位于 `backend/config/config.yaml`，可设置 ADB 设备ID、通知端点、日志等级等参数。
- 前端支持通过界面动态修改部分配置。

## 如何打开设备ADB权限

1. **打开开发者选项**：
   - 在 Android 设备上，进入"设置" > "关于手机"，连续点击"版本号"7次，直到提示已进入开发者模式。
2. **启用 USB 调试**：
   - 返回"设置" > "系统" > "开发者选项"，找到并开启"USB 调试"。
3. **授权调试**：
   - 首次连接时，设备会弹出"是否允许 USB 调试"对话框，点击"允许"。

## 适用场景

- 自动化测试与监控
- 设备远程管理
- 日志采集与事件通知

---

如需更详细的功能说明或定制化开发，请查阅源码或联系开发者。 