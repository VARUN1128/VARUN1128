"""Builds assets/contributions.svg from the GitHub GraphQL API.

Needs a personal access token (secret GH_PAT, scope: read:user) so private-repo
contributions are included. Also turn on
Profile -> Contribution settings -> "Include private contributions on my profile".
"""
import json, math, os, sys, urllib.error, urllib.request

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
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"ERROR: GitHub returned HTTP {e.code}: {e.read().decode()[:300]}")
        if e.code == 401:
            print("-> The GH_PAT token is invalid or expired. Create a new token and update the secret.")
        sys.exit(1)
    if "errors" in payload or not payload.get("data", {}).get("user"):
        print("ERROR: GraphQL problem:", json.dumps(payload)[:500])
        sys.exit(1)
    return payload["data"]["user"]["contributionsCollection"]


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
