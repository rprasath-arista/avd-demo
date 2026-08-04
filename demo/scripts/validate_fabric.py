#!/usr/bin/env python3
"""Pre-deployment fabric validation via CVP API."""

import json
import ssl
import urllib.request
import urllib.error
import sys
from datetime import datetime

CVP_HOST = "10.18.146.238"
CVP_USER = "ansible"
CVP_PASS = "ansible"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def cvp_request(path, data=None, method="GET", token=None):
    url = f"https://{CVP_HOST}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Cookie"] = f"access_token={token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=60)
    return json.loads(resp.read())

def login():
    result = cvp_request("/cvpservice/login/authenticate.do",
                         {"userId": CVP_USER, "password": CVP_PASS}, "POST")
    return result["cookie"]["Value"]

def get_devices(token):
    return cvp_request("/cvpservice/inventory/devices", method="GET", token=token)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
SKIP = "\033[90mSKIP\033[0m"
HEADER = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

results = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}

def log_test(status, category, device, detail):
    if status == PASS:
        results["pass"] += 1
    elif status == FAIL:
        results["fail"] += 1
    elif status == WARN:
        results["warn"] += 1
    else:
        results["skip"] += 1
    print(f"  [{status}] {category:30s} | {device:15s} | {detail}")

print(f"\n{BOLD}{'='*80}")
print(f"  Fabric Validation via CVP  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  CVP: {CVP_HOST}")
print(f"{'='*80}{RESET}\n")

token = login()
print(f"  CVP login: OK\n")

devices = get_devices(token)
fabric_devices = [d for d in devices if d["hostname"].startswith("DC1-")]

expected_devices = ["DC1-SPINE1", "DC1-SPINE2", "DC1-LEAF1A", "DC1-LEAF1B",
                    "DC1-LEAF2A", "DC1-LEAF2B", "DC1-L2LEAF1A", "DC1-L2LEAF2A"]

# ─── Device Inventory & Streaming ───
print(f"{HEADER}{'─'*80}")
print(f"  TEST GROUP: Device Inventory & Streaming Status")
print(f"{'─'*80}{RESET}")

found_names = [d["hostname"] for d in fabric_devices]
for dev in expected_devices:
    if dev in found_names:
        d = next(x for x in fabric_devices if x["hostname"] == dev)
        streaming = d.get("streamingStatus", "unknown")
        if streaming == "active":
            log_test(PASS, "Device registered & streaming", dev, f"IP={d['ipAddress']}")
        else:
            log_test(FAIL, "Device streaming", dev, f"streamingStatus={streaming}")
    else:
        log_test(FAIL, "Device registered", dev, "NOT FOUND in CVP inventory")

# ─── System Health ───
print(f"\n{HEADER}{'─'*80}")
print(f"  TEST GROUP: System Health (EOS version, model)")
print(f"{'─'*80}{RESET}")

for d in fabric_devices:
    hostname = d["hostname"]
    version = d.get("version", "unknown")
    model = d.get("modelName", "unknown")
    sn = d.get("serialNumber", "N/A")
    if version and version != "unknown":
        log_test(PASS, "EOS version", hostname, f"version={version} model={model} SN={sn}")
    else:
        log_test(WARN, "EOS version", hostname, "Could not determine version")

# ─── Container Topology ───
print(f"\n{HEADER}{'─'*80}")
print(f"  TEST GROUP: CVP Container Topology")
print(f"{'─'*80}{RESET}")

try:
    containers = cvp_request("/cvpservice/provisioning/getContainers.do?startIndex=0&endIndex=0",
                             method="GET", token=token)
    container_list = containers.get("data", [])
    container_names = [c["name"] for c in container_list]
    for cname in ["DC1_FABRIC", "DC1_SPINES", "DC1_L3LEAFS", "DC1_L2LEAFS"]:
        if cname in container_names:
            log_test(PASS, "Container exists", cname, "Present in CVP")
        else:
            log_test(FAIL, "Container exists", cname, "MISSING from CVP")
except Exception as e:
    log_test(WARN, "Container topology", "CVP", f"Could not query: {e}")

# ─── AVD Configlets ───
print(f"\n{HEADER}{'─'*80}")
print(f"  TEST GROUP: AVD Configlets on CVP")
print(f"{'─'*80}{RESET}")

try:
    configlets = cvp_request("/cvpservice/configlet/getConfiglets.do?startIndex=0&endIndex=0&type=All",
                             method="GET", token=token)
    configlet_names = [c["name"] for c in configlets.get("data", [])]
    for dev in expected_devices:
        cname = f"DC1-AVD_{dev}"
        if cname in configlet_names:
            log_test(PASS, "Configlet exists", dev, f"'{cname}' found on CVP")
        else:
            log_test(FAIL, "Configlet exists", dev, f"'{cname}' MISSING from CVP")
