"""Minimal read-only Gmail client for Newsletter Digest (stdlib only). Uses only gmail.readonly endpoints."""
import base64, json, os, time, urllib.error, urllib.parse, urllib.request

S = os.path.join(os.environ.get("AI_NEWS_HOME", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "secrets")
SENDERS = [s.strip() for s in os.environ.get("NEWSLETTER_SENDERS", "newsletter-a@example.com,newsletter-b@example.com").split(",") if s.strip()]
API = "https://gmail.googleapis.com/gmail/v1/users/me"


def access_token():
    c = json.load(open(f"{S}/google-client.json"))["installed"]
    t = json.load(open(f"{S}/token-readonly.json"))
    body = urllib.parse.urlencode({"client_id": c["client_id"], "client_secret": c["client_secret"],
                                   "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(c["token_uri"], data=body), timeout=30))["access_token"]


RETRY_WAITS = (5, 15, 30, 60, 90)   # seconds; the Gmail quota is per minute and shared with other apps on a Google project


def get(tok, path, **params):
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    for i in range(len(RETRY_WAITS) + 1):
        try:
            return json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            body = e.read()
            limited = e.code in (429, 500, 502, 503, 504) or (e.code == 403 and b"ateLimit" in body)
            if limited and i < len(RETRY_WAITS):
                time.sleep(RETRY_WAITS[i])
                continue
            raise


def search(tok, sender, newer_than="3d"):
    q = f"from:{sender} newer_than:{newer_than}"
    r = get(tok, "messages", q=q, maxResults=10)
    return [m["id"] for m in r.get("messages", [])]


def header(msg, name):
    for h in msg["payload"].get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _walk(part, out):
    mt = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if data and mt in ("text/html", "text/plain"):
        out.setdefault(mt, []).append(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace"))
    for p in part.get("parts", []) or []:
        _walk(p, out)


def fetch(tok, mid):
    """Returns dict: id, sender, subject, internal_ms, html, text."""
    m = get(tok, f"messages/{mid}", format="full")
    out = {}
    _walk(m["payload"], out)
    return {"id": mid, "sender": header(m, "From"), "subject": header(m, "Subject"),
            "internal_ms": int(m["internalDate"]),
            "html": "\n".join(out.get("text/html", [])), "text": "\n".join(out.get("text/plain", []))}
