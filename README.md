# ADB Watcher - 多珀播放器海报墙监控工具

## 什么是 ADB Watcher？

ADB Watcher 是一个专门为多珀播放器设计的海报墙监控工具。它能够实时监控您的多珀播放器，当您在播放器上点击播放电影或电视剧时，自动将媒体文件路径发送给蓝光机，实现一键播放功能。

## 主要用途

- **自动播放**：在多珀播放器上点击播放 → 蓝光机自动开始播放
- **无缝体验**：无需手动操作蓝光机，享受流畅的观影体验
- **实时监控**：24小时监控播放器状态，确保随时可用

## 快速开始

### 第一步：安装 ADB 工具

ADB Watcher 需要通过 ADB 与您的多珀播放器通信。请先安装 ADB 工具：

**Windows 用户：**
1. 下载 [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. 解压到任意文件夹（如 `C:\adb`）
3. 将 `C:\adb` 添加到系统环境变量 PATH 中
4. 打开命令提示符，输入 `adb version` 验证安装

**macOS 用户：**
```bash
brew install --cask android-platform-tools
```

**Linux 用户：**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install android-tools-adb

# CentOS/RHEL
sudo yum install android-tools
```

### 第二步：启用多珀播放器的 ADB 调试

1. 在多珀播放器上进入 **设置** → **关于本机**
2. 连续点击 **版本号** 7次，启用开发者选项
3. 返回设置，进入 **开发者选项**
4. 开启 **USB 调试** 和 **网络调试**
5. 记录下播放器的 IP 地址（在设置 → 网络中可以查看）

### 第三步：安装 ADB Watcher

1. 下载并解压 ADB Watcher
2. 打开命令提示符，进入项目目录
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   cd frontend
   npm install
   ```
4. 启动服务：
   ```bash
   python run_app.py
   ```

### 第四步：配置

打开浏览器访问：http://localhost:7708
- 配置多珀播放器IP地址
- 配置通知服务器IP地址（即BlurayPoster运行主机的IP地址）
- 配置路径映射

**配置完成请重新 python run_app.py 重启程序**

## 路径映射配置说明

需要将多珀播放事件推送出来的源播放地址，转换成BlurayPoster可识别的路径。
最简单的方法，是成功启动程序后，先尝试在多珀播放器上播放影片，前台日志区域会打印播放地址。
记录下来之后，在路径映射中作相关配置。

一般来说有如下规律：

### 如果播放的是SMB共享
在多珀海报墙中的源播放地址：
content://com.doopoodigital.video.app/camera_photos/data/data/doopooexplorer/samba/<nas_ip>#<nas_share_name>/<path>/
在多珀文件管理器中的源播放地址为：
content://com.doopoodigital.file.app.fileProvider/root_path/data/data/doopooexplorer/samba/<nas_ip>#<nas_share_name>/<path>/

### 如果播放的是多珀本地硬盘文件或者本地CD2挂载
在多珀海报墙中的源播放地址：
content://com.doopoodigital.video.app/camera_photos/storage/emulated/0/<path>/
在多珀文件管理器中的源播放地址为：
content://com.doopoodigital.file.app.fileProvider/externalstorage/<path>/

## 与 BlurayPoster 配合使用

ADB Watcher 需要配合 [BlurayPoster](https://github.com/narapeka/BlurayPoster) 使用才能实现自动播放功能。

请参考BlurayPoster项目说明，启用 media.file.Path 媒体库执行器。

