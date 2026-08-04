#!/usr/bin/env python3
"""Reset CVP: unassign and delete all AVD configlets from devices."""

from cvprac.cvp_client import CvpClient
import urllib3

urllib3.disable_warnings()

CVP_HOST = "10.18.146.238"
CVP_USER = "ansible"
CVP_PASS = "ansible"
PREFIX = "DC1-AVD_"

print(f"\n{'='*60}")
print(f"  CVP Reset — Removing AVD configlets")
print(f"  CVP: {CVP_HOST}")
print(f"{'='*60}\n")

client = CvpClient()
client.connect([CVP_HOST], CVP_USER, CVP_PASS)
print("Connected to CVP\n")

inventory = client.api.get_inventory()
fabric = [d for d in inventory if d["hostname"].startswith("DC1-")]
print(f"Found {len(fabric)} fabric device(s)\n")

print("--- Removing configlet assignments ---")
for d in fabric:
    hostname = d["hostname"]
    dev_cls = client.api.get_configlets_by_device_id(d["systemMacAddress"])
    avd_cls = [c for c in dev_cls if c["name"].startswith(PREFIX)]
    if avd_cls:
        names = [c["name"] for c in avd_cls]
        client.api.remove_configlets_from_device("AVD reset", d, avd_cls)
        print(f"  {hostname}: removed {names}")
    else:
        print(f"  {hostname}: clean")

print("\n--- Deleting configlets ---")
all_cls = client.api.get_configlets()["data"]
avd_cls = [c for c in all_cls if c["name"].startswith(PREFIX)]
if avd_cls:
    for c in avd_cls:
        client.api.delete_configlet(c["name"], c["key"])
        print(f"  Deleted: {c['name']}")
else:
    print("  No AVD configlets to delete")

print(f"\n{'='*60}")
print(f"  Reset complete. CVP is clean for a fresh demo.")
print(f"{'='*60}\n")
