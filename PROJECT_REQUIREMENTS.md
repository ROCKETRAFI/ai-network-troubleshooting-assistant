# AI-Powered Network Automation Assistant - Project Requirements

## 1. Project Title

**AI-Powered Network Automation Assistant for Cisco IOS Configuration Generation and Validation**

## 2. Base Paper Reference

Base paper:

**GeNet: A Multimodal LLM-Based Co-Pilot for Network Topology and Configuration**  
arXiv: 2407.08249v2  
URL: https://arxiv.org/abs/2407.08249v2

This project is inspired by the GeNet paper, but the implementation can be simplified and focused on real NOC-style change management.

## 3. Problem Statement

Network engineers often perform configuration changes manually. This process is time-consuming and error-prone, especially when changes involve routing protocols, IP addressing, interface configuration, and rollback planning.

The goal of this project is to build an AI-assisted network automation system that accepts network change requests in plain English and generates validated Cisco IOS configuration changes. The system should not deploy changes directly without human approval.

## 4. Main Objective

To develop an AI-powered assistant that converts natural language network change requests into structured network intents, verifies them using a source of truth, generates delta-only Cisco IOS configurations, validates the risk, and exports deployment-ready Ansible playbooks with rollback support.

## 5. Example User Requirement

Input:

```text
Connect R1 and R2 with OSPF on 10.1.1.0/30.
```

Expected output:

- Structured intent
- Device and subnet verification result
- Cisco IOS configuration delta
- Configuration diff
- Rollback commands
- Risk score
- Ansible playbook
- Human approval status

## 6. Scope of the Project

### In Scope

- Natural language to structured intent conversion
- Cisco IOS configuration generation
- OSPF support
- BGP support
- Modify mode for existing configurations
- Config diff engine
- Rule-based validation
- LLM-based risk scoring
- Blast radius estimation
- Rollback script generation
- Ansible playbook export
- Human approval gate
- Basic Gradio UI
- Automated tests

### Out of Scope for Initial Version

- Fully automatic production deployment
- Multi-vendor support such as Juniper, Arista, Fortinet
- Real-time network telemetry integration
- Complex firewall policy automation
- SD-WAN controller integration
- Full NetBox production deployment

These can be added as future enhancements.

## 7. Recommended Tech Stack

### Programming Language

- Python 3.11+

### AI / LLM

- GPT-4o or equivalent LLM
- Prompt-based structured intent extraction
- LLM risk scoring

### UI

- Gradio for quick demo interface

### Network Source of Truth

- NetBox
- For demo: mock NetBox data can be stored in JSON if real NetBox setup is difficult

### Config Parsing and Validation

- ciscoconfparse
- Python `ipaddress` module
- Custom rule-based validators

### Automation Export

- Ansible playbook YAML generation

### Testing

- pytest
- Unit tests for intent parsing, validation, config generation, rollback, and diff engine

## 8. System Architecture

```text
User Input
   |
   v
Natural Language Intent Parser
   |
   v
Structured Intent JSON
   |
   v
NetBox / Mock Source-of-Truth Verification
   |
   v
Rule-Based Validation
   |
   v
Cisco IOS Delta Config Generator
   |
   v
Config Diff + Rollback Generator
   |
   v
LLM Risk Scoring + Blast Radius Estimation
   |
   v
Human Approval Gate
   |
   v
Ansible Playbook Export
```

## 9. Core Modules Needed

### 9.1 Intent Parser

Purpose:

Convert plain English into structured JSON.

Example output:

```json
{
  "change_type": "routing",
  "protocol": "ospf",
  "devices": ["R1", "R2"],
  "network": "10.1.1.0/30",
  "area": "0",
  "mode": "add"
}
```

Required features:

- Identify devices
- Identify protocol
- Identify network/subnet
- Identify operation: add, modify, remove
- Ask for clarification when required data is missing

### 9.2 NetBox Verification Module

Purpose:

Check whether requested devices, interfaces, and subnets exist.

Checks:

- Device exists
- Interface exists
- IP subnet is valid
- Subnet is available or already assigned
- Requested change does not conflict with existing data

For demo, this can use `data/netbox_mock.json`.

### 9.3 Rule-Based Validation Module

Purpose:

Catch deterministic network errors before config generation.

Validation rules:

- Invalid subnet format
- Duplicate IP address
- Overlapping subnet
- Unknown device
- Missing interface
- BGP ASN missing
- OSPF area missing
- Interface shutdown conflict
- Routing protocol conflict
- Dangerous commands such as full config replacement

### 9.4 Config Generator

Purpose:

Generate Cisco IOS delta-only configuration.

Example:

```text
router ospf 1
 network 10.1.1.0 0.0.0.3 area 0
```

Rules:

- Generate only required config changes
- Do not rewrite full device config
- Keep output readable
- Separate config by device

### 9.5 Config Diff Engine

Purpose:

Show what will change before approval.

Output:

```diff
+ router ospf 1
+  network 10.1.1.0 0.0.0.3 area 0
```

### 9.6 Rollback Generator

Purpose:

Generate commands to undo the generated change.

Example:

```text
router ospf 1
 no network 10.1.1.0 0.0.0.3 area 0
```