except Exception as e:
    log_test(WARN, "Configlet check", "CVP", f"Could not query: {e}")

# ─── Configlet Assignments ───
print(f"\n{HEADER}{'─'*80}")
print(f"  TEST GROUP: Configlet Assignments")
print(f"{'─'*80}{RESET}")

for d in fabric_devices:
    hostname = d["hostname"]
    try:
        dev_configlets = cvp_request(
            f"/cvpservice/provisioning/getConfigletsByDeviceId.do?netElementId={d['systemMacAddress']}",
            method="GET", token=token)
        assigned = [c["name"] for c in dev_configlets.get("configletList", [])]
        avd_configlet = f"DC1-AVD_{hostname}"
        if avd_configlet in assigned:
            log_test(PASS, "AVD configlet assigned", hostname, f"'{avd_configlet}' attached ({len(assigned)} total)")
        else:
            log_test(FAIL, "AVD configlet assigned", hostname, f"'{avd_configlet}' NOT assigned. Has: {assigned}")
    except Exception as e:
        log_test(WARN, "Configlet assignment", hostname, f"Could not query: {e}")

# ─── Configuration Compliance ───
print(f"\n{HEADER}{'─'*80}")
print(f"  TEST GROUP: Configuration Compliance")
print(f"{'─'*80}{RESET}")

for d in fabric_devices:
    hostname = d["hostname"]
    compliance = d.get("complianceCode", "unknown")
    if compliance == "0000":
        log_test(PASS, "Config compliance", hostname, "In compliance")
    elif compliance == "0001":
        log_test(WARN, "Config compliance", hostname, "Config out of sync (pending task)")
    else:
        log_test(WARN, "Config compliance", hostname, f"complianceCode={compliance}")

# ─── Pending Tasks ───
print(f"\n{HEADER}{'─'*80}")
print(f"  TEST GROUP: Pending Tasks")
print(f"{'─'*80}{RESET}")

try:
    tasks = cvp_request("/cvpservice/task/getTasks.do?startIndex=0&endIndex=0&queryparam=Pending",
                        method="GET", token=token)
    task_list = tasks.get("data", [])
    if not task_list:
        log_test(PASS, "Pending tasks", "CVP", "No pending tasks")
    else:
        log_test(WARN, "Pending tasks", "CVP", f"{len(task_list)} pending task(s)")
        for t in task_list[:10]:
            desc = t.get("description", "N/A")
            dev = t.get("workOrderDetails", {}).get("netElementHostName", "unknown")
            log_test(WARN, "  Pending task", dev, desc[:60])
except Exception as e:
    log_test(WARN, "Pending tasks", "CVP", f"Could not query: {e}")

# ─── Device Container Placement ───
print(f"\n{HEADER}{'─'*80}")
print(f"  TEST GROUP: Device Container Placement")
print(f"{'─'*80}{RESET}")

expected_placement = {
    "DC1-SPINE1": "DC1_SPINES", "DC1-SPINE2": "DC1_SPINES",
    "DC1-LEAF1A": "DC1_L3LEAFS", "DC1-LEAF1B": "DC1_L3LEAFS",
    "DC1-LEAF2A": "DC1_L3LEAFS", "DC1-LEAF2B": "DC1_L3LEAFS",
    "DC1-L2LEAF1A": "DC1_L2LEAFS", "DC1-L2LEAF2A": "DC1_L2LEAFS",
}

for d in fabric_devices:
    hostname = d["hostname"]
    container = d.get("containerName", "unknown")
    expected = expected_placement.get(hostname, "unknown")
    if container == expected:
        log_test(PASS, "Container placement", hostname, f"In '{container}' (correct)")
    else:
        log_test(WARN, "Container placement", hostname, f"In '{container}', expected '{expected}'")

# ─── Summary ───
print(f"\n{BOLD}{'='*80}")
total = results["pass"] + results["fail"] + results["warn"] + results["skip"]
print(f"  VALIDATION SUMMARY")
print(f"{'='*80}{RESET}")
print(f"  Total tests:  {total}")
print(f"  {PASS} Passed:  {results['pass']}")
print(f"  {FAIL} Failed:  {results['fail']}")
print(f"  {WARN} Warning: {results['warn']}")
print(f"  {SKIP} Skipped: {results['skip']}")
print()

if results["fail"] > 0:
    print(f"  {BOLD}\033[91mFABRIC NOT READY — fix failures before deploying{RESET}")
    sys.exit(1)
elif results["warn"] > 0:
    print(f"  {BOLD}\033[93mFABRIC HAS WARNINGS — review before deploying{RESET}")
    sys.exit(0)
else:
    print(f"  {BOLD}\033[92mFABRIC READY — safe to deploy{RESET}")
    sys.exit(0)
