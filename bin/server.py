#!/usr/bin/env python3
"""Newsletter Digest web app: read-only JSON API + static page, loopback only. Run as the service user."""
import json, os, re, sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE = os.environ.get("AI_NEWS_HOME", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = f"{BASE}/data/news.db"
STATIC = f"{BASE}/bin/static"
PORT = int(os.environ.get("PORT", "3026"))
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".woff2": "font/woff2",
         ".svg": "image/svg+xml", ".png": "image/png"}


def q(sql, args=()):
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def api(path, qs):
    if path == "/api/days":
        return {"days": [{"day": d, "count": n} for d, n in q("select day, count(*) from cards group by day order by day desc limit 10")]}
    if path == "/api/day":
        d = (qs.get("d") or [""])[0]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            return None
        cards = [{"headline": h, "paragraph": p, "url": u, "sources": json.loads(s)}
                 for h, p, u, s in q("select headline, paragraph, url, sources from cards where day=? order by idx", (d,))]
        mails = [{"name": n, "subject": s} for n, s in q("select name, subject from emails where digest_day=? and status='ok' order by received_ms", (d,))]
        return {"day": d, "cards": cards, "emails": mails}
    if path == "/api/status":
        r = q("select ts, ok, note from runs order by ts desc limit 1")
        return {"last_run": ({"ts": r[0][0], "ok": bool(r[0][1]), "note": r[0][2]} if r else None)}
    return None


class H(BaseHTTPRequestHandler):
    server_version = "newsletter-digest"

    def log_message(self, *a):
        pass

    def send(self, code, body, ctype, cache="no-cache"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            try:
                out = api(u.path, parse_qs(u.query))
            except sqlite3.Error:
                out = {"days": [], "cards": [], "emails": [], "last_run": None}
            if out is None:
                return self.send(404, b'{"error":"not found"}', "application/json")
            return self.send(200, json.dumps(out).encode(), "application/json")
        name = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
        ext = os.path.splitext(name)[1]
        if not re.fullmatch(r"(fonts/)?[\w.-]+", name) or ext not in TYPES or not os.path.isfile(f"{STATIC}/{name}"):
            return self.send(404, b"not found", "text/plain")
        return self.send(200, open(f"{STATIC}/{name}", "rb").read(), TYPES[ext],
                         "public, max-age=2592000" if ext in (".woff2", ".svg", ".png") else "no-cache")


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
