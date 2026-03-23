# 1. 提取版本号到变量
VERSION=$(go run ./cmd/internal/read_tag)

# 2. 执行构建
go build -v -tags "with_quic,with_utls,with_clash_api" \
  -ldflags "-s -w -X 'github.com/sagernet/sing-box/constant.Version=$VERSION'" \
  ./cmd/sing-box



# 自动读取版本号
VERSION=$(go run ./cmd/internal/read_tag)

CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -v -trimpath \
    -o sing-box-amd64 \
    -tags "with_quic,with_utls,with_clash_api" \
    -ldflags "-X 'github.com/sagernet/sing-box/constant.Version=$VERSION' -s -w -buildid=" \
    ./cmd/sing-box


# 定义镜像完整名称（请替换为你的 GitHub 用户名，名称必须小写）
export IMAGE_NAME="ghcr.io/yljos/sing-box"

# 构建并标记为 latest
# --platform 指定构建目标为 linux/amd64 (即 x86_64)
podman buildx build --platform linux/amd64 -t ${IMAGE_NAME}:latest .


podman push ${IMAGE_NAME}:latest
