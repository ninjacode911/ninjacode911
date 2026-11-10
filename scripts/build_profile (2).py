#!/usr/bin/env python3
"""Builds the animated SVG cards for the profile README.

Standard library only. With GITHUB_TOKEN set (as it is inside GitHub Actions)
it pulls fresh numbers from the GraphQL API; without one it re-renders from the
last snapshot in scripts/profile-data.json.

    python scripts/build_profile.py
"""
import datetime as dt
import json
import os
import re
import urllib.request
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SNAPSHOT = ROOT / "scripts" / "profile-data.json"
README = ROOT / "README.md"

# --------------------------------------------------------------------------
# Everything you would want to edit by hand lives in CONFIG.
# --------------------------------------------------------------------------
CONFIG = {
    "login": "ninjacode911",
    "wordmark": "NAVNIT",
    "prompt": "navnit@pune:~$",
    "tagline": ["AI and MLOps engineer.", "Video editor after hours."],
    "facts": [  # {placeholders} are filled from live data
        ("role", "AI & MLOps engineer"),
        ("also", "Video editor"),
        ("base", "Pune, Maharashtra"),
        ("building", "Deep learning, GenAI, MLOps pipelines"),
        ("writes", "Python, R, Java"),
        ("cuts in", "After Effects, DaVinci Resolve"),
        ("shipped", "{repos} public projects"),
        ("this year", "{total} contributions"),
        ("site", "navnitai.vercel.app"),
    ],
    "stack": [
        ("Languages", ["Python", "Java", "R", "Julia", "Shell"]),
        ("AI & GenAI", ["Hugging Face", "LangChain", "OpenAI", "AWS Bedrock"]),
        ("Deep learning", ["TensorFlow", "Keras", "PyTorch", "ONNX"]),
        ("Classic ML", ["scikit-learn", "XGBoost", "LightGBM", "CatBoost"]),
        ("Computer vision", ["OpenCV", "YOLO", "Detectron2", "MediaPipe"]),
        ("NLP", ["NLTK", "spaCy", "Transformers"]),
        ("RL", ["OpenAI Gym", "Ray RLlib", "Stable Baselines"]),
        ("MLOps & cloud", ["Docker", "Kubernetes", "SageMaker", "Vertex AI", "Kubeflow"]),
        ("Big data & DB", ["Spark", "Kafka", "Hadoop", "MongoDB", "Redis"]),
        ("Tools", ["Git", "Conda", "Streamlit"]),
        ("Creative", ["After Effects", "DaVinci Resolve"]),
    ],
    "links": [  # (file slug, label, url)
        ("portfolio", "Portfolio", "https://navnitai.vercel.app/"),
        ("linkedin", "LinkedIn", "https://www.linkedin.com/in/navnitai/"),
        ("email", "Email", "mailto:navnitamrutharaj1234@gmail.com"),
        ("huggingface", "Hugging Face", "https://huggingface.co/NinjainPJs"),
        ("kaggle", "Kaggle", "https://www.kaggle.com/ninjacode911"),
        ("leetcode", "LeetCode", "https://leetcode.com/u/Ninja_in_PJs/"),
        ("stackoverflow", "Stack Overflow", "https://stackoverflow.com/users/32001856/navnit-a"),
        ("codesandbox", "CodeSandbox", "https://codesandbox.io/u/Ninjacode911"),
        ("codepen", "CodePen", "https://codepen.io/Navnit-A"),
        ("instagram", "Instagram", "https://www.instagram.com/navnit.a_"),
        ("youtube", "YouTube", "https://www.youtube.com/"),
    ],
}

# --------------------------------------------------------------------------
# Look
# --------------------------------------------------------------------------
BG, EDGE, RAISED = "#0F1521", "#232C3D", "#172033"
TEXT, DIM, FAINT = "#DCE3EE", "#8792A6", "#4A566B"
TEAL, AMBER = "#56C7C2", "#F5A742"
HEAT = ["#18202F", "#1F4B55", "#2B7C80", "#3FB0AB", "#8DE8DC"]
LANG_COLOURS = [TEAL, AMBER, "#6C9EF8", "#E8D27A", "#A58BF0", "#E48BB5", "#EE7D5B"]
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
W = 860
STILL = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"

