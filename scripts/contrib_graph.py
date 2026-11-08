"""Writes a text contribution heatmap straight into README.md (no images needed).

Uses the GitHub GraphQL API. A personal token in GH_PAT (scope: read:user) adds
private-repo contributions; without it the built-in GITHUB_TOKEN is used.
"""
import json, math, os, re, sys, urllib.error, urllib.request

USER = os.environ.get("GH_USER", "VARUN1128")
TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
FENCE = "`" * 3
LEVELS = ["·", "░", "▒", "▓", "█"]

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


def fetch():
    if not TOKEN:
        print("ERROR: no token available (set GH_PAT or pass GITHUB_TOKEN).")
        sys.exit(1)
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "contrib-graph"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"ERROR: GitHub returned HTTP {e.code}: {e.read().decode()[:300]}")
        sys.exit(1)
    if "errors" in payload or not (payload.get("data") or {}).get("user"):
        print("ERROR: GraphQL problem:", json.dumps(payload)[:500])
        sys.exit(1)
    return payload["data"]["user"]["contributionsCollection"]


def heatmap(weeks, total, private):
    peak = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=1) or 1
    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    lines = [f" >_ {total:,} contributions in the last year (incl. {private:,} private)", ""]
    for row in range(7):
        cells = ""
        for w in weeks:
            ds = w["contributionDays"]
            if row < len(ds):
                c = ds[row]["contributionCount"]
                lvl = 0 if c == 0 else min(4, math.ceil(4 * c / peak))
                cells += LEVELS[lvl]
            else:
                cells += " "
        lines.append(f" {days[row]} {cells}")
    lines += ["", " less " + " ".join(LEVELS) + " more"]
    return FENCE + "text\n" + "\n".join(lines) + "\n" + FENCE


if __name__ == "__main__":
    data = fetch()
    cal = data["contributionCalendar"]
    block = heatmap(cal["weeks"], cal["totalContributions"], data["restrictedContributionsCount"])
    with open("README.md", encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(r"(<!--GRAPH:START-->).*?(<!--GRAPH:END-->)", re.S)
    if not pattern.search(content):
        print("ERROR: README.md has no <!--GRAPH:START--> / <!--GRAPH:END--> markers.")
        sys.exit(1)
    content = pattern.sub(lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}", content)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)
    print("Graph written to README.md")
