# Newsletter Digest

A small scheduled AI agent. It reads newsletter emails from a Gmail inbox, turns each one into short story cards with Claude, merges stories that more than one newsletter covers, and serves the result as a single card page with a 10-day history.

## How it works

- A timer runs the job twice a day. Every email not yet processed is handled, so late or missed days catch up.
- Gmail access is read-only (`gmail.readonly`).
- Claude runs tool-less (`claude -p --tools ""`). It only turns email text into JSON.
- Every source URL on a card must appear in the email text, or it is dropped. Hosts you list in `BLOCKED_HOSTS` (newsletter and tracker domains) are never linked. Sponsor sections are skipped.
- Each story is a collapsible card with a short summary, source chips and a link to the original article when one exists. Light and dark themes follow the device.
- The last 10 days are kept in SQLite. The page is a dependency-free static front end served by a small standard-library Python server on loopback.

## Layout

    bin/digest.py        the job: fetch, extract, merge, store
    bin/gmail_read.py    read-only Gmail client (stdlib)
    bin/oauth_login.py   one-time Google sign-in (start / finish / revoke)
    bin/server.py        read-only JSON API + static files, 127.0.0.1:3026
    bin/static/          the page (index.html, style.css, app.js, theme.js, fonts, icons)
    deploy/              example systemd units
    secrets/             NOT in git: google-client.json, token-readonly.json, claude-token
    data/                NOT in git: news.db

## Configuration

| Variable | Purpose |
| --- | --- |
| `NEWSLETTER_SENDERS` | Comma-separated sender addresses to read. |
| `BLOCKED_HOSTS` | Comma-separated hosts that must never be linked. |
| `AI_NEWS_HOME` | Install directory (defaults to the repo). |
| `CLAUDE_BIN` | Path to the Claude Code CLI binary. |

The card page labels the two newsletters "Newsletter A" and "Newsletter B" (see `NAMES` in `bin/digest.py` and the constants at the top of `bin/static/app.js`). Rename them to match your senders.

## Setup (sketch)

1. Create a service user and `install -d -m 0700 secrets data`.
2. Create a Google OAuth desktop client, save it as `secrets/google-client.json`, then run `python3 -I bin/oauth_login.py start`, open the URL, and finish with `python3 -I bin/oauth_login.py finish '<redirected URL>'`.
3. Run `claude setup-token` and save the token to `secrets/claude-token` (mode 0600).
4. Adapt the units in `deploy/` for your paths and enable the timer. Put the web server behind your own reverse proxy and access control.
5. Backfill if you like: `python3 -I bin/digest.py run --backfill 7`.

## License

MIT
