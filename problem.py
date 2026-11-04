#!/usr/bin/env python3
"""£robl€m$ -- post and maintain the fortnightly problems.

The problem body is written in LaTeX (default) or pandoc-Markdown with $..$ math, and lives in
    _problems/NNN-slug.tex   (or .md)        <- you edit this
pandoc turns it into the Jekyll post
    _posts/YYYY-MM-DD-problem-NNN-slug.html  <- generated body; front matter is kept
The front matter of the generated post (title, deadline, status, ...) is authoritative: `build`
only replaces the body below it.

Usage
  ./problem.py new "Title" [--md] [--days 14] [--date YYYY-MM-DD]  create, open $EDITOR, build
  ./problem.py edit N                     open source of problem N in $EDITOR, rebuild
  ./problem.py build [N ...]              rebuild (all problems if no N)
  ./problem.py award N "Name" [--url URL] mark N as awarded (solver shown on the page)
  ./problem.py close N                    mark N as closed without award
  ./problem.py list                       table of all problems
  ./problem.py preview                    local jekyll server -> http://localhost:4000

Publishing is unchanged: ./deploy.sh "message".

LaTeX support (via pandoc's LaTeX reader, rendered by MathJax 3 on the page):
  inline $..$ / \\(..\\), display \\[..\\], equation/align (numbered iff they carry a \\label),
  \\eqref/\\ref, \\newcommand macros, \\section (-> h3), \\emph/\\textbf, itemize/enumerate,
  \\begin{abstract}..\\end{abstract} (context header, typeset like a LaTeX abstract; its first
  paragraph is the list teaser), \\href/\\url, \\includegraphics{/images/...}, ``quotes''.  No custom packages, no TikZ
  (include a pre-rendered SVG instead).
"""
import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "_problems"
POSTS = ROOT / "_posts"
LUA = SRC / "web-math.lua"
PERIOD_DAYS = 14
BOUNTY = "$20"
ICON = "/images/klingon.svg"

TEX_TEMPLATE = r"""% £robl€m {num:03d}: {title}
% Body only -- no \documentclass, no preamble packages. Title, dates, status live in the
% front matter of {post}.
% Macros defined here are expanded by pandoc:
\newcommand{{\vect}}[1]{{\boldsymbol{{#1}}}}

\begin{{abstract}}
Context of the problem: where it comes from, why it matters. Typeset like a LaTeX abstract
above the problem statement; its first paragraph is the teaser in the £robl€m$ list.
\end{{abstract}}

\section*{{Setting}}
Inline $E = \hbar\omega$, display with a number:
\begin{{equation}}
  \vect{{F}} = -\nabla V(\vect{{r}}) \label{{eq:force}}
\end{{equation}}
and a reference to Eq.~\eqref{{eq:force}}.

\section*{{Deliverable}}
\begin{{itemize}}
  \item \dots
\end{{itemize}}
"""

MD_TEMPLATE = r"""---
abstract: |
  Context of the problem: where it comes from, why it matters. Typeset like a LaTeX
  abstract above the problem statement; its first paragraph is the teaser.
---

<!-- £robl€m {num:03d}: {title}
     Body only. pandoc Markdown: $..$ inline, $$..$$ display, raw LaTeX commands allowed.
     Title, dates, status live in the front matter of {post}. -->

### Setting

Inline $E = \hbar\omega$, display:

$$ \boldsymbol{{F}} = -\nabla V(\boldsymbol{{r}}) $$

### Deliverable

- ...
"""


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:50].rstrip("-") or "problem"


def sources():
    """{num: Path} of problem sources."""
    out = {}
    for p in SRC.glob("[0-9][0-9][0-9]-*"):
        if p.suffix in (".tex", ".md"):
            out[int(p.name[:3])] = p
    return out


def post_for(num):
    hits = sorted(POSTS.glob(f"*-problem-{num:03d}-*.html"))
    return hits[0] if hits else None


def split_post(path):
    text = path.read_text()
    m = re.match(r"^---\n(.*?\n)---\n", text, re.S)
    if not m:
        sys.exit(f"{path}: no front matter")
    return m.group(1), text[m.end():]


def set_field(fm, key, value):
    line = f"{key}: {value}\n"
    if re.search(rf"^{key}:.*$", fm, re.M):
        return re.sub(rf"^{key}:.*\n", lambda _: line, fm, count=1, flags=re.M)
    return fm + line


def get_field(fm, key):
    m = re.search(rf"^{key}:[ \t]*(.*)$", fm, re.M)
    return m.group(1).strip().strip('"') if m else ""


