#!/usr/bin/env python3
"""Read-only Gmail login for Newsletter Digest. Run as the service user.

  oauth_login.py start              -> prints the consent URL
  oauth_login.py finish '<URL>'     -> saves secrets/token-readonly.json
  oauth_login.py revoke             -> revokes the login at Google and deletes the token file

Only the exact gmail.readonly scope is accepted.
"""
import base64, hashlib, json, os, secrets, sys, urllib.parse, urllib.request

S = os.path.join(os.environ.get("AI_NEWS_HOME", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "secrets")
CLIENT, PENDING, TOKEN = f"{S}/google-client.json", f"{S}/pending-auth.json", f"{S}/token-readonly.json"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
REDIRECT = "http://localhost:8765"


def client():
    return json.load(open(CLIENT))["installed"]


def write_private(path, obj):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)


def start():
    c = client()
    v = secrets.token_urlsafe(64)
    ch = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()
    st = secrets.token_urlsafe(24)
    write_private(PENDING, {"verifier": v, "state": st})
    print("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": st, "code_challenge": ch, "code_challenge_method": "S256"}))


def finish(url):
    c, pend = client(), json.load(open(PENDING))
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if qs.get("error"):
        sys.exit("Google returned an error: " + qs["error"][0])
    if qs.get("state", [""])[0] != pend["state"]:
        sys.exit("State mismatch: start over.")
    body = urllib.parse.urlencode({"code": qs["code"][0], "client_id": c["client_id"], "client_secret": c["client_secret"],
                                   "redirect_uri": REDIRECT, "grant_type": "authorization_code",
                                   "code_verifier": pend["verifier"]}).encode()
    tok = json.load(urllib.request.urlopen(urllib.request.Request(c["token_uri"], data=body)))
    if tok.get("scope", "").strip() != SCOPE:
        sys.exit("Unexpected scopes granted: " + tok.get("scope", "") + " (refusing to save)")
    if "refresh_token" not in tok:
        sys.exit("No refresh token returned; start over.")
    write_private(TOKEN, {"refresh_token": tok["refresh_token"], "scope": tok["scope"]})
    os.remove(PENDING)
    print("Read-only login saved.")


def revoke():
    t = json.load(open(TOKEN))["refresh_token"]
    try:
        urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/revoke",
                               data=urllib.parse.urlencode({"token": t}).encode()))
        print("Revoked at Google.")
    except Exception as e:
        print("Revoke call failed (revoke manually at myaccount.google.com/permissions):", e)
    os.remove(TOKEN)
    print("Token file deleted.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["start"]:
        start()
    elif a[:1] == ["finish"] and len(a) == 2:
        finish(a[1])
    elif a[:1] == ["revoke"]:
        revoke()
    else:
        sys.exit(__doc__)
