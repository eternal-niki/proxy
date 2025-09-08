from flask import Flask, request, Response, send_from_directory
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import base64

app = Flask(__name__)

# ブラウザっぽく見せるためのヘッダ
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
            body { background-color: #121212; color: #f5f5f5; font-family: 'Segoe UI', sans-serif;
                   display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { text-align: center; background: #1e1e1e; padding: 40px; border-radius: 12px;
                         box-shadow: 0 0 20px rgba(0,0,0,0.7); width: 100%; max-width: 500px; }
            h1 { margin-bottom: 20px; font-size: 28px; color: #7fffd4; }
            label { font-size: 16px; margin-bottom: 8px; display: block; }
            input[type="text"] { width: 100%; padding: 12px; border: none; border-radius: 8px;
                                 margin-bottom: 12px; font-size: 16px; }
            button { background: #7fffd4; border: none; border-radius: 8px; padding: 12px 24px; font-size: 16px;
                     font-weight: bold; color: #121212; cursor: pointer; transition: background 0.3s; margin: 6px 0; }
            button:hover { background: #00aacc; }
            .output { background: #2a2a2a; padding: 10px; border-radius: 8px; margin-top: 10px;
                      word-break: break-all; font-family: monospace; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>弐紀Webプロキシ</h1>
            <form action="/proxy" method="post" id="proxyForm">
                <label for="url">URLを入力:</label>
                <input type="text" id="url" placeholder="https://example.com">
                <button type="button" onclick="encodeBase64()">Base64にエンコード</button>
                <div id="b64_output" class="output"></div>
                <input type="hidden" id="b64" name="b64">
                <button type="submit">送信</button>
            </form>
        </div>

        <script>
        function encodeBase64() {
            let rawUrl = document.getElementById("url").value.trim();
            if (!rawUrl) {
                alert("URLを入力してください");
                return;
            }
            try {
                let encoded = btoa(unescape(encodeURIComponent(rawUrl)));
                document.getElementById("b64").value = encoded;
                document.getElementById("b64_output").innerText = encoded;
            } catch (e) {
                alert("エンコードに失敗しました: " + e);
            }
        }
        </script>
    </body>
    </html>
    """


@app.route("/proxy", methods=["GET", "POST"])
def proxy():
    # URLをBase64から復元
    b64_url = request.form.get("b64") or request.args.get("b64")
    if not b64_url:
        return "Base64エンコードされたURLを指定してください", 400

    try:
        url = base64.b64decode(b64_url).decode("utf-8")
    except Exception:
        return "Base64デコード失敗", 400

    try:
        resp = requests.get(url, headers=HEADERS, allow_redirects=False)
        content_type = resp.headers.get("Content-Type", "")

        # リダイレクトをPOSTで処理
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location")
            if location:
                new_url = urljoin(url, location)
                new_b64 = base64.b64encode(new_url.encode("utf-8")).decode("utf-8")
                html = f"""
                <html>
                <body onload="redirectPost('{new_b64}')">
                    <noscript>
                        <form action="/proxy" method="post">
                            <input type="hidden" name="b64" value="{new_b64}">
                            <button type="submit">Continue</button>
                        </form>
                    </noscript>
                </body>
                </html>
                <script>
                function redirectPost(b64) {{
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
                }}
                </script>
                """
                return Response(html, content_type="text/html")

        if "text/html" in content_type:
            soup = BeautifulSoup(resp.text, "html.parser")
            base_url = resp.url

            # ===== リンクをJS経由POSTに =====
            for tag in soup.find_all("a", href=True):
                abs_url = urljoin(base_url, tag["href"])
                if abs_url.startswith("http"):
                    abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                    tag["href"] = "#"
                    tag["onclick"] = f"proxyPost('{abs_b64}')"

            # ===== フォームを/proxyに変更 + hidden input =====
            for form in soup.find_all("form", action=True):
                abs_url = urljoin(base_url, form["action"])
                abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                form["action"] = "/proxy"
                for existing in form.find_all("input", attrs={"name": "b64"}):
                    existing.decompose()
                hidden = soup.new_tag("input", attrs={
                    "type": "hidden",
                    "name": "b64",
                    "value": abs_b64
                })
                form.insert(0, hidden)

            # ===== 画像・CSS・JSをGET経由/proxyに =====
            for tag in soup.find_all(["img", "script", "link"]):
                attr = "href" if tag.name == "link" else "src"
                if tag.has_attr(attr):
                    abs_url = urljoin(base_url, tag[attr])
                    if abs_url.startswith("http"):
                        abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                        tag[attr] = f"/proxy?b64={abs_b64}"

            # ===== JS関数 & 広告ブロック注入 =====
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
                const adSelectors = [
                    '.c-ad','.c-ad__item-horizontal','[id^="gnpbad_"]','[data-gninstavoid]',
                    '[data-cptid]','.adsbygoogle','[id^="ads-"]','.ad-container','.ad-slot',
                    '.sponsored','.promotion','iframe[src*="ads"]','iframe[src*="doubleclick"]',
                    'iframe[src*="googlesyndication.com"]','div[id^="taboola-"]','.taboola',
                    '.outbrain','div[id^="ob-"]','script[src*="genieesspv.jp"]',
                    'script[src*="imobile.co.jp"]','script[src*="imp-adedge.i-mobile.co.jp"]',
                    '[id^="_geniee"]','[id^="im-"]','[id^="ad_"]','#ad_closed_panel',
                    '[id^="google_ads_iframe_"]','#m2c-ad-parent-detail-page','.yads_ad',
                    '.yads_ad_res_l','ytd-in-feed-ad-layout-renderer','.ytd-ad-slot-renderer',
                    '#player-ads','#pb_template','[data-avm-id^="IFRAME-"]',
                    '.adsSectionOuterWrapper','.adWrapper.BaseAd--adWrapper--ANZ1O.BaseAd--card--cqv7t',
                    '.ci-bg-17992.ci-adhesion.ci-ad.ci-ad-4881','.top-ads-container.sticky-top',
                    '.AuroraVisionContainer-ad','.adthrive-auto-injected-player-container.adthrive-collapse-player',
                    '.adthrive','.AdThrive_Footer_1_desktop','.ad_300x250','[id^="bnc_ad_"][id$="_iframe"]',
                    '[id^="AD_"]','script[src*="ad.ad-stir.com/ad"]','[id^="adstir_inview_"]',
                    'iframe[src*="gmossp-sp.jp"]','#newAd_300x250','style-scope ytd-item-section-renderer'
                ];
                const removeAds = () => {
                    adSelectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => el.remove());
                    });
                };
                removeAds();
                setInterval(removeAds, 1000);
                const observer = new MutationObserver(() => removeAds());
                observer.observe(document.body, { childList: true, subtree: true });
            })();
            """
            if soup.body:
                soup.body.append(script_tag)

            return Response(str(soup), status=resp.status_code, content_type=content_type)

        return Response(resp.content, status=resp.status_code, content_type=content_type)

    except Exception as e:
        return f"エラー: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