def yq(s):
    """YAML double-quoted scalar."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def pandoc(src):
    if not shutil.which("pandoc"):
        sys.exit("pandoc not found")
    fmt = "latex" if src.suffix == ".tex" else "markdown+tex_math_dollars+raw_tex+latex_macros"
    cmd = ["pandoc", "-f", fmt, "-t", "html5", "--mathjax", "--wrap=preserve",
           "--shift-heading-level-by=2", "--lua-filter", str(LUA), str(src)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"pandoc failed on {src.name}:\n{r.stderr}")
    if r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)
    return r.stdout


def build(num):
    src = sources().get(num)
    post = post_for(num)
    if not src or not post:
        sys.exit(f"problem {num}: source or post missing")
    fm, _ = split_post(post)
    body = pandoc(src)
    post.write_text(f"---\n{fm}---\n<!-- GENERATED from _problems/{src.name} by problem.py; "
                    f"edit the source, not this body. -->\n{body}")
    print(f"built  {post.relative_to(ROOT)}")


def editor(path):
    ed = os.environ.get("PROBLEM_EDITOR") or "vi"
    subprocess.call(ed.split() + [str(path)])


def cmd_new(a):
    SRC.mkdir(exist_ok=True)
    date = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    deadline = date + dt.timedelta(days=a.days)
    num = max(sources(), default=0) + 1
    slug = slugify(a.title)
    src = SRC / f"{num:03d}-{slug}.{'md' if a.md else 'tex'}"
    post = POSTS / f"{date.isoformat()}-problem-{num:03d}-{slug}.html"
    fm = (f"layout: problem\n"
          f"title: {yq(a.title)}\n"
          f"date: {date.isoformat()}\n"
          f"categories: [problem]\n"
          f"number: {num}\n"
          f"deadline: {deadline.isoformat()}\n"
          f"bounty: {yq(BOUNTY)}\n"
          f"status: open\n"
          f"solver:\n"
          f"solution_url:\n"
          f"image: {yq(ICON)}\n"
          f"commentbox: true\n"
          f"render_with_liquid: false\n")
    post.write_text(f"---\n{fm}---\n")
    tpl = MD_TEMPLATE if a.md else TEX_TEMPLATE
    src.write_text(tpl.format(num=num, title=a.title, post=post.relative_to(ROOT)))
    print(f"source {src.relative_to(ROOT)}\npost   {post.relative_to(ROOT)}\n"
          f"№ {num}, posted {date}, deadline {deadline}")
    if not a.no_edit:
        editor(src)
    build(num)


def cmd_edit(a):
    src = sources().get(a.num) or sys.exit(f"no problem {a.num}")
    editor(src)
    build(a.num)


def cmd_build(a):
    for n in (a.nums or sorted(sources())):
        build(n)


def set_status(num, **fields):
    post = post_for(num) or sys.exit(f"no post for problem {num}")
    fm, body = split_post(post)
    for k, v in fields.items():
        fm = set_field(fm, k, v)
    post.write_text(f"---\n{fm}---\n{body}")
    print(f"{post.relative_to(ROOT)}: " + ", ".join(f"{k}={v}" for k, v in fields.items()))


def cmd_award(a):
    set_status(a.num, status="awarded", solver=yq(a.name), solution_url=yq(a.url) if a.url else "")


def cmd_close(a):
    set_status(a.num, status="closed")


def cmd_list(_):
    for n, src in sorted(sources().items()):
        post = post_for(n)
        fm = split_post(post)[0] if post else ""
        print(f"{n:3d}  {get_field(fm, 'date'):10s}  -> {get_field(fm, 'deadline'):10s}  "
              f"{get_field(fm, 'status'):8s}  {get_field(fm, 'title')}"
              + (f"   [{get_field(fm, 'solver')}]" if get_field(fm, 'solver') else ""))


def cmd_preview(_):
    # Build into a throw-away directory so neither ../site nor the tracked _site is touched.
    dest = Path(os.environ.get("TMPDIR", "/tmp")) / "kirschjs-preview"
    os.execvp("bundle", ["bundle", "exec", "jekyll", "serve", "--destination", str(dest),
                         "--livereload", "--future"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("new"); p.add_argument("title")
    p.add_argument("--md", action="store_true", help="Markdown body instead of LaTeX")
    p.add_argument("--days", type=int, default=PERIOD_DAYS)
    p.add_argument("--date", help="posting date YYYY-MM-DD (default today)")
    p.add_argument("--no-edit", action="store_true"); p.set_defaults(f=cmd_new)
    p = sp.add_parser("edit"); p.add_argument("num", type=int); p.set_defaults(f=cmd_edit)
    p = sp.add_parser("build"); p.add_argument("nums", type=int, nargs="*"); p.set_defaults(f=cmd_build)
    p = sp.add_parser("award"); p.add_argument("num", type=int); p.add_argument("name")
    p.add_argument("--url"); p.set_defaults(f=cmd_award)
    p = sp.add_parser("close"); p.add_argument("num", type=int); p.set_defaults(f=cmd_close)
    sp.add_parser("list").set_defaults(f=cmd_list)
    sp.add_parser("preview").set_defaults(f=cmd_preview)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
