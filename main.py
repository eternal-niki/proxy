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
:root { --bg:#121212;--card:#1e1e1e;--accent:#7fffd4;--muted:#555; }
html,body{height:100%;margin:0;}
body{background:var(--bg);color:#f5f5f5;font-family:'Segoe UI', Roboto, 'Noto Sans JP', sans-serif;}
.wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;box-sizing:border-box;}
.card{width:100%;max-width:640px;background:var(--card);padding:32px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.6);}
h1{margin:0 0 18px 0;color:var(--accent);font-size:26px;}
label.base{display:block;margin-bottom:12px;font-size:15px;color:#ddd;}
input[type="text"]{width:100%;padding:12px 14px;border-radius:10px;border:none;background:#121212;color:#fff;font-size:15px;box-sizing:border-box;}
.controls{display:flex;gap:12px;margin-top:14px;align-items:center;}
button{background:var(--accent);border:none;border-radius:10px;padding:10px 18px;font-weight:700;color:#0a0a0a;cursor:pointer;}
button:hover{filter:brightness(0.95);}
.output{margin-top:12px;background:#2a2a2a;padding:10px;border-radius:8px;word-break:break-all;font-family:monospace;font-size:13px;color:#e8e8e8;}
footer{text-align:center;color:var(--muted);font-size:12px;margin-top:12px;}
.switch-row{display:flex;align-items:center;gap:12px;margin-top:12px;}
.switch{position:relative;width:56px;height:30px;background:#2b2b2b;border-radius:999px;cursor:pointer;transition:background .2s;}
.switch.on{background:linear-gradient(90deg,#2dd4bf,#00aacc);}
.switch .knob{position:absolute;top:3px;left:3px;width:24px;height:24px;background:#fff;border-radius:50%;transition:transform .18s;}
.switch.on .knob{transform:translateX(26px);}
.switch-label{font-size:14px;color:#ddd;}
@media(max-width:520px){.card{padding:20px;}.controls{flex-direction:column;align-items:stretch;}}
</style>
</head>
<body>
<div class="wrap">
<div class="card">
<h1>Webプロキシ</h1>
<form id="proxyForm" onsubmit="return submitProxy();">
<label class="base" for="url">URLを入力：</label>
<input type="text" id="url" name="target_url" placeholder="https://example.com">
<div class="switch-row" style="justify-content:space-between;">
<div style="display:flex;align-items:center;gap:10px;">
<div id="toggle" class="switch on" onclick="toggleOriginalMeta()"><div class="knob"></div></div>
<div class="switch-label">元サイトのタイトル/ファビコンを使う</div>
</div>
<div style="font-size:13px;color:#bdbdbd;">トグルON = 元サイトの meta を尊重</div>
</div>
<div class="controls">
<button type="button" onclick="encodeBase64()">エンコード</button>
<button type="submit">送信</button>
</div>
<input type="hidden" id="b64" name="b64">
<input type="hidden" id="original_meta" name="original_meta" value="true">
<div id="b64_output" class="output"></div>
</form>
<footer>v1.3.5β</footer>
</div>
</div>

<script>
let originalMeta = true;
function setToggleVisual(){const el=document.getElementById("toggle");if(originalMeta) el.classList.add("on");else el.classList.remove("on");document.getElementById("original_meta").value = originalMeta?"true":"false";}
function toggleOriginalMeta(){originalMeta=!originalMeta;setToggleVisual();}
setToggleVisual();

function encodeBase64(){
let rawUrl=document.getElementById("url").value.trim();
if(!rawUrl){alert("URLを入力してください");return;}
try{
let encoded=btoa(unescape(encodeURIComponent(rawUrl)));
document.getElementById("b64").value=encoded;
let fullUrl=location.origin+"/proxy?b64="+encoded+"&type=get&encodetype=https";
if(originalMeta) fullUrl+="&original_meta=true";
document.getElementById("b64_output").innerText=fullUrl;
}catch(e){alert("エンコードに失敗しました:"+e);}
}

function submitProxy(){
let rawUrl=document.getElementById("url").value.trim();
if(!rawUrl){alert("URLを入力してください");return false;}
let encoded=btoa(unescape(encodeURIComponent(rawUrl)));
let finalUrl="/proxy?b64="+encoded+"&type=get";
if(originalMeta) finalUrl+="&original_meta=true";
window.location.href=finalUrl;
return false;
}
</script>
</body>
</html>
"""

@app.route("/proxy", methods=["GET","POST"])
def proxy():
    url = request.form.get("target_url")
    if url:
        req_type = "post"
    else:
        b64_url = request.form.get("b64") or request.args.get("b64")
        if not b64_url:
            return "URLを指定してください",400
        try:
            url = base64.b64decode(b64_url).decode("utf-8")
        except:
            return "Base64デコード失敗",400
        req_type = request.args.get("type") or request.form.get("type") or "post"

    encode_https = (request.args.get("encodetype")=="https") or (request.form.get("encodetype")=="https")
    use_original_meta = (request.args.get("original_meta")=="true") or (request.form.get("original_meta")=="true")

    try:
        resp = requests.get(url, headers=HEADERS, allow_redirects=False, timeout=15)
        resp.encoding = resp.apparent_encoding
        content_type = resp.headers.get("Content-Type","")
        if "text/html" in content_type:
            soup = BeautifulSoup(resp.text,"html.parser")
            base_url = resp.url

            # aタグ書き換え
            for tag in soup.find_all("a", href=True):
                abs_url = urljoin(base_url, tag["href"])
                if encode_https and abs_url.startswith("http://"):
                    abs_url = "https://" + abs_url[len("http://"):]
                if tag.has_attr("onclick") and "submit" in tag["onclick"]:
                    continue
                if abs_url.startswith("http") or "/search.html" in abs_url:
                    abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                    tag["href"] = f"/proxy?b64={abs_b64}&type=get" \
                        + ("&encodetype=https" if encode_https else "") \
                        + ("&original_meta=true" if use_original_meta else "")

            # form書き換え
            for form in soup.find_all("form", action=True):
                if form.get("name") == "player_form":  # JS依存フォームは書き換えない
                    continue
                abs_url = urljoin(base_url, form["action"])
                if encode_https and abs_url.startswith("http://"):
                    abs_url = "https://" + abs_url[len("http://"):]
                abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                form["action"] = "/proxy"
                for existing in form.find_all("input", attrs={"name":"b64"}):
                    existing.decompose()
                hidden = soup.new_tag("input", attrs={"type":"hidden","name":"b64","value":abs_b64})
                form.insert(0, hidden)
                if encode_https:
                    hidden_type = soup.new_tag("input", attrs={"type":"hidden","name":"encodetype","value":"https"})
                    form.insert(1, hidden_type)
                hidden_meta = soup.new_tag("input", attrs={"type":"hidden","name":"original_meta","value":"true" if use_original_meta else "false"})
                form.insert(2, hidden_meta)

            # img / script / link / iframe 書き換え
            for tag in soup.find_all(["img","script","link","iframe"]):
                attr = "href" if tag.name=="link" else "src"
                if tag.has_attr(attr):
                    abs_url = urljoin(base_url, tag[attr])
                    if encode_https and abs_url.startswith("http://"):
                        abs_url = "https://" + abs_url[len("http://"):]
                    if abs_url.startswith("http"):
                        abs_b64 = base64.b64encode(abs_url.encode("utf-8")).decode("utf-8")
                        tag[attr] = f"/proxy?b64={abs_b64}&type=get" \
                            + ("&encodetype=https" if encode_https else "") \
                            + ("&original_meta=true" if use_original_meta else "")

            # 広告除去 & proxyPost スクリプト
            script_tag = soup.new_tag("script")
            script_tag.string = """
function proxyPost(b64,use_original_meta){
var f=document.createElement('form');f.method='POST';f.action='/proxy';
var i=document.createElement('input');i.type='hidden';i.name='b64';i.value=b64;f.appendChild(i);
var m=document.createElement('input');m.type='hidden';m.name='original_meta';m.value=use_original_meta?'true':'false';f.appendChild(m);
document.body.appendChild(f);f.submit();}

(function(){
const adSelectors=['.c-ad','.c-ad__item-horizontal','[id^="gnpbad_"]','[data-gninstavoid]','[data-cptid]','.adsbygoogle','[id^="ads-"]','.ad-container','.ad-slot','.sponsored','.promotion','iframe[src*="ads"]','iframe[src*="doubleclick"]','iframe[src*="googlesyndication.com"]','div[id^="taboola-"]','.taboola','.outbrain','div[id^="ob-"]','script[src*="genieesspv.jp"]','script[src*="imobile.co.jp"]','script[src*="imp-adedge.i-mobile.co.jp"]','[id^="_geniee"]','[id^="im-"]','[id^="ad_"]','#ad_closed_panel','[id^="google_ads_iframe_"]','#m2c-ad-parent-detail-page','.yads_ad','.yads_ad_res_l','ytd-in-feed-ad-layout-renderer','.ytd-ad-slot-renderer','#player-ads','#pb_template','[data-avm-id^="IFRAME-"]','.adsSectionOuterWrapper','.adWrapper.BaseAd--adWrapper--ANZ1O.BaseAd--card--cqv7t','.ci-bg-17992.ci-adhesion.ci-ad.ci-ad-4881','.top-ads-container.sticky-top','.AuroraVisionContainer-ad','.adthrive-auto-injected-player-container.adthrive-collapse-player','.adthrive','.AdThrive_Footer_1_desktop','.ad_300x250','[id^="bnc_ad_"][id$="_iframe"]','[id^="AD_"]','script[src*="ad.ad-stir.com/ad"]','[id^="adstir_inview_"]',"iframe[src*='gmossp-sp.jp']",'#newAd_300x250','style-scope ytd-item-section-renderer','[id^="bnc_ad_"]'];
const removeAds=()=>{adSelectors.forEach(selector=>{document.querySelectorAll(selector).forEach(el=>el.remove());});};
removeAds();setInterval(removeAds,1000);const observer=new MutationObserver(()=>removeAds());observer.observe(document.body,{childList:true,subtree:true});
})();
"""
            if soup.body: soup.body.append(script_tag)

            return Response(str(soup), status=resp.status_code, content_type="text/html; charset=utf-8")

        return Response(resp.content, status=resp.status_code, content_type=content_type)

    except Exception as e:
        return f"エラー: {e}",500

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080)
