from flask import Flask, request, Response, send_from_directory
import requests
import base64

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

@app.route("/icon.ico")
def icon():
    return send_from_directory(directory=".", path="icon.ico")

@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>弐紀Webプロキシ</title>
<link rel="icon" href="/icon.ico" type="image/x-icon">
</head>
<body>
<h1>Webプロキシ</h1>
<form method="get" action="/proxy">
<input type="text" name="b64" placeholder="Base64エンコード済URL">
<button type="submit">送信</button>
</form>
</body>
</html>
"""

@app.route("/proxy", methods=["GET","POST"])
def proxy():
    b64_url = request.args.get("b64") or request.form.get("b64")
    if not b64_url:
        return "URLを指定してください", 400
    try:
        url = base64.b64decode(b64_url).decode("utf-8")
    except Exception:
        return "Base64デコード失敗", 400

    try:
        # 元ページをそのまま返す
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        content_type = resp.headers.get("Content-Type", "text/html")
        return Response(resp.content, status=resp.status_code, content_type=content_type)
    except Exception as e:
        return f"エラー: {e}", 500

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080)
