"""Tests for gitCorrect's pure logic — no git, no terminal."""
import os
import sys

# Make gitCorrect.py importable as a module.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gitCorrect as gc


# A fixed list of commands for tests, so tests don't depend on the
# git version installed on the machine.
FAKE_CMDS = [
    "add", "am", "annotate", "apply", "archive", "bisect", "blame",
    "branch", "bundle", "checkout", "cherry-pick", "clean", "clone",
    "commit", "config", "describe", "diff", "fetch", "gc", "grep",
    "init", "log", "merge", "mv", "pull", "push", "rebase", "reflog",
    "remote", "reset", "restore", "revert", "rm", "show", "stash",
    "status", "submodule", "switch", "tag", "worktree",
]


def top(typo, args=None):
    """Helper: return the top suggestion's command name, or None."""
    hits = gc.suggest(typo, args or [], FAKE_CMDS)
    return hits[0][0] if hits else None


# ---------------------------------------------------------------------------
# suggest()
# ---------------------------------------------------------------------------

def test_typo_transposition():
    assert top("confi") == "config"
    assert top("comit") == "commit"
    assert top("stauts") == "status"
    assert top("barnch") == "branch"


def test_typo_missing_letter():
    assert top("stat") == "status"
    assert top("int") == "init"


def test_typo_extra_letter():
    assert top("statuss") == "status"
    assert top("committ") == "commit"
    assert top("configg") == "config"


def test_context_pushes_score_up():
    without = gc.suggest("confi", [], FAKE_CMDS)
    with_ctx = gc.suggest("confi", ["--global", "user.name", "X"], FAKE_CMDS)
    assert with_ctx[0][1] >= without[0][1]


def test_weak_input_returns_low_scores():
    hits = gc.suggest("b", [], FAKE_CMDS)
    for _, score in hits:
        assert score < 0.55


def test_garbage_returns_nothing():
    assert gc.suggest("xyzabc", [], FAKE_CMDS) == []


def test_exact_match_is_not_a_typo():
    hits = gc.suggest("commit", [], FAKE_CMDS)
    if hits:
        assert hits[0][0] == "commit"


# ---------------------------------------------------------------------------
# fix_flags()
# ---------------------------------------------------------------------------

def test_long_flag_typo_is_fixed():
    fixed, corrections = gc.fix_flags("config", ["--globak", "user.name"])
    assert fixed == ["--global", "user.name"]
    assert corrections == [("--globak", "--global")]


def test_valid_long_flag_is_untouched():
    fixed, corrections = gc.fix_flags("config", ["--global", "user.name"])
    assert fixed == ["--global", "user.name"]
    assert corrections == []


def test_short_flags_are_untouched():
    fixed, corrections = gc.fix_flags("commit", ["-m", "msg"])
    assert fixed == ["-m", "msg"]
    assert corrections == []


def test_unknown_subcommand_does_nothing():
    fixed, corrections = gc.fix_flags("xyz", ["--anything"])
    assert fixed == ["--anything"]
    assert corrections == []


def test_non_flag_args_are_untouched():
    fixed, corrections = gc.fix_flags("commit", ["file.py", "-m", "msg"])
    assert fixed == ["file.py", "-m", "msg"]
    assert corrections == []


# ---------------------------------------------------------------------------
# is_dangerous()
# ---------------------------------------------------------------------------

def test_dangerous_subcommand():
    assert gc.is_dangerous("reset", ["--hard"])
    assert gc.is_dangerous("clean", ["-fd"])
    assert gc.is_dangerous("rebase", [])


def test_dangerous_flag_on_safe_subcommand():
    assert gc.is_dangerous("push", ["--force"])
    assert gc.is_dangerous("push", ["-f"])


def test_combined_short_flags_detected():
    assert gc.is_dangerous("clean", ["-fd"])
    assert gc.is_dangerous("clean", ["-df"])


def test_safe_commands_not_flagged():
    assert not gc.is_dangerous("config", ["--global", "user.name", "X"])
    assert not gc.is_dangerous("commit", ["-m", "msg"])
    assert not gc.is_dangerous("status", [])