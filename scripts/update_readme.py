"""Refreshes the live sections of README.md using the public GitHub API."""
import json, os, re, urllib.request
from collections import Counter
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "VARUN1128")
TOKEN = os.environ.get("GITHUB_TOKEN")


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
stats = f"""```text
 {USER}@github  ~  status
 ─────────────────────────────────────────────
 public repos ........ {user['public_repos']}
 followers ........... {user['followers']}
 stars earned ........ {stars}
 top languages ....... {top_langs}
 recent commits ...... {recent_commits} (last ~90 days of public events)
 last synced ......... {now}
```"""

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
```

## 3. `scripts/contrib_graph.py`

```python
"""Builds assets/contributions.svg from the GitHub GraphQL API.

Needs a personal access token (secret GH_PAT, scope: read:user) so private-repo
contributions are included. Also turn on
Profile -> Contribution settings -> "Include private contributions on my profile".
"""
import json, math, os, sys, urllib.request

USER = os.environ.get("GH_USER", "VARUN1128")
PAT = os.environ.get("GH_PAT")
OUT = "assets/contributions.svg"

QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      restrictedContributionsCount
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ contributionCount date } }
      }
    }
  }
}"""

COLORS = ["#161b22", "#0b4f3a", "#00805a", "#00c27a", "#00ff9c"]
CELL, GAP, LEFT, TOP = 11, 3, 20, 46


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"Bearer {PAT}", "Content-Type": "application/json",
                 "User-Agent": "contrib-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]["user"]["contributionsCollection"]


def render(weeks, total, private):
    peak = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=1) or 1
    width = LEFT * 2 + len(weeks) * (CELL + GAP)
    height = TOP + 7 * (CELL + GAP) + 34
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="10" fill="#0d1117"/>',
        f'<text x="{LEFT}" y="26" fill="#00ff9c" font-family="monospace" font-size="14" font-weight="bold">'
        f'&gt;_ {total:,} contributions in the last year (incl. {private:,} private)</text>',
    ]
    for x, w in enumerate(weeks):
        for y, d in enumerate(w["contributionDays"]):
            c = d["contributionCount"]
            lvl = 0 if c == 0 else min(4, math.ceil(4 * c / peak))
            out.append(
                f'<rect x="{LEFT + x * (CELL + GAP)}" y="{TOP + y * (CELL + GAP)}" width="{CELL}" height="{CELL}" '
                f'rx="2" fill="{COLORS[lvl]}"><title>{d["date"]}: {c}</title></rect>'
            )
    ly = height - 14
    out.append(f'<text x="{LEFT}" y="{ly + 9}" fill="#8b949e" font-family="monospace" font-size="10">less</text>')
    for i, col in enumerate(COLORS):
        out.append(f'<rect x="{LEFT + 30 + i * 14}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" fill="{col}"/>')
    out.append(f'<text x="{LEFT + 104}" y="{ly + 9}" fill="#8b949e" font-family="monospace" font-size="10">more</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if not PAT:
        print("GH_PAT not set; keeping existing graph.")
        sys.exit(0)
    data = fetch()
    cal = data["contributionCalendar"]
    svg = render(cal["weeks"], cal["totalContributions"], data["restrictedContributionsCount"])
    os.makedirs("assets", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("Wrote", OUT)
```

## 4. `assets/contributions.svg`
This is a placeholder. The workflow overwrites it with your real graph.

```xml
<svg xmlns="http://www.w3.org/2000/svg"
