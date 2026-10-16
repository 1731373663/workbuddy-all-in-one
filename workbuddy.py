#!/usr/bin/env python3
"""WorkBuddy All-in-One: daily rewards + growth task center, one entry point.

Merged from:
  * daily.py                - signin / cat travel / makeup / streak redeem / blind box
                              (from 88lin/workbuddy-auto-signin)
  * scripts/task_runner.py  - growth task center auto-complete
                              (from bbb2bb/workbuddy-task-helper)

Usage:
  python workbuddy.py auto                  # guarded run (default)
  python workbuddy.py daily                 # daily only
  python workbuddy.py tasks                 # task center only
  python workbuddy.py status                # read-only checkin status
  python workbuddy.py doctor                # offline credential check
  python workbuddy.py auto --account <uid>  # single account
  python workbuddy.py auto --include-global # also run global realm accounts
  python workbuddy.py auto --force          # bypass all guards
  python workbuddy.py auto --dry-run        # show guard decision, do nothing

Guard rules for the write actions:
  1. at most 3 successful runs per local day
  2. at most 5 attempts per local day (3 successes + 2 retries)
  3. at least 3 hours between two successful runs
  4. after a failed run, wait at least 15 minutes before retrying
  5. a 3-second TCP probe must reach the API host first; if the network is
     down the run is skipped and does NOT consume an attempt

State lives in state.json next to this script.
"""
import glob
import json
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "scripts")
AUTHS = os.path.join(HERE, "auths")
DAILY = os.path.join(HERE, "daily.py")
RUNNER = os.path.join(SCRIPTS, "task_runner.py")
STATE = os.path.join(HERE, "state.json")

MAX_SUCCESS_PER_DAY = 3
MAX_ATTEMPT_PER_DAY = 5
SUCCESS_GAP_MINUTES = 180
RETRY_GAP_MINUTES = 15
PROBE_HOST = "copilot.tencent.com"
PROBE_PORT = 443
PROBE_TIMEOUT = 3


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


def _today():
    return time.strftime("%Y-%m-%d")


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            st = json.load(f)
    except Exception:
        st = {}
    if st.get("date") != _today():
        st = {"date": _today(), "success_count": 0, "attempt_count": 0,
              "last_success_ts": 0, "last_attempt_ts": 0, "last_ok": None}
    for k in ("success_count", "attempt_count"):
        st[k] = int(st.get(k) or 0)
    for k in ("last_success_ts", "last_attempt_ts"):
        st[k] = float(st.get(k) or 0)
    return st


def save_state(st):
    st["when"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def probe_network():
    try:
        with socket.create_connection((PROBE_HOST, PROBE_PORT), timeout=PROBE_TIMEOUT):
            return True
    except Exception:
        return False


def guard_reason(st, force=False):
    if force:
        return None
    if st["success_count"] >= MAX_SUCCESS_PER_DAY:
        return "daily success limit reached (%d/%d)" % (st["success_count"], MAX_SUCCESS_PER_DAY)
    if st["attempt_count"] >= MAX_ATTEMPT_PER_DAY:
        return "daily attempt limit reached (%d/%d)" % (st["attempt_count"], MAX_ATTEMPT_PER_DAY)
    now = time.time()
    if st["last_success_ts"]:
        gap = (now - st["last_success_ts"]) / 60.0
        if gap < SUCCESS_GAP_MINUTES:
            return ("last success %.0f min ago, need %d min between runs"
                    % (gap, SUCCESS_GAP_MINUTES))
    if st["last_ok"] is False and st["last_attempt_ts"]:
        gap = (now - st["last_attempt_ts"]) / 60.0
        if gap < RETRY_GAP_MINUTES:
            return ("last attempt failed %.0f min ago, retry in %d min"
                    % (gap, RETRY_GAP_MINUTES))
    return None


def _env(auth_file=None):
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if auth_file:
        env["WORKBUDDY_AUTH_FILE"] = auth_file
    else:
        env.pop("WORKBUDDY_AUTH_FILE", None)
    return env


def _ts():
    return time.strftime("[%Y-%m-%d %H:%M:%S]")


def _emit(line):
    """Print one line with a timestamp prefix so the log is easy to read."""
    print("%s %s" % (_ts(), line.rstrip("\r\n")), flush=True)


def _run_streaming(cmd, cwd, env):
    """Run a child process, prefixing every output line with a timestamp."""
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                         errors="replace", bufsize=1)
    for line in p.stdout:
        _emit(line)
    p.wait()
    return p.returncode


def run_daily(action="auto", auth_file=None):
    return _run_streaming([sys.executable, DAILY, action], HERE, _env(auth_file))


def run_tasks(uid):
    return _run_streaming([sys.executable, RUNNER, uid, "--yes"], SCRIPTS, _env())


def run_accounts(accts, action):
    rc = 0
    failed = False
    for uid, path in accts:
        _emit("== %s ==" % uid[:8])
        if action in ("daily", "auto", "all"):
            c = run_daily("auto", path)
            rc = c or rc
            if c != 0:
                failed = True
        if action in ("tasks", "auto", "all"):
            c = run_tasks(uid)
            rc = c or rc
            if c != 0:
                failed = True
    return rc, failed


def main():
    argv = sys.argv[1:] or ["auto"]
    only = None
    include_global = "--include-global" in argv
    force = "--force" in argv
    dry = "--dry-run" in argv
    for flag in ("--include-global", "--force", "--dry-run"):
        while flag in argv:
            argv.remove(flag)
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
            _emit("== %s ==" % uid[:8])
            rc = run_daily(action, path) or rc
        return rc

    st = load_state()
    reason = guard_reason(st, force=force)
    if reason:
        _emit("skip: %s" % reason)
        return 0

    if not force and not probe_network():
        _emit("skip: network probe failed (%s:%d); attempt not counted"
              % (PROBE_HOST, PROBE_PORT))
        return 0

    if dry:
        _emit("dry-run: guards passed, would run %s on %d account(s)"
              % (action, len(accts)))
        return 0

    st["attempt_count"] += 1
    st["last_attempt_ts"] = time.time()
    save_state(st)

    rc, failed = run_accounts(accts, action)

    st = load_state()
    st["last_ok"] = not failed
    if not failed:
        st["success_count"] += 1
        st["last_success_ts"] = time.time()
    save_state(st)
    return rc


if __name__ == "__main__":
    sys.exit(main())
