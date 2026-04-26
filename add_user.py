#!/usr/bin/env python3
"""
add_user.py
──────────
Add or update users in Secret Manager without redeploying.
Run from the project root after initial deployment.

Usage:  python3 add_user.py
"""
import json, hashlib, getpass, subprocess, sys

PROJECT_ID  = input("GCP Project ID: ").strip()
SECRET_NAME = input("Secret name [skill-agent-users]: ").strip() or "skill-agent-users"

# Load existing users
print("\nLoading existing users...")
try:
    result = subprocess.run(
        ["gcloud", "secrets", "versions", "access", "latest",
         f"--secret={SECRET_NAME}", f"--project={PROJECT_ID}"],
        capture_output=True, text=True, check=True
    )
    users = json.loads(result.stdout)
    print(f"  Found {len(users)} existing user(s): {', '.join(users.keys())}")
except Exception:
    print("  No existing users found — starting fresh.")
    users = {}

# Add new users
print("\nAdd users (blank username to finish):\n")
while True:
    u = input("  Username (blank to finish): ").strip()
    if not u:
        break
    p  = getpass.getpass(f"  Password for {u}: ")
    p2 = getpass.getpass(f"  Confirm: ")
    if p != p2:
        print("  ✗ Passwords don't match\n")
        continue
    users[u] = hashlib.sha256(p.encode()).hexdigest()
    print(f"  ✓ Added {u}\n")

if not users:
    print("No users. Exiting.")
    sys.exit(0)

# Write to temp file and upload new version
with open("/tmp/users.json", "w") as f:
    json.dump(users, f)

subprocess.run(
    ["gcloud", "secrets", "versions", "add", SECRET_NAME,
     f"--project={PROJECT_ID}", "--data-file=/tmp/users.json"],
    check=True
)

import os; os.remove("/tmp/users.json")
print(f"\n✅  Updated Secret Manager with {len(users)} user(s).")
print("  Changes take effect on next login — no redeploy needed.")
