#!/usr/bin/env python3
"""gitCorrect — figure out what you meant when you typo a git subcommand."""
import os
import re
import subprocess
import sys
import difflib


def list_commands():
    out = subprocess.check_output(
        ["git", "help", "-a"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    cmds = set()
    for line in out.splitlines():
        m = re.match(r"^\s{2,}([a-z0-9][a-z0-9-]*)\s{2,}\S", line)
        if m:
            cmds.add(m.group(1))
    return sorted(cmds)


def context_bonus(cmd, args):
    if cmd == "config" and any(
        a in ("--global", "--system", "--local") or ("." in a and "=" in a)
        for a in args
    ):
        return 0.35
    if cmd == "commit" and any(a in ("-m", "--message") for a in args):
        return 0.25
    if cmd in ("checkout", "switch") and any(a in ("-b", "-B", "-c", "-C") for a in args):
        return 0.15
    return 0.0


def suggest(typo, args, cmds):
    scored = []
    for c in cmds:
        base = difflib.SequenceMatcher(None, typo, c).ratio()
        if len(typo) >= 3 and c.startswith(typo) and c != typo:
            base += 0.05
        if base < 0.55:
            continue
        scored.append((c, min(base + context_bonus(c, args), 0.99)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:3]


def run_git(args):
    sys.exit(subprocess.call(["git", *args]))


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        run_git(args)

    sub, rest = args[0], args[1:]
    cmds = list_commands()

    if sub in cmds:
        run_git(args)

    hits = suggest(sub, rest, cmds)
    if not hits:
        run_git(args)

    cmd, score = hits[0]
    print(f"git: '{sub}' is not a git command. Did you mean '{cmd}'? "
          f"(score {score:.2f})", file=sys.stderr)

    try:
        ans = input(f"Run 'git {cmd} {' '.join(rest)}'? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = ""

    if ans in ("y", "yes"):
        run_git([cmd, *rest])
    run_git(args)


if __name__ == "__main__":
    main()