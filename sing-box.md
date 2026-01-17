go build -v -tags "with_quic,with_utls,with_clash_api" -ldflags "-s -w -X 'github.com/sagernet/sing-box/constant.Version=1.12.16'" ./cmd/sing-box




# 定义你想要的版本号
export MY_VERSION="v1.12.17-custom"

CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -v -trimpath \
    -o sing-box-amd64 \
    -tags "with_quic,with_utls,with_clash_api" \
    -ldflags "-X 'github.com/sagernet/sing-box/constant.Version=$MY_VERSION' -s -w -buildid=" \
    ./cmd/sing-box



# 定义镜像完整名称（请替换为你的 GitHub 用户名，名称必须小写）
export IMAGE_NAME="ghcr.io/your_username/sing-box"

# 构建并标记为 latest
# --platform 指定构建目标为 linux/amd64 (即 x86_64)
podman buildx build --platform linux/amd64 -t ${IMAGE_NAME}:latest .


podman push ${IMAGE_NAME}:latest
