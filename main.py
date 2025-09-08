from flask import Flask, request, Response, send_from_directory
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
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
        <style>
            .body { background-color: #121212; color: #f5f5f5; font-family: 'Segoe UI', sans-serif;
                   display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { text-align: center; background: #1e1e1e; padding: 40px; border-radius: 12px;
                         box-shadow: 0 0 20px rgba(0,0,0,0.7); width: 100%; max-width: 500px; }
            h1 { margin-bottom: 20px; font-size: 28px; color: #7fffd4; }
            label { font-size: 16px; margin-bottom: 8px; display: block; }
            input[type="text"] { width: 100%; padding: 12px; border: none; border-radius: 8px;
                                 margin-bottom: 12px; font-size: 16px; }
            .button-row { display: flex; justify-content: space-between; margin-bottom: 12px; }
            button { background: #7fffd4; border: none; border-radius: 8px; padding: 12px 24px; font-size: 16px;
                     font-weight: bold; color: #121212; cursor: pointer; transition: background 0.3s; }
            button:hover { background: #00aacc; }
            .output { background: #2a2a2a; padding: 10px; border-radius: 8px; margin-top: 10px;
                      word-break: break-all; font-family: monospace; font-size: 14px; }
        </style>
    </head>
    <body>
		<div class=body>
        <div class="container">
            <h1>弐紀Webプロキシ</h1>
            <form action="/proxy" method="post" id="proxyForm">
                <label for="url">URLを入力:</label>
                <input type="text" id="url" name="target_url" placeholder="https://example.com">
                <div class="button-row">
                    <button type="button" onclick="encodeBase64()">エンコード</button>
                    <button type="submit">送信</button>
                </div>
                <input type="hidden" id="b64" name="b64">
                <div id="b64_output" class="output"></div>
            </form>
        </div>
		</div>
		<footer style="text-align:center; font-size:12px; color:#555; margin-top:20px; ">
    		v1.0.0
		</footer>

        <script>
        function encodeBase64() {
            let rawUrl = document.getElementById("url").value.trim();
            if (!rawUrl) { alert("URLを入力してください"); return; }
            try {
                let encoded = btoa(unescape(encodeURIComponent(rawUrl)));
                document.getElementById("b64").value = encoded;
                let fullUrl = "https://proxy-xvup.onrender.com/proxy?b64=" + encoded + "&type=get";
                document.getElementById("b64_output").innerText = fullUrl;
            } catch(e) { alert("エンコードに失敗しました: " + e); }
        }
        </script>
    </body>
    </html>
    """

@app.route("/proxy", methods=["GET", "POST"])
def proxy():
    url = request.form.get("target_url")
    if url:
        req_type = "post"
    else:
        b64_url = request.form.get("b64") or request.args.get("b64")
        if not b64_url:
            return "URLを指定してください", 400
        try:
            url = base64.b64decode(b64_url).decode("utf-8")
        except Exception:
            return "Base64デコード失敗", 400
        req_type = request.args.get("type") or request.form.get("type") or "post"

    # encodetype=https チェック
    encode_https = request.args.get("encodetype") == "https"

    try:
        resp = requests.get(url, headers=HEADERS, allow_redirects=False)
        resp.encoding = resp.apparent_encoding  # 元サイトの文字コード自動判定
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" in content_type:
            soup = BeautifulSoup(resp.text, "html.parser")
            base_url = resp.url

            for tag in soup.find_all("a", href=True):
                abs_url = urljoin(base_url, tag["href"])
                if encode_https and abs_url.startswith("http://"):
                    abs_url = "https://" + abs_url[len("http://"):]
                if abs_url.startswith("http"):
                    abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                    if req_type == "get":
                        tag["href"] = f"/proxy?b64={abs_b64}&type=get"
                        if encode_https:
                            tag["href"] += "&encodetype=https"
                    else:
                        tag["href"] = "#"
                        tag["onclick"] = f"proxyPost('{abs_b64}')"

            for form in soup.find_all("form", action=True):
                abs_url = urljoin(base_url, form["action"])
                if encode_https and abs_url.startswith("http://"):
                    abs_url = "https://" + abs_url[len("http://"):]
                abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                form["action"] = "/proxy"
                for existing in form.find_all("input", attrs={"name": "b64"}):
                    existing.decompose()
                hidden = soup.new_tag("input", attrs={"type": "hidden", "name": "b64", "value": abs_b64})
                form.insert(0, hidden)
                # フォーム送信でも encodetype を引き継ぎたい場合
                if encode_https:
                    hidden_type = soup.new_tag("input", attrs={"type": "hidden", "name": "encodetype", "value": "https"})
                    form.insert(1, hidden_type)

            for tag in soup.find_all(["img", "script", "link","iframe"]):
                attr = "href" if tag.name == "link" else "src"
                if tag.has_attr(attr):
                    abs_url = urljoin(base_url, tag[attr])
                    if encode_https and abs_url.startswith("http://"):
                        abs_url = "https://" + abs_url[len("http://"):]
                    if abs_url.startswith("http"):
                        abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                        tag[attr] = f"/proxy?b64={abs_b64}&type=get"
                        if encode_https:
                            tag[attr] += "&encodetype=https"

            script_tag = soup.new_tag("script")
            script_tag.string = """
            function proxyPost(b64) {
                var f = document.createElement('form');
                f.method = 'POST';
                f.action = '/proxy';
                var i = document.createElement('input');
                i.type = 'hidden';
                i.name = 'b64';
                i.value = b64;
                f.appendChild(i);
                document.body.appendChild(f);
                f.submit();
            }
            (function() {
                const adSelectors = [...]; // 省略
                const removeAds = () => { adSelectors.forEach(s => document.querySelectorAll(s).forEach(e=>e.remove())); };
                removeAds(); setInterval(removeAds, 1000);
                const observer = new MutationObserver(()=>removeAds());
                observer.observe(document.body,{ childList:true,subtree:true });
            })();
            """
            if soup.body:
                soup.body.append(script_tag)

            return Response(str(soup), status=resp.status_code, content_type="text/html; charset=utf-8")

        return Response(resp.content, status=resp.status_code, content_type=content_type)

    except Exception as e:
        return f"エラー: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
