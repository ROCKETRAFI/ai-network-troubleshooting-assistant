# AI-Powered Network Automation Assistant

Final-year project MVP inspired by **GeNet** ([arXiv:2407.08249](https://arxiv.org/abs/2407.08249)).

Plain-English change requests become a **review pack**: structured intent, mock NetBox checks, Cisco IOS **delta** (not a full rewrite), rollback, diff, risk/blast radius, and Ansible YAML. **Nothing is pushed to a live router.** An engineer must approve before Ansible export is released.

This is an **AI-assisted change-management copilot**, not an auto-deploy controller.

## What it does

| Step | What happens |
| --- | --- |
| 1. Intent | LLM (Gemini/OpenAI) or regex fallback → JSON |
| 2. Source of truth | Mock NetBox JSON: devices, roles, interfaces, prefixes |
| 3. Validation | Rule-based checks + `ciscoconfparse` on sample running-configs |
| 4. Self-check | Generated IOS is compared to the parsed intent |
| 5. Generate | OSPF/BGP delta + rollback + unified diff |
| 6. Risk | Heuristic score and blast radius (not an LLM judge) |
| 7. Approval | Ansible playbook is **held** until the approval box is ticked |
| 8. Export | `cisco.ios.ios_config` playbook YAML |

## Demo UI

Custom HTML/CSS/JS console (**Network Assistance**) served by FastAPI on [http://127.0.0.1:7860](http://127.0.0.1:7860).

- **Chat** — ask questions. Network phrases (`add`/`connect` + OSPF/BGP) run the change pipeline.
- **Change Studio** — form: request, sample configs (R1/R2/R3), approval, tabbed review (intent, IOS, risk, Ansible).
- **Topology** — upload a diagram (GNS3 / Packet Tracer / sketch / course SVG). Gemini vision extracts devices and links, checks them against mock NetBox, and can send an OSPF/BGP suggestion to Change Studio.

## Lab inventory

| Device | Role | Notes |
| --- | --- | --- |
| R1 | core | OSPF already advertises `192.168.10.0/24` |
| R2 | distribution | OSPF already advertises `192.168.20.0/24` |
| R3 | access | No OSPF yet |
| SW1 | access | In NetBox only (no IOS generation) |

Sample IOS: `configs/R1.cfg`, `R2.cfg`, `R3.cfg`. Mock SoT: `data/netbox_mock.json`.

## Setup

Python 3.11+ recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:7860**. Restart the process after code or `.env` changes (`uvicorn` does not auto-reload).

## Optional LLM

The app runs **without** an API key using the rule-based parser. For richer chat and better intent parsing, add a Google AI Studio key (new keys often look like `AQ.…`; prefer `gemini-flash-lite-latest` — `gemini-2.5-flash` is blocked for many new projects, and free-tier per-model quotas are small).

Create `.env` (gitignored):

```text
AI_PROVIDER=auto
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-flash-lite-latest
```

OpenAI is optional (`OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4o-mini`). If the API fails or quota is exhausted, intent parsing falls back to regex.

**Never commit `.env` or paste keys into this README, reports, or screenshots.**

## Tests

```powershell
pytest
```

Coverage includes intent parsing, validators, config/rollback/diff, Ansible export, NetBox mock, risk, chat, and pipeline gates (duplicate OSPF, held playbook).

## Demo script (viva)

1. **Valid OSPF**

   ```text
   Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0
   ```

   Expect PASS, IOS delta, rollback, Medium risk (R1 is core), Ansible **held**.

2. **Duplicate OSPF (should FAIL)**

   ```text
   Add OSPF on R1 network 192.168.10.0/24 area 0
   ```

   Expect error: network already exists on sample R1 running-config.

3. **Unsupported protocol (should FAIL)**

   ```text
   Configure RIP on R1
   ```

4. **BGP**

   ```text
   Add BGP neighbor 10.1.2.2 on R1 with local ASN 65001 and remote ASN 65002
   ```

5. **Approval** — tick **I approve this change for export** in Change Studio (or Device context in Chat), generate again → Ansible YAML appears.

6. **Remove**

   ```text
   Remove OSPF network 192.168.10.0/24 area 0 from R1
   ```

Other useful checks: unknown device `R9`, missing BGP ASN, interface `FastEthernet0/0`, broad `/16` subnet (warning), overlap `10.1.1.0/24` vs known `/30` (warning), OSPF process `5` vs existing process `1` (warning).

## What is validated

- Protocol is OSPF or BGP only
- Device exists in mock NetBox; R1 flagged as **core**
- Interface exists if named
- OSPF CIDR + area; BGP neighbor IP + local/remote ASN
- Duplicate OSPF `network` / BGP neighbor vs sample `configs/*.cfg`
- Dangerous strings in pasted config (`reload`, `write erase`, …)
- Redistribute / default-originate / shutdown interface / process-id mismatch (warnings)
- Self-check: generated lines match intent (network, area, neighbor, devices)

## Project layout

```text
SOFT_AM/
  app.py                 FastAPI app + change API
  static/                HTML, CSS, JS UI
  data/netbox_mock.json
  configs/R1.cfg R2.cfg R3.cfg
  src/
    intent_parser.py     LLM + regex
    llm_intent_parser.py
    gemini_client.py
    netbox_client.py
    validators.py
    config_inspector.py  ciscoconfparse
    verifier.py          intent vs IOS
    config_generator.py
    diff_engine.py
    rollback.py
    risk_scorer.py
    ansible_exporter.py
    pipeline.py          orchestrates the change
    chat_assistant.py
  tests/
  PROJECT_REQUIREMENTS.md
```

## Architecture

```text
User (Chat / Change Studio)
        |
        v
Natural language
        |
        v
Intent JSON (LLM or rules)
        |
        v
Mock NetBox + running-config inspect
        |
        v
Rule validation + self-check
        |
        v
IOS delta + diff + rollback + risk
        |
        v
Human approval
        |
        v
Ansible YAML (or hold comment)
```

## Limitations (say this in viva)

- No SSH, no production deploy, no live NetBox API
- OSPF/BGP only (no VLAN, NAT, ACL, VRF, multi-vendor)
- Risk score is **rule-based**, not LLM scoring
- One running-config blob / sample files — not a live `show run`
- Approval is a UI flag, not ITSM/CAB
- Inspired by GeNet topology *understanding*; this copilot still only **generates OSPF/BGP deltas**, not firewalls or full topology rewrites

## Screenshots

Add PNGs under `docs/screenshots/` after a local demo:

| File | Capture |
| --- | --- |
| `docs/screenshots/salon.png` | Chat with a valid OSPF result |
| `docs/screenshots/duplicate-fail.png` | Duplicate `192.168.10.0/24` on R1 |
| `docs/screenshots/atelier-held.png` | Change Studio Ansible held without approval |
| `docs/screenshots/atelier-approved.png` | Playbook after approval |

## Topology images (GeNet-inspired extra)

Image input is supported in the **Topology** tab. It does **not** run the [ICDCS25-GeNet dataset](https://github.com/networkcopilot/ICDCS25-GeNet) through this generator.

Their dataset is mostly:

- Topology pictures (GNS3, PowerPoint, paper sketches)
- Config scenarios such as zone-based firewall, time-based ACL, DMZ, adding PCs

Those labels do not map to this MVP’s OSPF/BGP delta engine. Copying their `Dataset/` folder into this repo would also fall under their **CC BY-NC-SA 4.0** license (attribution + share-alike, non-commercial).

**What to do for viva**

1. Open **Topology**, click a course sample (`lab-ospf.svg`, `bgp-edge-peering.svg`, or the firewall diagram), then **Analyze & Read Diagram**.
2. OSPF/BGP samples should suggest a change; send it to Change Studio.
3. The firewall/DMZ sample should **not** produce IOS — that shows the scope boundary.
4. Optional: screenshot Packet Tracer / GNS3 of this lab and upload PNG/JPG.

Needs `GEMINI_API_KEY` (vision). Without a key, the tab reports that images cannot be read.

## Base paper

Ifland, B. et al. *GeNet: A Multimodal LLM-Based Co-Pilot for Network Topology and Configuration*. [arXiv:2407.08249](https://arxiv.org/abs/2407.08249). ICDCS workshop version: [DOI 10.1109/ICDCSW63273.2025.00026](https://doi.org/10.1109/ICDCSW63273.2025.00026). Code: [networkcopilot/ICDCS25-GeNet](https://github.com/networkcopilot/ICDCS25-GeNet).

This project keeps the **intent → copilot** idea, adds **change review** (validation, delta, rollback, risk, human gate), and uses vision only to **read a diagram**, not to rewrite the whole network.

## License

Academic / coursework use unless the authors add a license file.
