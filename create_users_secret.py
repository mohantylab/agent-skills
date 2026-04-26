#!/usr/bin/env python3
"""
create_users_secret.py
Create hashed user credentials and upload to GCP Secret Manager.
Run once before deploying. Never commit the output file.

Usage:
    python create_users_secret.py
"""
import json, hashlib, getpass, subprocess, sys

PROJECT_ID  = input("GCP Project ID: ").strip()
SECRET_NAME = input("Secret name [skill-agent-users]: ").strip() or "skill-agent-users"

users = {}
print("\nAdd users (blank username to finish):\n")
while True:
    u = input("  Username: ").strip()
    if not u: break
    p  = getpass.getpass(f"  Password for {u}: ")
    p2 = getpass.getpass(f"  Confirm: ")
    if p != p2: print("  ✗ Passwords don't match\n"); continue
    users[u] = hashlib.sha256(p.encode()).hexdigest()
    print(f"  ✓ Added {u}\n")

if not users: print("No users added."); sys.exit(0)

with open("users.json", "w") as f:
    json.dump(users, f, indent=2)
print(f"\nSaved {len(users)} user(s) to users.json")

create = input("\nUpload to Secret Manager now? [y/N]: ").strip().lower()
if create == 'y':
    subprocess.run(["gcloud","secrets","create",SECRET_NAME,
                    f"--project={PROJECT_ID}","--data-file=users.json"], check=True)
    print(f"✅ Secret '{SECRET_NAME}' created in project '{PROJECT_ID}'")
else:
    print(f"\nRun manually:\n  gcloud secrets create {SECRET_NAME} --project={PROJECT_ID} --data-file=users.json")

print("\n⚠️  Delete users.json now:\n  rm users.json")