FONT = {  # 5x7 block letters for the wordmark
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01111 10000 10000 10000 10000 10000 01111", "D": "11110 10001 10001 10001 10001 10001 11110",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01111 10000 10000 10011 10001 10001 01111", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "11111 00100 00100 00100 00100 00100 11111", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 11001 10101 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 11011 10001", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
}


def svg(w, h, body, style="", label=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(label)}" font-family="{MONO}">'
        f"<style>{style}{STILL}</style>"
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="{EDGE}"/>'
        f"{body}</svg>"
    )


def text(x, y, s, size=13, fill=TEXT, weight=400, anchor="start", cls=""):
    c = f' class="{cls}"' if cls else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
        f'text-anchor="{anchor}"{c} xml:space="preserve">{escape(s)}</text>'
    )


def wrap(s, width, max_lines):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    if len(lines) > max_lines:
        last = lines[max_lines - 1]
        lines = lines[: max_lines - 1] + [last[: width - 1].rstrip(" ,.;:") + "…"]
    return lines


def nice_name(repo):
    return re.sub(r"^Project-+", "", repo).replace("-", " ").strip()


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
QUERY = """
query($login:String!,$after:String){
  user(login:$login){
    name location
    followers{totalCount} following{totalCount}
    pinnedItems(first:6,types:REPOSITORY){nodes{... on Repository{
      name description url stargazerCount primaryLanguage{name}}}}
    repositories(first:100,after:$after,ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC){
      pageInfo{hasNextPage endCursor}
      nodes{name stargazerCount forkCount primaryLanguage{name}}}
    contributionsCollection{contributionCalendar{
      weeks{contributionDays{date contributionCount}}}}
  }
}"""


