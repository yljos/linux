#!/bin/sh
# Minimal OpenNDS Theme

title="theme_minimal"
EXPECTED_NAME="aaa"

generate_splash_sequence() {
    [ "$mypassword" = "$EXPECTED_NAME" ] && landing_page || login_form
}

header() {
    echo "<!DOCTYPE html><html><head><meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Wi-Fi</title>
    <style>body{text-align:center;font-family:sans-serif;margin-top:20vh;background:#f4f4f9}input{margin:10px;padding:8px}</style>
    </head><body>"
}

footer() {
    echo "</body></html>"
    exit 0
}

login_form() {
    header
    echo "<h2>网络认证</h2>
    <p>请输入关键词</p>
    <form action=\"/opennds_preauth/\" method=\"get\">
        <input type=\"hidden\" name=\"fas\" value=\"$fas\">
        <input type=\"text\" name=\"mypassword\" required>
        <br><input type=\"submit\" value=\"开始认证\">
    </form>"
    footer
}

landing_page() {
    # Auth device
    /usr/bin/ndsctl auth "$clientmac"
    
    header
    echo "<h2 style=\"color:green\">验证成功</h2><p>已连网，请关闭此页面。</p>"
    footer
}

# Standard configuration mapping
session_length="0"
upload_rate="0"
download_rate="0"
upload_quota="0"
download_quota="0"
quotas="$session_length $upload_rate $download_rate $upload_quota $download_quota"
ndscustomparams=""
ndscustomimages=""
ndscustomfiles=""
ndsparamlist="$ndsparamlist $ndscustomparams $ndscustomimages $ndscustomfiles"

# Register custom input field
additionalthemevars="mypassword"
fasvarlist="$fasvarlist $additionalthemevars"
userinfo="$title"