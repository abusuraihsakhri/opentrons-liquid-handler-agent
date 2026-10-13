"""
FastAPI REST API Server for Opentrons Liquid Handler Agent.
"""
import hmac
import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Opentrons Liquid Handler Agent API",
    description="Enterprise Distributed Component Platform (AI Drug Discovery, Structural Biology & Wet-Lab Robotics)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "opentrons-liquid-handler-agent", "domain": "AI Drug Discovery, Structural Biology & Wet-Lab Robotics", "standard": "wwPDB / IUPAC / OpenSMILES / ISAC Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
        return dossier.to_dict()
    except SecurityException:
        raise HTTPException(status_code=422, detail="Sensitive identifiers are not accepted")
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid task payload")


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        raise HTTPException(status_code=422, detail="Sensitive identifiers are not accepted")


@app.get("/api/audit/logs")
def api_audit_logs(x_audit_log_key: str = Header(default="")):
    expected = os.environ.get("AUDIT_LOG_ACCESS_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Audit log access is not configured")
    if not hmac.compare_digest(x_audit_log_key, expected):
        raise HTTPException(status_code=403, detail="Audit log access denied")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
