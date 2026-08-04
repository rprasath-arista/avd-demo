# AVD Demo — DC1 Fabric

Arista Validated Design (AVD) demo for deploying and managing a DC1 leaf-spine fabric via CloudVision Portal (CVP).

## Quick Start

```bash
# Generate configs only
make build

# Push configlets to CVP (no execution)
make provision

# Full deploy: build + provision + execute tasks
make deploy

# Validate fabric state (via AVD/Ansible)
make validate

# Validate fabric state (standalone ANTA)
make anta-validate

# Reset fabric on CVP
make reset
```

## Design Type

**Data Center (DC) — EVPN/VXLAN Leaf-Spine Fabric**

| Attribute | Value |
|-----------|-------|
| Design Model | Layer 3 Leaf-Spine |
| Underlay Routing | eBGP |
| Overlay Routing | eBGP |
| Overlay Technology | VXLAN with VLAN-Aware Bundles |
| High Availability | MLAG on L3 Leaf pairs |
| Platform | vEOS-LAB |
| Management | CloudVision Portal (CVP) |
| Validation | ANTA (standalone + AVD integrated) |

## Topology

- **2 Spines:** DC1-SPINE1, DC1-SPINE2
- **4 L3 Leafs:** DC1-LEAF1A, DC1-LEAF1B, DC1-LEAF2A, DC1-LEAF2B
- **2 L2 Leafs:** DC1-L2LEAF1A, DC1-L2LEAF2A
- **CVP Server:** 10.18.146.238

![Topology Diagram](demo/topology-diagram.png)

## Project Structure

```
├── ansible.cfg              # Ansible configuration
├── inventory.yml            # Device inventory (spines, leafs, CVP)
├── group_vars/
│   ├── DC1.yml              # Global settings (users, TerminAttr, DNS)
│   ├── DC1_FABRIC.yml       # Fabric design (BGP, MLAG, interfaces)
│   ├── DC1_SERVERS.yml      # Server-facing port profiles
│   └── DC1_TENANTS_NETWORKS.yml  # VRFs, VLANs, SVIs
├── anta/
│   ├── inventory.yml        # ANTA device inventory (standalone)
│   └── catalog.yml          # ANTA test catalog
├── playbooks/
│   ├── dc1-fabric-deploy-cvp.yml   # Build + deploy configs via CVP
│   ├── dc1-fabric-reset-cvp.yml    # Reset fabric on CVP
│   └── dc1-validate-state.yml      # ANTA fabric validation
└── demo/scripts/
    ├── reset_cvp.py         # CVP reset helper
    └── validate_fabric.py   # Fabric validation helper
```

## ANTA — Standalone Validation

ANTA (Arista Network Test Automation) is also set up as a standalone tool for direct device testing outside of Ansible.

### Install

```bash
pip install anta
```

### Run Tests

```bash
# Full NRFU table report
make anta-validate

# JSON report (saved to anta/results.json)
make anta-validate-json

# Filter by device
anta nrfu -u ansible -p ansible --enable --insecure \
  -i anta/inventory.yml -c anta/catalog.yml \
  --device DC1-SPINE1 table

# Filter by tag (e.g. only L3 leafs, only MLAG devices)
anta nrfu -u ansible -p ansible --enable --insecure \
  -i anta/inventory.yml -c anta/catalog.yml \
  --tags l3leaf table

# Show only failures
anta nrfu -u ansible -p ansible --enable --insecure \
  -i anta/inventory.yml -c anta/catalog.yml \
  --hide success table
```

### Test Coverage

| Category | Tests | Scope |
|----------|-------|-------|
| System | Uptime, reload cause, coredump, CPU, memory, NTP | All devices |
| Hardware | Temperature, transceivers, cooling, power | All devices |
| Configuration | Zero-touch, running-config diffs | All devices |
| Interfaces | Errors, discards, err-disabled, storm control | All devices |
| STP | MSTP mode, blocked ports, counters | Leafs |
| MLAG | Status, interfaces, config sanity | MLAG pairs |
| BGP | Peer count, peer health (underlay + EVPN overlay) | Spines + L3 leafs |
| Routing | Multi-agent model, loopback reachability | Spines + L3 leafs |
| VXLAN | Vxlan1 interface, config sanity, VTEP peers | L3 leafs |
| BFD | Peer health | All devices |
| Security | SSH, telnet, HTTP API status | All devices |

## Requirements

- Python 3.x
- Ansible
- [arista.avd](https://avd.arista.com/) collection
- [arista.cvp](https://cvp.avd.sh/) collection
- [anta](https://anta.arista.com/) for standalone validation
- Access to CVP instance and EOS devices
