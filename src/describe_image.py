"""用 DeepSeek 视觉模型描述图片（当 pi 的"眼睛"）。

用法:
    python describe_image.py <图片路径> ["提问（可选）"]

从 ~/.pi/agent/auth.json 读取 deepseek 的 key，把图片 base64 后
发给 deepseek-v4-flash-vision-exp，打印模型的文字描述。
"""
import base64
import json
import os
import sys
import urllib.request

AUTH = os.path.expanduser("~/.pi/agent/auth.json")
MODEL = "deepseek-v4-flash-vision-exp"
BASE = "https://api.deepseek.com"


def load_key():
    with open(AUTH, encoding="utf-8") as f:
        d = json.load(f)
    cred = d.get("deepseek", {})
    return cred.get("key") or cred.get("apiKey") or ""


def call_vision(image_path, question):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    # 自动探测 mime
    ext = os.path.splitext(image_path)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp"}.get(ext, "image/png")
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        "max_tokens": 2000,
    }
    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {load_key()}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("用法: python describe_image.py <图片路径> [提问]")
    img = sys.argv[1]
    q = sys.argv[2] if len(sys.argv) > 2 else "请详细描述这张图片里的内容和排版情况。"
    print(call_vision(img, q))
