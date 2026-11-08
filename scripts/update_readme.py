"""Refreshes the live sections of README.md using the public GitHub API."""
import json, os, re, urllib.request
from collections import Counter
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "VARUN1128")
TOKEN = os.environ.get("GITHUB_TOKEN")
FENCE = "`" * 3  # three backticks, built this way so copy-paste can't break the file


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "readme-updater"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def replace(text, tag, body):
    pattern = re.compile(rf"(<!--{tag}:START-->).*?(<!--{tag}:END-->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text)


user = api(f"/users/{USER}")
repos = api(f"/users/{USER}/repos?per_page=100&sort=pushed&type=owner")
own = [r for r in repos if not r["fork"] and r["name"].lower() != USER.lower()]
stars = sum(r["stargazers_count"] for r in own)
langs = Counter(r["language"] for r in own if r["language"]).most_common(3)
events = api(f"/users/{USER}/events/public?per_page=100")
recent_commits = sum(len(e["payload"].get("commits", [])) for e in events if e["type"] == "PushEvent")
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

top_langs = " · ".join(f"{n} ({c})" for n, c in langs) or "n/a"
stats_lines = [
    f" {USER}@github  ~  status",
    " ─────────────────────────────────────────────",
    f" public repos ........ {user['public_repos']}",
    f" followers ........... {user['followers']}",
    f" stars earned ........ {stars}",
    f" top languages ....... {top_langs}",
    f" recent commits ...... {recent_commits} (last ~90 days of public events)",
    f" last synced ......... {now}",
]
stats = FENCE + "text\n" + "\n".join(stats_lines) + "\n" + FENCE

rows = ["| Repository | Language | ⭐ | Last push |", "|:--|:--|:-:|:--|"]
for r in own[:6]:
    desc = (r["description"] or "").replace("|", "/")
    rows.append(
        f"| [**{r['name']}**]({r['html_url']})<br/><sub>{desc}</sub> "
        f"| {r['language'] or '-'} | {r['stargazers_count']} | {r['pushed_at'][:10]} |"
    )
repo_table = "\n".join(rows)

with open("README.md", encoding="utf-8") as f:
    content = f.read()
content = replace(content, "STATS", stats)
content = replace(content, "REPOS", repo_table)
with open("README.md", "w", encoding="utf-8") as f:
    f.write(content)
print("README updated", now)