### 9.7 Risk Scoring Module

Purpose:

Estimate risk before human approval.

Risk levels:

- Low
- Medium
- High
- Critical

Risk factors:

- Number of devices affected
- Routing protocol affected
- Core device involved
- Existing config modified
- New subnet introduced
- BGP changes
- Possible traffic interruption

### 9.8 Blast Radius Estimation

Purpose:

Explain impact of the change.

Example:

```text
Blast radius: Medium
Affected devices: R1, R2
Affected protocol: OSPF
Possible impact: Routing adjacency change between R1 and R2.
```

### 9.9 Human Approval Gate

Purpose:

Prevent direct deployment.

Flow:

- Show parsed intent
- Show validation result
- Show generated config
- Show rollback
- Show risk score
- Engineer approves or rejects

### 9.10 Ansible Export Module

Purpose:

Export generated config as an Ansible playbook.

Example:

```yaml
---
- name: Apply network change
  hosts: routers
  gather_facts: false
  tasks:
    - name: Configure OSPF
      cisco.ios.ios_config:
        lines:
          - network 10.1.1.0 0.0.0.3 area 0
        parents:
          - router ospf 1
```

## 10. Dataset Needed

Minimum demo dataset:

### Devices

- R1
- R2
- R3
- SW1

### Interfaces

- R1: GigabitEthernet0/0, GigabitEthernet0/1
- R2: GigabitEthernet0/0, GigabitEthernet0/1
- R3: GigabitEthernet0/0, GigabitEthernet0/1

### Subnets

- 10.1.1.0/30
- 10.1.2.0/30
- 192.168.10.0/24
- 192.168.20.0/24

### Sample Existing Configs

Store under:

```text
configs/
  R1.cfg
  R2.cfg
  R3.cfg
```

## 11. Suggested Folder Structure

```text
network-ai-assistant/
  app.py
  requirements.txt
  README.md
  data/
    netbox_mock.json
  configs/
    R1.cfg
    R2.cfg
    R3.cfg
  src/
    intent_parser.py
    netbox_client.py
    validators.py
    config_generator.py
    diff_engine.py
    rollback.py
    risk_scorer.py
    ansible_exporter.py
  tests/
    test_intent_parser.py
    test_validators.py
    test_config_generator.py
    test_rollback.py
    test_ansible_exporter.py
```

## 12. Minimum Features for Final Submission

The project can be considered complete if it supports:

- Plain English input
- Structured intent JSON output
- Mock NetBox verification
- OSPF config generation
- BGP config generation
- Config diff
- Rollback commands
- Risk score
- Human approval button
- Ansible playbook export
- At least 20 automated tests
- README with setup and demo screenshots

## 13. Extra Features for Higher Marks

- Upload topology image and extract device/link details
- Real NetBox API integration
- Cisco Packet Tracer / GNS3 demo
- ACL generation
- VLAN generation
- NAT generation
- Change history database
- Login system
- PDF report generation
- Multi-vendor config generation

## 14. Validation Rules Senior Engineers May Expect

- Device existence check
- Interface existence check
- Interface status check
- IP format validation
- Subnet overlap detection
- Duplicate IP detection
- OSPF area validation
- OSPF process ID validation
- BGP ASN validation
- BGP neighbor IP validation
- Route redistribution warning
- Default route modification warning
- Core device modification warning
- Existing config conflict detection
- Rollback availability check
- Dangerous command detection
- Empty config rejection
- Human approval requirement

## 15. Milestone Plan

### Phase 1: Project Setup

- Create Python project structure
- Add requirements
- Add mock NetBox JSON
- Add sample Cisco configs

### Phase 2: Intent Parsing

- Build prompt for LLM intent extraction
- Convert output into JSON
- Add fallback regex parser for demo safety

### Phase 3: Validation

- Implement subnet validation
- Implement device validation
- Implement OSPF and BGP checks

### Phase 4: Config Generation

- Generate OSPF delta config
- Generate BGP delta config
- Generate rollback config

### Phase 5: UI

- Build Gradio interface
- Show intent, validation, config, diff, risk, rollback, and approval

### Phase 6: Export and Testing

- Export Ansible playbook
- Add pytest test cases
- Prepare README and demo screenshots

## 16. Final Deliverables

- Source code
- README.md
- PROJECT_REQUIREMENTS.md
- requirements.txt
- Sample configs
- Mock NetBox data
- Test cases
- Demo screenshots
- Final report
- Presentation PPT

## 17. Best Final-Year Project Angle

Best focus:

**AI-assisted network change management**

Reason:

In real NOC environments, engineers need safe and auditable changes more than fully automatic configuration deployment. So the project should emphasize validation, diff, rollback, risk scoring, and human approval.

## 18. Short Abstract

This project proposes an AI-powered network automation assistant that converts natural language network change requests into validated Cisco IOS configuration changes. The system extracts structured intent using an LLM, verifies devices and subnets using NetBox or mock source-of-truth data, performs rule-based and AI-assisted validation, generates delta-only configurations, prepares rollback commands, estimates blast radius, and exports Ansible playbooks. A human approval gate ensures that no generated configuration is deployed without engineer review.

