from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)


@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>MYAFOWebプロキシ</title>
        <style>
            body {
                background-color: #121212;
                color: #f5f5f5;
                font-family: 'Segoe UI', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                text-align: center;
                background: #1e1e1e;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 0 20px rgba(0,0,0,0.7);
            }
            h1 {
                margin-bottom: 20px;
                font-size: 28px;
                color: #00d8ff;
            }
            label {
                font-size: 16px;
                margin-bottom: 8px;
                display: block;
            }
            input[type="text"] {
                width: 100%;
                max-width: 400px;
                padding: 12px;
                border: none;
                border-radius: 8px;
                margin-bottom: 20px;
                font-size: 16px;
            }
            button {
                background: #00d8ff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                color: #121212;
                cursor: pointer;
                transition: background 0.3s;
            }
            button:hover {
                background: #00aacc;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>MYAFOWebプロキシ</h1>
            <form action="/proxy" method="post">
                <label for="url">URLを入力:</label>
                <input type="text" id="url" name="url" placeholder="https://example.com">
                <br>
                <button type="submit">送信</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.route("/proxy", methods=["GET", "POST"])
def proxy():
    # 送られてきたURLを取得
    url = request.form.get("url") or request.args.get("url")
    if not url:
        return "urlを指定してください", 400

    try:
        # GETはリダイレクトさせずに取得
        resp = requests.get(url, allow_redirects=False)
        content_type = resp.headers.get("Content-Type", "")

        # リダイレクトを検出
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location")
            if location:
                # 絶対URLに変換
                new_url = urljoin(url, location)
                # ブラウザでPOSTさせるフォームを返す
                html = f"""
                <html>
                <body onload="redirectPost('{new_url}')">
                    <noscript>
                        <form action="/proxy" method="post">
                            <input type="hidden" name="url" value="{new_url}">
                            <button type="submit">Continue</button>
                        </form>
                    </noscript>
                </body>
                </html>
                <script>
                function redirectPost(targetUrl) {{
                    var f = document.createElement('form');
                    f.method = 'POST';
                    f.action = '/proxy';
                    var i = document.createElement('input');
                    i.type = 'hidden';
                    i.name = 'url';
                    i.value = targetUrl;
                    f.appendChild(i);
                    document.body.appendChild(f);
                    f.submit();
                }}
                </script>
                """
                return Response(html, content_type="text/html")

        # HTMLの場合はリンク・フォーム・リソースを書き換える
        if "text/html" in content_type:
            soup = BeautifulSoup(resp.text, "html.parser")
            base_url = resp.url

            # ===== タイトル偽装 =====
            if soup.title:
                soup.title.string = "無題のページ"
            else:
                new_title = soup.new_tag("title")
                new_title.string = "無題のページ"
                if soup.head:
                    soup.head.append(new_title)

            # ===== favicon偽装 =====
            for link in soup.find_all("link", rel=lambda x: x and "icon" in x):
                link.decompose()
            favicon = soup.new_tag(
                "link",
                rel="icon",
                href="/proxy?url=https://example.com/favicon.ico")
            if soup.head:
                soup.head.append(favicon)

            # リンク → JS経由POST
            for tag in soup.find_all("a", href=True):
                abs_url = urljoin(base_url, tag["href"])
                tag["href"] = "#"
                tag["onclick"] = f"proxyPost('{abs_url}')"

            # フォーム → actionを/proxyに変更してhiddenでURL埋め込む
            for form in soup.find_all("form", action=True):
                abs_url = urljoin(base_url, form["action"])
                form["action"] = "/proxy"
                hidden = soup.new_tag("input",
                                      type="hidden",
                                      name="url",
                                      value=abs_url)
                form.insert(0, hidden)

            # 画像・CSS・JS → GET経由で/proxyに
            for tag in soup.find_all(["img", "script", "link"]):
                attr = "href" if tag.name == "link" else "src"
                if tag.has_attr(attr):
                    abs_url = urljoin(base_url, tag[attr])
                    tag[attr] = f"/proxy?url={abs_url}"

            # JS関数を注入（リンククリック用POST）
            script_tag = soup.new_tag("script")
            script_tag.string = """
            function proxyPost(url) {
                var f = document.createElement('form');
                f.method = 'POST';
                f.action = '/proxy';
                var i = document.createElement('input');
                i.type = 'hidden';
                i.name = 'url';
                i.value = url;
                f.appendChild(i);
                document.body.appendChild(f);
                f.submit();
            }
            """
            if soup.body:
                soup.body.append(script_tag)

            return Response(str(soup),
                            status=resp.status_code,
                            content_type=content_type)

        # HTML以外（画像、CSS、JSなど）はそのまま返す
        return Response(resp.content,
                        status=resp.status_code,
                        content_type=content_type)

    except Exception as e:
        return f"エラー: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
