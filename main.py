from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title弐紀Webプロキシ</title>
        <link rel="icon" href="/icon.ico" type="image/x-icon">
        <style>
            body { background-color: #121212; color: #f5f5f5; font-family: 'Segoe UI', sans-serif;
                   display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { text-align: center; background: #1e1e1e; padding: 40px; border-radius: 12px;
                         box-shadow: 0 0 20px rgba(0,0,0,0.7); }
            h1 { margin-bottom: 20px; font-size: 28px; color: #7fffd4; }
            label { font-size: 16px; margin-bottom: 8px; display: block; }
            input[type="text"] { width: 100%; max-width: 400px; padding: 12px; border: none; border-radius: 8px;
                                 margin-bottom: 20px; font-size: 16px; }
            button { background: #7fffd4; border: none; border-radius: 8px; padding: 12px 24px; font-size: 16px;
                     font-weight: bold; color: #121212; cursor: pointer; transition: background 0.3s; }
            button:hover { background: #00aacc; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>弐紀Webプロキシ</h1>
            <form action="/proxy" method="post">
                <label for="url">URLを入力:</label>
                <input type="text" id="url" name="target_url" placeholder="https://example.com">
                <br>
                <button type="submit">送信</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.route("/proxy", methods=["GET", "POST"])
def proxy():
    url = request.form.get("target_url") or request.args.get("target_url")
    if not url:
        return "URLを指定してください", 400

    try:
        resp = requests.get(url, headers=HEADERS, allow_redirects=False)
        content_type = resp.headers.get("Content-Type", "")

        # リダイレクトをPOSTで処理
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location")
            if location:
                new_url = urljoin(url, location)
                html = f"""
                <html>
                <body onload="redirectPost('{new_url}')">
                    <noscript>
                        <form action="/proxy" method="post">
                            <input type="hidden" name="target_url" value="{new_url}">
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
                    i.name = 'target_url';
                    i.value = targetUrl;
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
                attrs={
                    "rel": "icon",
                    "href": "/proxy?target_url=https://example.com/favicon.ico"
                })
            if soup.head:
                soup.head.append(favicon)

            # ===== リンクをJS経由POSTに =====
            for tag in soup.find_all("a", href=True):
                abs_url = urljoin(base_url, tag["href"])
                if abs_url.startswith("http"):
                    tag["href"] = "#"
                    tag["onclick"] = f"proxyPost('{abs_url}')"

            # ===== フォームを/proxyに変更 + hidden input =====
            for form in soup.find_all("form", action=True):
                abs_url = urljoin(base_url, form["action"])
                form["action"] = "/proxy"
                for existing in form.find_all("input",
                                              attrs={"name": "target_url"}):
                    existing.decompose()
                hidden = soup.new_tag("input",
                                      attrs={
                                          "type": "hidden",
                                          "name": "target_url",
                                          "value": abs_url
                                      })
                form.insert(0, hidden)

            # ===== 画像・CSS・JSをGET経由/proxyに =====
            for tag in soup.find_all(["img", "script", "link"]):
                attr = "href" if tag.name == "link" else "src"
                if tag.has_attr(attr):
                    abs_url = urljoin(base_url, tag[attr])
                    if abs_url.startswith("http"):
                        tag[attr] = f"/proxy?target_url={abs_url}"

            # ===== JS関数 & 広告ブロック注入 =====
            script_tag = soup.new_tag("script")
            script_tag.string = """
            function proxyPost(url) {
                var f = document.createElement('form');
                f.method = 'POST';
                f.action = '/proxy';
                var i = document.createElement('input');
                i.type = 'hidden';
                i.name = 'target_url';
                i.value = url;
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

            return Response(str(soup),
                            status=resp.status_code,
                            content_type=content_type)

        return Response(resp.content,
                        status=resp.status_code,
                        content_type=content_type)

    except Exception as e:
        return f"エラー: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
