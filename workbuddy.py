#!/usr/bin/env python3
"""WorkBuddy All-in-One: daily rewards + growth task center, one entry point.

Merged from:
  * daily.py                - signin / cat travel / makeup / streak redeem / blind box
                              (from 88lin/workbuddy-auto-signin)
  * scripts/task_runner.py  - growth task center auto-complete
                              (from bbb2bb/workbuddy-task-helper)

Usage:
  python workbuddy.py auto                  # all CN accounts: daily + tasks
  python workbuddy.py daily                 # daily only
  python workbuddy.py tasks                 # task center only
  python workbuddy.py status                # read-only checkin status
  python workbuddy.py doctor                # offline credential check
  python workbuddy.py auto --account <uid>  # single account
  python workbuddy.py auto --include-global # also run global realm accounts
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "scripts")
AUTHS = os.path.join(HERE, "auths")
DAILY = os.path.join(HERE, "daily.py")
RUNNER = os.path.join(SCRIPTS, "task_runner.py")


def _is_global(d):
    auth = d.get("auth") or {}
    if (auth.get("realm") or d.get("realm") or "").strip().lower() == "global":
        return True
    return (auth.get("domain") or "").strip().lower().endswith(".workbuddy.ai")


def _accounts(include_global=False):
    out = []
    for p in sorted(glob.glob(os.path.join(AUTHS, "workbuddy-*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            uid = ((d.get("account") or {}).get("uid") or "")
            if not uid:
                continue
            if _is_global(d) and not include_global:
                continue
            out.append((uid, p))
        except Exception:
            continue
    return out


def _env(auth_file=None):
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if auth_file:
        env["WORKBUDDY_AUTH_FILE"] = auth_file
    else:
        env.pop("WORKBUDDY_AUTH_FILE", None)
    return env


def run_daily(action="auto", auth_file=None):
    cmd = [sys.executable, DAILY, action]
    return subprocess.call(cmd, cwd=HERE, env=_env(auth_file))


def run_tasks(uid):
    cmd = [sys.executable, RUNNER, uid, "--yes"]
    return subprocess.call(cmd, cwd=SCRIPTS, env=_env())


def main():
    argv = sys.argv[1:] or ["auto"]
    only = None
    include_global = "--include-global" in argv
    if include_global:
        argv.remove("--include-global")
    if "--account" in argv:
        i = argv.index("--account")
        if i + 1 >= len(argv):
            print("--account requires a uid prefix", file=sys.stderr)
            return 2
        only = argv[i + 1]
        del argv[i:i + 2]

    action, rest = argv[0], argv[1:]
    accts = _accounts(include_global or bool(only))
    if only:
        accts = [a for a in accts if a[0].startswith(only)]
    if not accts:
        print("no matching accounts in auths/", file=sys.stderr)
        return 2

    if action in ("status", "doctor", "claim", "growth"):
        rc = 0
        for uid, path in accts:
            print("== %s ==" % uid[:8], flush=True)
            rc = run_daily(action, path) or rc
        return rc

    if action == "daily":
        rc = 0
        for uid, path in accts:
            print("== %s ==" % uid[:8], flush=True)
            rc = run_daily("auto", path) or rc
        return rc

    if action == "tasks":
        rc = 0
        for uid, path in accts:
            rc = run_tasks(uid) or rc
        return rc

    if action in ("auto", "all"):
        rc = 0
        for uid, path in accts:
            print("== %s ==" % uid[:8], flush=True)
            rc = run_daily("auto", path) or rc
            rc = run_tasks(uid) or rc
        return rc

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
