import express from "express";
import fetch from "node-fetch";
import { JSDOM } from "jsdom";

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// フルページHTMLフォーム
app.get("/", (req, res) => {
  res.send(`
  <html><head><meta charset="UTF-8"><title>MYAFOWebプロキシ</title></head>
  <body>
    <h1>MYAFOWebプロキシ</h1>
    <form action="/proxy" method="post">
      <input type="text" name="url" placeholder="https://example.com">
      <button type="submit">送信</button>
    </form>
  </body></html>
  `);
});

// GET/POST共通ハンドラ
async function handleProxy(url, res) {
  if (!url) return res.status(400).send("URLを指定してください");

  try {
    const response = await fetch(url, { redirect: "manual" });
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get("location");
      if (location) {
        const newUrl = new URL(location, url).href;
        return res.send(`
          <html><body onload="submitForm()">
            <form id="f" method="POST" action="/proxy">
              <input type="hidden" name="url" value="${newUrl}">
            </form>
            <script>
            function submitForm() { document.getElementById('f').submit(); }
            </script>
          </body></html>
        `);
      }
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/html")) {
      const html = await response.text();
      const dom = new JSDOM(html);
      const document = dom.window.document;

      // タイトル偽装
      if (document.querySelector("title")) document.querySelector("title").textContent = "無題のページ";
      else {
        const t = document.createElement("title");
        t.textContent = "無題のページ";
        document.head.appendChild(t);
      }

      // favicon偽装
      document.querySelectorAll('link[rel*="icon"]').forEach(el => el.remove());
      const favicon = document.createElement("link");
      favicon.rel = "icon";
      favicon.href = "/proxy?url=https://example.com/favicon.ico";
      document.head.appendChild(favicon);

      // aタグ → JSでPOST
      document.querySelectorAll("a[href]").forEach(el => {
        const absUrl = new URL(el.getAttribute("href"), url).href;
        el.setAttribute("href", "#");
        el.setAttribute("onclick", `proxyPost('${absUrl}')`);
      });

      // formタグ → actionを書き換え
      document.querySelectorAll("form[action]").forEach(f => {
        const absUrl = new URL(f.getAttribute("action"), url).href;
        f.action = "/proxy";
        const hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = "url";
        hidden.value = absUrl;
        f.prepend(hidden);
      });

      // 画像・JS・CSS → GETで/proxy
      ["img", "script", "link"].forEach(tagName => {
        document.querySelectorAll(tagName).forEach(el => {
          const attr = tagName === "link" ? "href" : "src";
          if (!el.hasAttribute(attr)) return;
          const absUrl = new URL(el.getAttribute(attr), url).href;
          el.setAttribute(attr, `/proxy?url=${encodeURIComponent(absUrl)}`);
        });
      });

      // JS関数注入
      const script = document.createElement("script");
      script.textContent = `
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
      `;
      document.body.appendChild(script);

      res.set("Content-Type", "text/html");
      return res.send(dom.serialize());
    }

    // HTML以外はそのまま返す
    const buffer = await response.arrayBuffer();
    res.set("Content-Type", contentType);
    res.send(Buffer.from(buffer));
  } catch (err) {
    res.status(500).send("取得エラー: " + err);
  }
}

// GET/POST共通ルート
app.all("/proxy", async (req, res) => {
  const url = req.body.url || req.query.url;
  await handleProxy(url, res);
});

// Render対応ポート
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Proxyサーバー起動: http://localhost:${PORT}`));
