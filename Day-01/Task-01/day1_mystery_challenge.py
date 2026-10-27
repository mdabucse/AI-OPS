#!/usr/bin/env python3
"""
Day 1 mystery challenge.

Usage:
    python3 day1_mystery_challenge.py [--minutes 8]

Running this injects a random hidden fault into your own local app -- no
setup needed, nothing to type beforehand. The challenge runs for a fixed
time and clears itself automatically. There is no command that tells you
the answer while you're investigating. At the end you'll be asked to type
your diagnosis; only after that is saved does the file also record the
real answer, together with an integrity hash, so it's verifiable that your
diagnosis wasn't edited after the fact.

Do not open this file's source before completing the exercise. The fault
is picked freshly at random each run, so reading the code will not tell
you this run's answer -- but it defeats the point of the exercise for you.
"""
import hashlib
import json
import random
import sys
import time
import urllib.error
import urllib.request

APP = "http://localhost:8000"
MODES = ["errors", "cpu"]


def _call(path: str) -> dict:
    req = urllib.request.Request(f"{APP}{path}", method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def _integrity_hash(payload: dict) -> str:
    material = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(material).hexdigest()


def _collect_diagnosis() -> dict:
    print("\n--- Submit your diagnosis ---")
    print("Answer based only on what you observed. Short answers are fine.\n")
    return {
        "signal_changed": input("Which signal(s) on your dashboard changed? "),
        "log_evidence": input("What did the logs show, if anything? "),
        "diagnosis": input("Your diagnosis, and the evidence behind it: "),
        "slo_impact": input("Does this burn your SLO/error budget? Roughly how much? "),
    }


def main():
    minutes = 8
    if "--minutes" in sys.argv:
        minutes = int(sys.argv[sys.argv.index("--minutes") + 1])

    mode = random.choice(MODES)
    try:
        _call(f"/chaos/{mode}/on")
    except (urllib.error.URLError, ConnectionError) as e:
        print(f"Could not reach the app at {APP}. Is the stack running? ({e})")
        sys.exit(1)

    print("Mystery fault injected on your local app.")
    print("Investigate using your 'AIOps Day 1' dashboard and your own queries.")
    print(f"You have {minutes} minutes. The fault clears itself automatically -- no command needed.\n")

    try:
        for remaining in range(minutes * 60, 0, -1):
            if remaining % 60 == 0 and remaining > 0:
                print(f"{remaining // 60} minute(s) remaining...")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        try:
            _call(f"/chaos/{mode}/off")
        except (urllib.error.URLError, ConnectionError):
            print("Warning: could not confirm the fault was cleared. Tell your trainer.")
        print("Fault cleared.")

    diagnosis = _collect_diagnosis()

    # The real answer is written only now, after your diagnosis is already
    # locked in above -- and only together with a hash over everything, so
    # your trainer can tell if this file was edited after the fact.
    timestamp = int(time.time())
    record = {**diagnosis, "timestamp": timestamp, "actual_fault": mode}
    record["integrity_hash"] = _integrity_hash(record)

    fname = f"diagnosis_{timestamp}.json"
    with open(fname, "w") as f:
        json.dump(record, f, indent=2)

    print(f"\nSaved to {fname}. This file includes today's real answer and a")
    print("verification hash, specifically so you can't edit your diagnosis")
    print("after seeing it. Submit the file as-is to your trainer.")


if __name__ == "__main__":
    main()
