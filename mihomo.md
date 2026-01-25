# 获取当前的 git tag 或分支名
VERSION=$(git describe --tags --always)
# 获取当前时间
TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# 带参数编译
CGO_ENABLED=0 go build -ldflags "-X 'github.com/metacubex/mihomo/constant.Version=${VERSION}' -X 'github.com/metacubex/mihomo/constant.BuildTime=${TIME}' -w -s -buildid="