"""
Security and validation tests for opentrons-liquid-handler-agent.
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import tempfile
import warnings
from agents.base import AuditTrail, PHIGuard, SecurityException, assert_no_phi
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from cli import main


class TestPHIGuard:
    """Test PHI outbound guard enforcement."""

    def test_mrn_detection(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Patient MRN-994827 blood culture positive")

    def test_ssn_detection(self):
        with pytest.raises(SecurityException):
            assert_no_phi("SSN: 123-45-6789")

    def test_phone_detection(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Call patient at 555-123-4567")

    def test_email_detection(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Email patient at john@example.com")

    def test_clean_text_passes(self):
        assert_no_phi("Analytical assay specimen KEY-001 optimal") is None

    def test_empty_text_passes(self):
        assert_no_phi("") is None

    def test_none_text_passes(self):
        assert_no_phi(None) is None

    def test_redact_phi(self):
        redacted = PHIGuard.redact_phi("Patient MRN-994827 needs follow-up")
        assert "MRN" not in redacted
        assert "[REDACTED_IDENTIFIER]" in redacted


class TestAuditTrail:
    """Test HMAC-SHA256 audit trail functionality."""

    def test_custom_secret_key(self):
        at = AuditTrail(secret_key="test-secret-key")
        assert at.secret_key == b"test-secret-key"

    def test_ephemeral_key_generation(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            at = AuditTrail()
            assert len(at.secret_key) > 0

    def test_audit_logging(self):
        at = AuditTrail(secret_key="test-key")
        entry = at.log("test_actor", "test_tier", "TEST_EVENT", {"data": "value"})
        assert entry["actor"] == "test_actor"
        assert entry["event_type"] == "TEST_EVENT"
        assert entry["current_hash"] != ""

    def test_integrity_verification(self):
        at = AuditTrail(secret_key="test-key")
        at.log("actor1", "tier1", "EVENT1", {"data": "1"})
        at.log("actor2", "tier2", "EVENT2", {"data": "2"})
        assert at.verify_integrity() is True

    def test_chain_linking(self):
        at = AuditTrail(secret_key="test-key")
        entry1 = at.log("actor1", "tier1", "EVENT1", {"data": "1"})
        entry2 = at.log("actor2", "tier2", "EVENT2", {"data": "2"})
        assert entry2["prev_hash"] == entry1["current_hash"]


class TestCLIValidation:
    """Test CLI input validation and error handling."""

    def test_batch_missing_file(self):
        result = main(["batch", "-i", "nonexistent_file.csv"])
        assert result == 1

    def test_batch_with_valid_csv(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            f.write("task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag,status_descriptor\n")
            f.write("T1,KEY-01,12.0,4.0,False,NOMINAL\n")
            f.write("T2,KEY-02,35.0,15.0,True,DISCORDANT\n")
            temp_path = f.name

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out_f:
                out_path = out_f.name

            result = main(["batch", "-i", temp_path, "-o", out_path])
            assert result == 0
            assert os.path.exists(out_path)

            with open(out_path, 'r') as f:
                content = f.read()
                assert "overall_urgency" in content
        finally:
            os.unlink(temp_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_batch_with_invalid_data(self):
        """Test that batch processing handles invalid rows gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            f.write("task_id,target_identifier,primary_metric,secondary_metric\n")
            f.write("T1,KEY-01,invalid,4.0\n")
            f.write("T2,KEY-02,12.0,4.0\n")
            temp_path = f.name

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out_f:
                out_path = out_f.name

            result = main(["batch", "-i", temp_path, "-o", out_path])
            assert result == 0
        finally:
            os.unlink(temp_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_audit_command(self):
        result = main(["audit", "--task-id", "TEST-01"])
        assert result == 0

    def test_chat_command(self):
        result = main(["chat", "test", "query"])
        assert result == 0

    def test_verify_audit_command(self):
        result = main(["verify-audit"])
        assert result == 0


class TestSupervisorPHIGuard:
    """Test that supervisor enforces PHI guard on payloads."""

    def test_phi_in_task_id_blocked(self):
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id="MRN-994827",
            target_identifier="KEY-01",
            primary_metric=12.0,
        )
        with pytest.raises(SecurityException):
            supervisor.process_task(payload)

    def test_phi_in_target_blocked(self):
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id="TASK-01",
            target_identifier="Patient John Doe",
            primary_metric=12.0,
        )
        with pytest.raises(SecurityException):
            supervisor.process_task(payload)

    def test_clean_payload_processed(self):
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id="TASK-01",
            target_identifier="KEY-01",
            primary_metric=12.0,
            secondary_metric=4.0,
            status_descriptor="NOMINAL",
        )
        dossier = supervisor.process_task(payload)
        assert dossier.task_id == "TASK-01"
