from pathlib import Path

from src.pipeline import execute_change
from src.chat_assistant import chat_response
from src.netbox_client import MockNetBox
from src.topology_vision import describe_topology

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

try:
    from fastapi import FastAPI, File, UploadFile
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
except ModuleNotFoundError:
    FastAPI = None
    File = None
    UploadFile = None
    FileResponse = None
    StaticFiles = None
    BaseModel = object
    Field = None


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
NETBOX = MockNetBox(BASE_DIR / "data" / "netbox_mock.json")
DEFAULT_CONFIG = "hostname R1\ninterface GigabitEthernet0/0\n no shutdown\n"

SAMPLE_CONFIGS = {
    "Minimal R1": DEFAULT_CONFIG,
}
for device in ("R1", "R2", "R3"):
    config_path = BASE_DIR / "configs" / f"{device}.cfg"
    if config_path.exists():
        SAMPLE_CONFIGS[device] = config_path.read_text(encoding="utf-8")

CHANGE_EXAMPLES = [
    "Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0",
    "Add BGP neighbor 10.1.2.2 on R1 with local ASN 65001 and remote ASN 65002",
    "Remove OSPF network 10.1.1.0/30 area 0 from R1",
]
TOPOLOGY_SAMPLES_DIR = STATIC_DIR / "topology_samples"


def list_topology_samples() -> list[dict[str, str]]:
    if not TOPOLOGY_SAMPLES_DIR.exists():
        return []
    labels = {
        "lab-ospf.svg": "Campus OSPF (3-router core)",
        "bgp-edge-peering.svg": "HQ + branch eBGP",
        "firewall-dmz-out-of-scope.svg": "Firewall / DMZ (out of scope)",
    }
    samples = []
    for path in sorted(TOPOLOGY_SAMPLES_DIR.iterdir()):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            continue
        samples.append(
            {
                "id": path.name,
                "label": labels.get(path.name, path.stem.replace("-", " ")),
                "url": f"/static/topology_samples/{path.name}?v=campus-2",
            }
        )
    return samples


def process_change(request_text: str, existing_config: str, approval: bool):
    if not request_text.strip():
        return "{}", "No request provided.", "", "", "", "", "", "Not approved"

    result = execute_change(request_text, NETBOX, existing_config, approval)
    return (
        result.intent.to_pretty_json(),
        result.validation_report(),
        result.generated_text,
        result.diff,
        result.rollback,
        result.risk_report(),
        result.playbook,
        result.approval_status,
    )


def respond_chat(
    message: str,
    history: list[dict[str, str]],
    existing_config: str,
    approval: bool,
    topology: dict | None = None,
    studio: dict | None = None,
):
    return chat_response(message, history, NETBOX, existing_config, approval, topology, studio)


def load_sample_config(name: str) -> str:
    return SAMPLE_CONFIGS.get(name, DEFAULT_CONFIG)


if FastAPI is not None:
    class ChatIn(BaseModel):
        message: str
        history: list[dict[str, str]] = Field(default_factory=list)
        existing_config: str = ""
        approval: bool = False
        topology: dict | None = None
        studio: dict | None = None

    class ChangeIn(BaseModel):
        request_text: str
        existing_config: str = ""
        approval: bool = False

    web = FastAPI(title="Network Assistance — AI Copilot")
    web.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @web.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @web.get("/api/meta")
    def api_meta():
        return {
            "examples": CHANGE_EXAMPLES,
            "configs": SAMPLE_CONFIGS,
            "default_config": DEFAULT_CONFIG,
            "topology_samples": list_topology_samples(),
        }

    @web.post("/api/chat")
    def api_chat(payload: ChatIn):
        try:
            reply = respond_chat(
                payload.message,
                payload.history,
                payload.existing_config,
                payload.approval,
                payload.topology,
                payload.studio,
            )
            return {"reply": reply}
        except Exception as exc:
            return {"reply": f"I hit an internal error while handling that request: {exc}"}

    @web.post("/api/topology")
    async def api_topology(file: UploadFile = File(...)):
        payload = await file.read()
        if len(payload) > 4_000_000:
            return {"ok": False, "error": "Image is larger than 4 MB."}
        mime = file.content_type or "image/jpeg"
        if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}:
            mime = "image/png"
        return describe_topology(payload, mime, NETBOX)

    @web.post("/api/change")
    def api_change(payload: ChangeIn):
        intent, validation, config, diff, rollback, risk, playbook, status = process_change(
            payload.request_text,
            payload.existing_config,
            payload.approval,
        )
        return {
            "intent": intent,
            "validation": validation,
            "config": config,
            "diff": diff,
            "rollback": rollback,
            "risk": risk,
            "playbook": playbook,
            "approval_status": status,
            "rejected": status.startswith("Rejected") or status == "Not approved",
        }
else:
    web = None


if __name__ == "__main__":
    if web is None:
        raise RuntimeError("FastAPI is not installed. Run: pip install -r requirements.txt")
    import uvicorn

    uvicorn.run("app:web", host="127.0.0.1", port=7860, reload=False)
