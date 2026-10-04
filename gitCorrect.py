#!/usr/bin/env python3
"""gitCorrect — figure out what you meant when you typo a git subcommand or flag."""
import os
import re
import subprocess
import sys
import difflib


KNOWN_FLAGS = {
    "config": ["--global", "--system", "--local", "--worktree", "--get",
               "--get-all", "--get-regexp", "--unset", "--unset-all",
               "--add", "--replace-all", "--list", "--edit",
               "--name-only", "--show-origin", "--show-scope"],
    "commit": ["--message", "--amend", "--all", "--patch", "--no-verify",
               "--author", "--date", "--allow-empty", "--verbose"],
    "log":    ["--oneline", "--graph", "--all", "--decorate", "--stat",
               "--patch", "--pretty", "--author", "--since", "--until"],
    "push":   ["--force", "--force-with-lease", "--set-upstream", "--tags",
               "--all", "--delete", "--dry-run"],
    "pull":   ["--rebase", "--no-rebase", "--ff-only", "--no-ff", "--all"],
    "checkout": ["--branch", "--force", "--track", "--orphan", "--detach"],
    "switch": ["--create", "--force-create", "--detach", "--track", "--orphan"],
    "branch": ["--all", "--remotes", "--delete", "--move", "--copy",
               "--list", "--verbose", "--set-upstream-to"],
}


DANGEROUS_SUBCOMMANDS = {
    "reset", "clean", "rebase", "filter-branch", "filter-repo",
    "reflog", "gc", "prune", "rm",
}

DANGEROUS_FLAGS = {
    "--hard", "--force", "-f", "--mirror", "--delete", "-D",
    "--expire", "--prune", "--no-verify",
}


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
        if c.startswith(typo) and c != typo:
            base += 0.15
        if base < 0.35:
            continue
        scored.append((c, min(base + context_bonus(c, args), 0.99)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:3]


def fix_flags(sub, flags):
    """Correct long-flag typos for known subcommands."""
    long_known = KNOWN_FLAGS.get(sub, [])
    if not long_known:
        return flags, []

    fixed = []
    corrections = []
    for f in flags:
        if not f.startswith("--") or f in long_known:
            fixed.append(f)
            continue
        matches = difflib.get_close_matches(f, long_known, n=1, cutoff=0.7)
        if matches:
            corrections.append((f, matches[0]))
            fixed.append(matches[0])
        else:
            fixed.append(f)
    return fixed, corrections


def is_dangerous(sub, args):
    if sub in DANGEROUS_SUBCOMMANDS:
        return True
    for a in args:
        if a in DANGEROUS_FLAGS:
            return True
        if a.startswith("-") and not a.startswith("--") and len(a) > 1:
            for ch in a[1:]:
                if f"-{ch}" in DANGEROUS_FLAGS:
                    return True
    return False


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

    # No candidates at all → hand off to git.
    if not hits:
        run_git(args)

    best_cmd, best_score = hits[0]

    # Strong suggestion → normal path.
    if best_score >= 0.55:
        cmd, score = best_cmd, best_score
    else:
        # Weak candidates only → show them, then defer to git.
        print(f"git: '{sub}' is not a git command. No confident match. Maybe:",
              file=sys.stderr)
        for c, s in hits:
            print(f"     {c:<15} ({s:.2f})", file=sys.stderr)
        run_git(args)
        return

    # Fix long flags before prompting.
    fixed_rest, flag_fixes = fix_flags(cmd, rest)
    danger = is_dangerous(cmd, fixed_rest)

    print(f"git: '{sub}' is not a git command. Did you mean '{cmd}'? "
          f"(score {score:.2f})", file=sys.stderr)
    for old, new in flag_fixes:
        print(f"     (also fixing {old} → {new})", file=sys.stderr)
    if danger:
        print("     ⚠  WARNING: this command can destroy work. "
              "Type 'yes' to confirm.", file=sys.stderr)

    preview = " ".join([cmd, *fixed_rest])

    try:
        if danger:
            ans = input(f"Run 'git {preview}'? Type 'yes' to confirm: ").strip().lower()
            confirmed = ans == "yes"
        else:
            ans = input(f"Run 'git {preview}'? [y/N] ").strip().lower()
            confirmed = ans in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        confirmed = False

    if confirmed:
        run_git([cmd, *fixed_rest])
    run_git(args)


if __name__ == "__main__":
    main()