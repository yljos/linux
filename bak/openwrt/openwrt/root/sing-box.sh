#!/bin/sh

# ------------------------------------------------
# 配置区域
# ------------------------------------------------
# 定义 Linux 下的 Firefox User-Agent
# 含义：运行在 X11 系统(Linux x86_64) 上的 Firefox 浏览器
UA="Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0"

# ------------------------------------------------
# 第一部分：依赖检测
# ------------------------------------------------
if [ -f /root/1 ]; then
	echo "检测到依赖已安装 (标记 /root/1 存在)，跳过 opkg 安装步骤。"
else
	echo "未检测到依赖标记，开始安装..."

	echo "正在更新软件包列表..."
	opkg update

	echo "正在安装或更新依赖 (curl, jq, tar, kmod-nft-tproxy)..."
	opkg install curl jq tar kmod-nft-tproxy

	# 安装完成后写入标记
	echo "1" >/root/1
	echo "依赖处理完毕。"
fi

# ------------------------------------------------
# 第二部分：Sing-box 更新逻辑 (Linux Firefox UA)
# ------------------------------------------------
echo "继续执行后续逻辑..."
echo "正在获取最新 Sing-box 版本信息..."

# 1. 获取重定向地址 (使用 Linux Firefox UA)
# -w %{redirect_url}: 尝试直接输出跳转后的 URL
LATEST_URL=$(curl -s -I -A "$UA" -o /dev/null -w "%{redirect_url}" "https://github.com/SagerNet/sing-box/releases/latest")

# 3. 校验获取结果
if [ -z "$LATEST_URL" ]; then
	echo "错误：无法获取版本信息。请检查网络连接。"
	exit 1
fi

# 4. 提取版本号 (Tag)
TAG=$(echo "$LATEST_URL" | grep -oE "v[0-9]+\.[0-9]+\.[0-9]+" | head -n 1)

if [ -z "$TAG" ]; then
	echo "错误：解析版本号失败。获取到的 URL 为: $LATEST_URL"
	exit 1
fi

# 提取纯数字版本 (去掉 v)
VERSION=$(echo "$TAG" | sed 's/^v//')
DOWNLOAD_URL="https://github.com/SagerNet/sing-box/releases/download/$TAG/sing-box-$VERSION-linux-amd64.tar.gz"

echo "-----------------------------------------------"
echo "模拟浏览器: Linux Firefox"
echo "最新版本: $TAG"
echo "下载链接: $DOWNLOAD_URL"
echo "-----------------------------------------------"
echo "正在下载..."

cd /usr/bin || exit 1

# 下载 (带上 UA 防止下载阶段被拦截)
curl -Lo temp_singbox.tar.gz -A "$UA" "$DOWNLOAD_URL"

if [ $? -eq 0 ]; then
	echo "下载完成，正在解压安装..."

	# 解压文件
	tar zxvf temp_singbox.tar.gz --strip-components=1 "sing-box-$VERSION-linux-amd64/sing-box"

	# 权限设置
	chown root:root sing-box
	chmod +x sing-box

	# 清理临时文件
	rm temp_singbox.tar.gz

	echo "✅ Sing-box 更新成功！当前版本: $VERSION"

	# 如需自动重启，请取消下面这行的注释
	# /etc/init.d/sing-box restart
else
	echo "❌ 下载失败，请重试。"
	rm -f temp_singbox.tar.gz
	exit 1
fi
