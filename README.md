# gitCorrect

Autocorrect for git. Because `git confi` should just work.

```
$ git confi --global user.name "Jane"
git: 'confi' is not a git command. Did you mean 'config'? (score 0.99)
Run 'git config --global user.name Jane'? [y/N] y
```

## What it does

- Fixes typos in git subcommands: `confi` → `config`, `comit` → `commit`, `stauts` → `status`
- Fixes typos in long flags: `--globak` → `--global`
- Uses argument context to improve guesses: `confi --global` scores higher than `confi` alone
- Refuses to auto-run dangerous commands (`reset --hard`, `push --force`) — requires typing the full word `yes` to confirm
- Passes through valid commands silently, so it never gets in your way

## Install

```
pip install gitcorrect
```

## Use

`gitcorrect` is a drop-in wrapper around git. You give it the same arguments you'd give to git:

```
gitcorrect confi --global user.name "Jane"
gitcorrect stauts
gitcorrect comit -m "fix bug"
```

To make it intercept `git` itself, add a shell hook.

### PowerShell

Add this to your `$PROFILE`:

```powershell
function git {
    gitcorrect @args
}
```

### Bash / Zsh

Add this to `~/.bashrc` or `~/.zshrc`:

```bash
git() {
    command gitcorrect "$@"
}
```

Now `git confi` goes through `gitcorrect`, and every other `git` command still works normally.

## What it won't do

- Fix typos in short flags (`-m`, `-a`). One letter is a huge semantic difference and too risky.
- Fix typos in non-flag arguments (config keys, branch names). Coming in a future version.
- Replace git. It delegates to the real `git` for everything.

## License

MIT