def gql(token, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-builder"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out["data"]["user"]


def fetch(token):
    login, repos, after = CONFIG["login"], [], None
    while True:
        u = gql(token, {"login": login, "after": after})
        page = u["repositories"]
        for n in page["nodes"]:
            repos.append({
                "name": n["name"], "stars": n["stargazerCount"], "forks": n["forkCount"],
                "lang": (n["primaryLanguage"] or {}).get("name"),
            })
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    weeks = u["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {
        "fetched": dt.date.today().isoformat(),
        "user": {
            "login": login, "name": u["name"], "location": u["location"],
            "followers": u["followers"]["totalCount"], "following": u["following"]["totalCount"],
        },
        "repos": repos,
        "pinned": [
            {"name": n["name"], "desc": n["description"] or "", "url": n["url"],
             "stars": n["stargazerCount"], "lang": (n["primaryLanguage"] or {}).get("name")}
            for n in u["pinnedItems"]["nodes"] if n
        ],
        "days": [[d["date"], d["contributionCount"]] for w in weeks for d in w["contributionDays"]],
    }


def summarise(data):
    days = [(dt.date.fromisoformat(d), c) for d, c in data["days"]]
    longest = run = 0
    for _, c in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    for i, (_, c) in enumerate(reversed(days)):
        if c:
            current += 1
        elif i:  # an empty today does not break the streak yet
            break
    best = max(days, key=lambda x: x[1])
    return {
        "days": days,
        "total": sum(c for _, c in days),
        "active": sum(1 for _, c in days if c),
        "longest": longest,
        "current": current,
        "best": best,
        "repos": len(data["repos"]),
        "stars": sum(r["stars"] for r in data["repos"]),
        "followers": data["user"]["followers"],
        "langs": Counter(r["lang"] for r in data["repos"] if r["lang"]).most_common(),
    }


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------
def header_card(s):
    h = 286
    word = CONFIG["wordmark"].upper()
    cols = len(word) * 6 - 1
    pitch = min(10, 350 / cols)
    x0, y0 = 32, 78
    blocks = []
    for li, ch in enumerate(word):
        rows = FONT.get(ch, FONT["X"]).split()
        for r, row in enumerate(rows):
            for c, bit in enumerate(row):
                if bit == "1":
                    col = li * 6 + c
                    fill = [HEAT[4], HEAT[4], "#6FD6CE", HEAT[3], HEAT[3], "#35969A", HEAT[2]][r]
                    blocks.append(
                        f'<rect class="b" x="{x0 + col * pitch:.1f}" y="{y0 + r * pitch:.1f}" '
                        f'width="{pitch - 1:.1f}" height="{pitch - 1:.1f}" rx="1.5" fill="{fill}" '
                        f'style="animation-delay:{col * 28 + r * 22}ms"/>'
                    )
    body = [text(32, 44, f'{CONFIG["prompt"]} whoami', 13, DIM)]
    body += blocks
    ty = y0 + 7 * pitch + 34
    for i, line in enumerate(CONFIG["tagline"]):
        body.append(text(32, ty + i * 22, line, 14, TEXT if i == 0 else DIM, cls="l"
                         ).replace('class="l"', f'class="l" style="animation-delay:{1.1 + i * .15:.2f}s"'))
    fx, fy = 432, 82
    fmt = {"repos": s["repos"], "total": f'{s["total"]:,}'}
    for i, (k, v) in enumerate(CONFIG["facts"]):
        y = fy + i * 21
        delay = f'style="animation-delay:{1.2 + i * .09:.2f}s"'
        body.append(f'<g class="l" {delay}>{text(fx, y, k, 13, TEAL)}{text(fx + 96, y, v.format(**fmt), 13, TEXT)}</g>')
    py = h - 26
    pw = len(CONFIG["prompt"]) * 7.83
    body.append(text(32, py, CONFIG["prompt"], 13, DIM))
    body.append(f'<rect class="cur" x="{32 + pw + 8:.0f}" y="{py - 12}" width="8" height="15" fill="{AMBER}"/>')
    style = (
        ".b{animation:pop .35s ease-out both}.l{animation:rise .5s ease-out both}"
        ".cur{animation:blink 1.1s steps(1) infinite}"
        "@keyframes pop{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}"
        "@keyframes rise{from{opacity:0}to{opacity:1}}"
        "@keyframes blink{50%{opacity:0}}"
    )
    return svg(W, h, "".join(body), style, f'{CONFIG["wordmark"].title()}: {" ".join(CONFIG["tagline"])}')


def timeline_card(s):
    days = s["days"]
    counts = sorted(c for _, c in days if c)
    q = [counts[int(len(counts) * p)] for p in (.25, .5, .75)] if counts else [1, 2, 3]

    def level(c):
        return 0 if c == 0 else 1 + sum(c > t for t in q)

    first = days[0][0]
    lead = (first.weekday() + 1) % 7  # GitHub weeks start on Sunday
    ncols = (lead + len(days) + 6) // 7
    weeks = [[] for _ in range(ncols)]
    for i, (d, c) in enumerate(days):
        weeks[(lead + i) // 7].append(((lead + i) % 7, d, c))
    week_tot = [sum(c for _, _, c in w) for w in weeks]
    peak = max(week_tot) or 1

    h, x0, pitch, top, mid = 322, 84, 14, 78, 214
    span = ncols * pitch
    sweep, cycle = 6.0, 22.0
    body = [
        text(24, 40, "The last 12 months, as a timeline", 14, TEXT, 600),
        text(W - 34, 40, f'{days[0][0]:%b %Y} to {days[-1][0]:%b %Y}', 12, DIM, anchor="end"),
        text(24, top + 54, "days", 12, DIM), text(24, mid + 4, "weeks", 12, DIM),
        f'<rect x="{x0 - 6}" y="{top - 6}" width="{span + 10}" height="{7 * pitch + 10}" rx="6" fill="{RAISED}" opacity=".45"/>',
        f'<rect x="{x0 - 6}" y="{mid - 28}" width="{span + 10}" height="56" rx="6" fill="{RAISED}" opacity=".45"/>',
    ]
    last_month = None
    for i, w in enumerate(weeks):
        x = x0 + i * pitch
        m = w[0][1].month
        if m != last_month and i < ncols - 2:
            if last_month is not None or w[0][1].day <= 7:
                body.append(text(x, top - 14, f"{w[0][1]:%b}", 11, DIM))
            last_month = m
        cells = "".join(
            f'<rect x="{x}" y="{top + r * pitch}" width="{pitch - 2}" height="{pitch - 2}" rx="2.5" fill="{HEAT[level(c)]}"/>'
            for r, _, c in w
        )
        half = max(1.5, 24 * week_tot[i] / peak)
        bar = f'<rect x="{x + 2}" y="{mid - half:.1f}" width="{pitch - 6}" height="{half * 2:.1f}" rx="2" fill="{TEAL}" opacity=".85"/>'
        body.append(f'<g class="c" style="animation-delay:{i / ncols * sweep:.2f}s">{cells}{bar}</g>')
    body.append(
        f'<g class="ph"><path d="M{x0 - 6} {top - 12}h10l-5 7z" fill="{AMBER}"/>'
        f'<rect x="{x0 - 1.75}" y="{top - 8}" width="1.5" height="{mid + 30 - top + 8}" fill="{AMBER}"/></g>'
    )
    best_d, best_c = s["best"]
    reads = [
        (f'{s["total"]:,}', "contributions"),
        (str(s["active"]), "active days"),
        (f'{s["longest"]} days', "longest streak"),
        (str(best_c), f"most in one day, {best_d:%b} {best_d.day}"),
    ]
    if s["current"] >= 3:
        reads[1] = (f'{s["current"]} days', "current streak")
    for i, (v, lab) in enumerate(reads):
        x = x0 - 6 + i * 190
        body.append(text(x, 278, v, 17, TEXT, 600) + text(x, 298, lab, 12, DIM))
    p = sweep / cycle * 100
    style = (
        f".c{{animation:lit {cycle}s linear infinite both}}"
        f".ph{{transform:translateX({span}px);animation:sweep {cycle}s linear infinite}}"
        "@keyframes lit{0%{opacity:.14}2.2%{opacity:1}100%{opacity:1}}"
        f"@keyframes sweep{{0%{{transform:translateX(0);opacity:0}}1%{{opacity:1}}"
        f"{p:.1f}%{{transform:translateX({span}px)}}97%{{transform:translateX({span}px);opacity:1}}"
        f"100%{{transform:translateX({span}px);opacity:0}}}}"
    )
    label = f'{s["total"]:,} contributions in the last year, {s["active"]} active days, longest streak {s["longest"]} days'
    return svg(W, h, "".join(body), style, label)


def languages_card(s):
    h = 136
    langs = s["langs"]
    top = langs[:6]
    rest = sum(n for _, n in langs[6:])
    if rest:
        top.append(("Other", rest))
    total = sum(n for _, n in top) or 1
    body = [
        text(24, 40, "What the public repos are written in", 14, TEXT, 600),
        text(W - 24, 40, f'{s["repos"]} repos, {s["stars"]} stars, {s["followers"]} followers', 12, DIM, anchor="end"),
        f'<clipPath id="r"><rect x="24" y="58" width="{W - 48}" height="14" rx="7"/></clipPath>',
    ]
    x, segs, lx = 24.0, [], 24
    for i, (name, n) in enumerate(top):
        colour = LANG_COLOURS[i] if i < len(LANG_COLOURS) and name != "Other" else FAINT
        w = (W - 48) * n / total
        segs.append(f'<rect x="{x:.1f}" y="58" width="{max(w - 2, 1):.1f}" height="14" fill="{colour}"/>')
        x += w
        lab = f"{name} {n}"
        body.append(f'<circle cx="{lx + 5}" cy="102" r="5" fill="{colour}"/>' + text(lx + 16, 106, lab, 12, DIM))
        lx += 16 + len(lab) * 7.25 + 22
    body.append(f'<g clip-path="url(#r)">{"".join(segs)}</g>')
    return svg(W, h, "".join(body), "", "Languages: " + ", ".join(f"{n} {c}" for n, c in top))


def stack_card():
    rows = CONFIG["stack"]
    h = 64 + len(rows) * 24 + 10
    body = [text(24, 40, "Toolbox", 14, TEXT, 600)]
    for i, (k, items) in enumerate(rows):
        y = 74 + i * 24
        if i:
            body.append(f'<rect x="24" y="{y - 17}" width="{W - 48}" height="1" fill="{EDGE}" opacity=".7"/>')
        body.append(text(24, y, k, 13, TEAL))
        x = 190
        for it in items:
            body.append(text(x, y, it, 13, TEXT))
            x += len(it) * 7.83 + 26
    return svg(W, h, "".join(body), "", "Toolbox: " + "; ".join(f'{k}: {", ".join(v)}' for k, v in rows))


def project_card(p, colour):
    w, h = 424, 138
    body = [
        f'<rect x="1" y="16" width="3" height="{h - 32}" rx="1.5" fill="{colour}"/>',
        text(22, 36, nice_name(p["name"]), 14, TEXT, 600),
    ]
    for i, line in enumerate(wrap(p["desc"] or "No description yet.", 52, 3)):
        body.append(text(22, 60 + i * 18, line, 12, DIM))
    foot = p["lang"] or "Mixed"
    body.append(f'<circle cx="27" cy="{h - 22}" r="4.5" fill="{colour}"/>' + text(38, h - 18, foot, 12, DIM))
    if p["stars"]:
        body.append(text(w - 20, h - 18, f'{p["stars"]} star{"s" if p["stars"] != 1 else ""}', 12, DIM, anchor="end"))
    return svg(w, h, "".join(body), "", f'{nice_name(p["name"])}: {p["desc"]}')


def link_chip(label):
    w = round(len(label) * 7.25 + 28)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="30" viewBox="0 0 {w} 30" role="img" '
        f'aria-label="{escape(label)}" font-family="{MONO}">'
        f'<rect x=".5" y=".5" width="{w - 1}" height="29" rx="14.5" fill="{BG}" stroke="{EDGE}"/>'
        f'{text(w / 2, 19.5, label, 12, TEXT, anchor="middle")}</svg>'
    )


# --------------------------------------------------------------------------
def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        data = fetch(token)
        SNAPSHOT.write_text(json.dumps(data, separators=(",", ":")))
    else:
        print("No GITHUB_TOKEN set, rendering from the saved snapshot.")
        data = json.loads(SNAPSHOT.read_text())
    s = summarise(data)

    ASSETS.mkdir(exist_ok=True)
    out = {
        "header": header_card(s), "timeline": timeline_card(s),
        "languages": languages_card(s), "stack": stack_card(),
    }
    lang_colour = {name: LANG_COLOURS[i] for i, (name, _) in enumerate(s["langs"][: len(LANG_COLOURS)])}
    for old in ASSETS.glob("project-*.svg"):
        old.unlink()
    rows = []
    for i, p in enumerate(data["pinned"], 1):
        out[f"project-{i}"] = project_card(p, lang_colour.get(p["lang"], DIM))
        alt = escape(nice_name(p["name"]), {'"': "&quot;"})
        rows.append(f'<a href="{p["url"]}"><img src="assets/project-{i}.svg" width="49.5%" alt="{alt}" /></a>')
    for slug, label, _ in CONFIG["links"]:
        out[f"link-{slug}"] = link_chip(label)
    for name, content in out.items():
        (ASSETS / f"{name}.svg").write_text(content, encoding="utf-8")

    if README.exists():
        md = README.read_text(encoding="utf-8")
        block = "<!-- projects:start -->\n" + "\n".join(rows) + "\n<!-- projects:end -->"
        new = re.sub(r"<!-- projects:start -->.*?<!-- projects:end -->", lambda _: block, md, flags=re.S)
        if new != md:
            README.write_text(new, encoding="utf-8")
    print(f'Built {len(out)} cards: {s["total"]:,} contributions, {s["repos"]} repos, {s["stars"]} stars.')


if __name__ == "__main__":
    main()
