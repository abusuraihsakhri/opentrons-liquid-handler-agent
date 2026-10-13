"""Regression checks for audit authenticity, numerical feasibility and data protection."""
import math
import pytest

from agents.base import AuditTrail, SecurityException
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from opentrons_agent.audit_trail import ActionType, AuditTrail as PipettingAuditTrail
from opentrons_agent.normalization_engine import NormalizationEngine, SampleConcentration


def test_audit_detects_field_tampering():
    trail = AuditTrail(secret_key="unit-test-secret")
    trail.log("operator", "supervisor", "PROCESS", {"status": "SUCCESS"})
    trail.log("operator", "supervisor", "PROCESS", {"status": "SUCCESS"})
    assert trail.verify_integrity()
    trail.logs[0]["event_type"] = "ALTERED"
    assert not trail.verify_integrity()


def test_audit_readers_receive_copies():
    trail = AuditTrail(secret_key="unit-test-secret")
    trail.log("operator", "supervisor", "PROCESS", {"status": "SUCCESS"})
    snapshot = trail.get_trail()
    snapshot[0]["event_type"] = "ALTERED"
    assert trail.verify_integrity()


def test_audit_blocks_phi_in_actor():
    trail = AuditTrail(secret_key="unit-test-secret")
    with pytest.raises(SecurityException):
        trail.log("Patient John Doe", "supervisor", "PROCESS", {"status": "SUCCESS"})


def test_pipetting_hash_covers_error_and_liquid_class():
    trail = PipettingAuditTrail("DEMO")
    entry = trail.log_action(ActionType.DISPENSE, 10.0, liquid_class="aqueous")
    assert trail.verify_chain_integrity()["status"] == "VALID"
    entry.liquid_class = "modified"
    assert trail.verify_chain_integrity()["status"] == "COMPROMISED"


def test_pipetting_hash_covers_error_message():
    trail = PipettingAuditTrail("DEMO")
    entry = trail.log_action(ActionType.ERROR, 0.0, error_message="original")
    entry.error_message = "changed"
    assert trail.verify_chain_integrity()["status"] == "COMPROMISED"


def test_serial_dilution_source_tracks_previous_well():
    engine = NormalizationEngine()
    steps = engine.calculate_serial_dilution(100.0, 10.0, 3)
    assert [(s.source_well, s.destination_well) for s in steps] == [
        ("Stock", "A1"), ("A1", "A2"), ("A2", "A3")
    ]


def test_dilution_cannot_concentrate_sample():
    engine = NormalizationEngine()
    sample = SampleConcentration("S1", concentration=5.0)
    with pytest.raises(ValueError, match="cannot reach"):
        engine.calculate_simple_dilution(sample, 10.0, 100.0)


def test_matching_concentrations_require_no_diluent():
    engine = NormalizationEngine()
    result = engine.back_calculate_from_target(10.0, 50.0, 10.0)
    assert result["feasible"] is True
    assert result["stock_volume_uL"] == 50.0
    assert result["diluent_volume_uL"] == 0.0


def test_plate_bounds_and_nonfinite_inputs():
    engine = NormalizationEngine()
    sample = SampleConcentration("S1", concentration=20.0)
    with pytest.raises(ValueError, match="capacity"):
        engine.normalize_samples([sample] * 97, 10.0, 100.0)
    with pytest.raises(ValueError):
        engine.calculate_serial_dilution(10.0, 1.0, 3)
    with pytest.raises(ValueError):
        engine.calculate_simple_dilution(sample, math.nan, 100.0)


def test_supervisor_rejects_phi_in_attributes():
    payload = SystemTaskPayload(
        task_id="DEMO", target_identifier="S01",
        primary_metric=12.0, attributes={"contact": "john@example.com"},
    )
    with pytest.raises(SecurityException):
        SystemSupervisor().process_task(payload)


def test_supervisor_rejects_nan_metrics():
    with pytest.raises(ValueError):
        SystemTaskPayload(task_id="DEMO", target_identifier="S01", primary_metric=math.nan)
