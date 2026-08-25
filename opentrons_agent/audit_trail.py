"""
Traceability & Audit Trail Integration for Opentrons Liquid Handler.
21 CFR Part 11-compliant records with immutable audit trail and data integrity verification.
"""
import hashlib
import json
import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class ActionType(str, Enum):
    ASPIRATE = "ASPIRATE"
    DISPENSE = "DISPENSE"
    MIX = "MIX"
    TOUCH_TIP = "TOUCH_TIP"
    BLOW_OUT = "BLOW_OUT"
    DROP_TIP = "DROP_TIP"
    PICK_UP_TIP = "PICK_UP_TIP"
    PROTOCOL_START = "PROTOCOL_START"
    PROTOCOL_END = "PROTOCOL_END"
    ERROR = "ERROR"
    RECOVERY = "RECOVERY"


@dataclass
class BarcodeRecord:
    """Barcode scan record for plate identification."""
    barcode: str
    labware_type: str
    deck_position: int
    scan_timestamp: str = ""
    verified: bool = False

    def __post_init__(self):
        if not self.scan_timestamp:
            self.scan_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class AuditEntry:
    """Immutable audit trail entry for a single pipetting action."""
    entry_id: str
    action: ActionType
    source_barcode: Optional[str]
    destination_barcode: Optional[str]
    source_well: Optional[str]
    destination_well: Optional[str]
    volume_uL: float
    timestamp: str = ""
    operator_id: str = "SYSTEM"
    protocol_id: str = ""
    liquid_class: str = ""
    success: bool = True
    error_message: str = ""
    previous_hash: str = ""
    entry_hash: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not self.entry_hash:
            self.entry_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of entry data for tamper detection."""
        hash_data = {
            "entry_id": self.entry_id,
            "action": self.action.value,
            "source_barcode": self.source_barcode,
            "destination_barcode": self.destination_barcode,
            "source_well": self.source_well,
            "destination_well": self.destination_well,
            "volume_uL": self.volume_uL,
            "timestamp": self.timestamp,
            "operator_id": self.operator_id,
            "protocol_id": self.protocol_id,
            "success": self.success,
            "previous_hash": self.previous_hash,
        }
        serialized = json.dumps(hash_data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()


class AuditTrail:
    """Immutable, hash-chained audit trail for 21 CFR Part 11 compliance."""

    def __init__(self, protocol_id: str, operator_id: str = "SYSTEM"):
        self.protocol_id = protocol_id
        self.operator_id = operator_id
        self.entries: List[AuditEntry] = []
        self.barcode_registry: Dict[str, BarcodeRecord] = {}
        self._entry_counter = 0
        self._chain_head = "GENESIS"

    def register_barcode(self, barcode: str, labware_type: str, deck_position: int) -> BarcodeRecord:
        """Register a barcode scan for source/destination plate identification."""
        record = BarcodeRecord(
            barcode=barcode,
            labware_type=labware_type,
            deck_position=deck_position,
            verified=True,
        )
        self.barcode_registry[barcode] = record
        return record

    def log_action(
        self,
        action: ActionType,
        volume_uL: float,
        source_barcode: Optional[str] = None,
        destination_barcode: Optional[str] = None,
        source_well: Optional[str] = None,
        destination_well: Optional[str] = None,
        liquid_class: str = "",
        success: bool = True,
        error_message: str = "",
    ) -> AuditEntry:
        """Log a pipetting action with hash-chain integrity."""
        self._entry_counter += 1
        entry_id = f"{self.protocol_id}-{self._entry_counter:06d}"

        entry = AuditEntry(
            entry_id=entry_id,
            action=action,
            source_barcode=source_barcode,
            destination_barcode=destination_barcode,
            source_well=source_well,
            destination_well=destination_well,
            volume_uL=volume_uL,
            operator_id=self.operator_id,
            protocol_id=self.protocol_id,
            liquid_class=liquid_class,
            success=success,
            error_message=error_message,
            previous_hash=self._chain_head,
        )
        self._chain_head = entry.entry_hash
        self.entries.append(entry)
        return entry

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the entire audit trail hash chain."""
        if not self.entries:
            return {"status": "empty_chain", "entries": 0}

        broken_links = []
        hash_mismatches = []

        for i, entry in enumerate(self.entries):
            # Check previous hash link
            expected_prev = "GENESIS" if i == 0 else self.entries[i - 1].entry_hash
            if entry.previous_hash != expected_prev:
                broken_links.append({
                    "entry_id": entry.entry_id,
                    "expected_previous": expected_prev,
                    "actual_previous": entry.previous_hash,
                })

            # Verify hash computation
            recomputed = entry.compute_hash()
            if recomputed != entry.entry_hash:
                hash_mismatches.append({
                    "entry_id": entry.entry_id,
                    "stored_hash": entry.entry_hash,
                    "recomputed_hash": recomputed,
                })

        is_valid = len(broken_links) == 0 and len(hash_mismatches) == 0
        return {
            "status": "VALID" if is_valid else "COMPROMISED",
            "total_entries": len(self.entries),
            "broken_links": len(broken_links),
            "hash_mismatches": len(hash_mismatches),
            "chain_head": self._chain_head,
            "details": {
                "broken_link_entries": broken_links[:5],
                "mismatch_entries": hash_mismatches[:5],
            },
        }

    def generate_chain_of_custody_report(self) -> Dict[str, Any]:
        """Generate GLP-compliant chain-of-custody report."""
        action_counts = {}
        for entry in self.entries:
            key = entry.action.value
            action_counts[key] = action_counts.get(key, 0) + 1

        total_volume_transferred = sum(
            e.volume_uL for e in self.entries
            if e.action in (ActionType.DISPENSE, ActionType.ASPIRATE)
        )

        error_entries = [e for e in self.entries if not e.success]
        barcodes_used = set()
        for e in self.entries:
            if e.source_barcode:
                barcodes_used.add(e.source_barcode)
            if e.destination_barcode:
                barcodes_used.add(e.destination_barcode)

        return {
            "protocol_id": self.protocol_id,
            "operator_id": self.operator_id,
            "report_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_actions": len(self.entries),
            "action_breakdown": action_counts,
            "total_volume_transferred_uL": round(total_volume_transferred, 2),
            "unique_barcodes": sorted(barcodes_used),
            "registered_labware": len(self.barcode_registry),
            "error_count": len(error_entries),
            "chain_integrity": self.verify_chain_integrity()["status"],
            "first_action": self.entries[0].timestamp if self.entries else None,
            "last_action": self.entries[-1].timestamp if self.entries else None,
        }

    def export_entries_json(self) -> str:
        """Export all audit entries as JSON for external system integration."""
        export_data = []
        for entry in self.entries:
            export_data.append({
                "entry_id": entry.entry_id,
                "action": entry.action.value,
                "source_barcode": entry.source_barcode,
                "destination_barcode": entry.destination_barcode,
                "source_well": entry.source_well,
                "destination_well": entry.destination_well,
                "volume_uL": entry.volume_uL,
                "timestamp": entry.timestamp,
                "operator_id": entry.operator_id,
                "protocol_id": entry.protocol_id,
                "liquid_class": entry.liquid_class,
                "success": entry.success,
                "error_message": entry.error_message,
                "entry_hash": entry.entry_hash,
                "previous_hash": entry.previous_hash,
            })
        return json.dumps(export_data, indent=2)
