#!/bin/bash
set -e

# 项目根目录
WORKDIR=$(cd "$(dirname "$0")" && pwd)
cd "$WORKDIR"

# 1. 检查依赖
function check_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo >&2 "请先安装 $1"; exit 1; }
}

# 新增：检查并安装 ADB
function check_and_install_adb() {
  if command -v adb >/dev/null 2>&1; then
    echo "ADB (Android Debug Bridge) 已安装。"
    adb version
  else
    echo "未检测到 ADB (Android Debug Bridge)。正在尝试自动安装..."
    if [[ "$(uname)" == "Linux" ]]; then
      echo "检测到 Linux 系统。"
      if command -v apt-get >/dev/null 2>&1; then
        echo "检测到 Debian/Ubuntu 系统。正在使用 apt 安装 android-tools-adb..."
        sudo apt-get update
        sudo apt-get install -y android-tools-adb
      elif command -v dnf >/dev/null 2>&1; then
        echo "检测到 Fedora 系统。正在使用 dnf 安装 android-tools..."
        sudo dnf install -y android-tools
      elif command -v pacman >/dev/null 2>&1; then
        echo "检测到 Arch Linux 系统。正在使用 pacman 安装 android-tools..."
        sudo pacman -Syu --noconfirm android-tools
      elif command -v zypper >/dev/null 2>&1; then
        echo "检测到 openSUSE 系统。正在使用 zypper 安装 android-tools..."
        sudo zypper install -y android-tools
      else
        echo "无法识别的 Linux 发行版或未找到主流包管理器 (apt, dnf, pacman, zypper)。"
        echo "请参照 README.md 中的说明手动安装 ADB。"
        exit 1
      fi
      echo "ADB 安装尝试完成。请检查是否成功。"
      adb version
    elif [[ "$(uname)" == "Darwin" ]]; then
      echo "检测到 macOS 系统。"
      echo "请使用 Homebrew 安装 ADB: brew install --cask android-platform-tools"
      echo "如果未安装 Homebrew, 请访问 https://brew.sh/ 安装。"
      echo "安装 ADB 后请重新运行此脚本。"
      exit 1
    else
      echo "不支持的操作系统: $(uname)"
      echo "请参照 README.md 中的说明手动安装 ADB。"
      exit 1
    fi
  fi
}

echo "[1/7] 检查依赖..."
check_cmd python3
check_cmd pip3
check_cmd node
check_cmd npm

echo "[2/7] 检查并安装 ADB..."
check_and_install_adb

echo "[3/7] 安装Python依赖..."
pip3 install --upgrade pip
if [ -f "requirements.txt" ]; then
  pip3 install -r requirements.txt
else
  echo "警告: requirements.txt 文件不存在，跳过 Python 依赖安装"
fi

echo "[4/7] 安装前端依赖..."
cd frontend
npm install
cd "$WORKDIR"

# 5. 生成并安装 systemd 服务 (如果系统支持 systemctl)
if command -v systemctl >/dev/null 2>&1 && [ "$(uname)" == "Linux" ]; then # 确保是 Linux 且有 systemctl
  SERVICE_FILE=adbwatcher.service
  echo "[5/7] 生成 systemd 服务文件..."
  cat <<EOF | sudo tee /etc/systemd/system/adbwatcher.service > /dev/null
[Unit]
Description=ADB Watcher Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$WORKDIR
ExecStart=$(command -v python3) $WORKDIR/run_app.py
Restart=always
RestartSec=3
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  sudo systemctl enable adbwatcher.service
  sudo systemctl restart adbwatcher.service

  echo "[6/7] systemd 服务已启动并设置为开机自启。"
  echo "[7/7] 部署完成！"
  echo "可通过 systemctl status adbwatcher.service 查看服务状态。"
else
  echo "[5/7] 未检测到 systemctl (或非 Linux 系统)，跳过 systemd 服务安装。"
  echo "您可以手动运行 'python3 $WORKDIR/run_app.py' 来启动应用。"
  echo "[6/7] 部署完成 (无 systemd 服务)。"
  echo "[7/7] 安装完成！" 
fi

echo ""
echo "🎉 安装完成！"
echo "📱 前端访问地址: http://<您的IP或localhost>:7708"
echo "🔧 请参考 README.md 进行配置" 