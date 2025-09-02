import express from "express";
import fetch from "node-fetch";
import { JSDOM } from "jsdom";

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// GET/POST両対応でプロキシ
async function handleProxy(url, res) {
  if (!url) return res.status(400).send("URLが必要です");

  try {
    const response = await fetch(url);
    const html = await response.text();

    const dom = new JSDOM(html);
    const document = dom.window.document;

    // 画像・CSS・JSリンクを書き換え
    const attrs = ["src", "href"];
    attrs.forEach(attr => {
      const elements = document.querySelectorAll(`[${attr}]`);
      elements.forEach(el => {
        const original = el.getAttribute(attr);
        if (!original) return;
        const absUrl = new URL(original, url).href;
        el.setAttribute(attr, `/resource?url=${encodeURIComponent(absUrl)}`);
      });
    });

    res.set("Access-Control-Allow-Origin", "*"); // CORS対応
    res.send(dom.serialize());
  } catch (err) {
    res.status(500).send("取得エラー");
  }
}

// POSTプロキシ
app.post("/proxy", async (req, res) => {
  await handleProxy(req.body.url, res);
});

// GETプロキシ（iframeなどURL指定用）
app.get("/proxy", async (req, res) => {
  await handleProxy(req.query.url, res);
});

// リソース取得用
app.get("/resource", async (req, res) => {
  const url = req.query.url;
  if (!url) return res.status(400).send("URLが必要です");

  try {
    const response = await fetch(url);
    const contentType = response.headers.get("content-type");
    res.set("Content-Type", contentType);
    res.set("Access-Control-Allow-Origin", "*"); // CORS対応

    const buffer = await response.arrayBuffer();
    res.send(Buffer.from(buffer));
  } catch (err) {
    res.status(500).send("取得エラー");
  }
});

// フォームとiframeサンプルページ
app.get("/", (req, res) => {
  res.send(`
    <h2>フルページPOST/GETプロキシ</h2>
    <form method="POST" action="/proxy" target="proxyFrame">
      <input type="text" name="url" placeholder="アクセスしたいURL" style="width:300px"/>
      <button type="submit">Go (POST)</button>
    </form>
    <form method="GET" action="/proxy" target="proxyFrame">
      <input type="text" name="url" placeholder="アクセスしたいURL" style="width:300px"/>
      <button type="submit">Go (GET)</button>
    </form>
    <iframe name="proxyFrame" width="100%" height="800"></iframe>
  `);
});

app.listen(3000, () => {
  console.log("POST/GETフルページプロキシサーバー起動: http://localhost:3000");
});
