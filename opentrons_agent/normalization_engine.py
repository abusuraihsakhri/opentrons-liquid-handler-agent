"""
Normalization & Dilution Calculator for Opentrons Liquid Handler.
Automated dilution scheme generation for sample normalization with error propagation.
"""
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class SampleConcentration:
    """Sample concentration measurement with uncertainty."""
    sample_id: str
    concentration: float          # ng/µL or target units
    uncertainty: float = 0.0      # standard deviation
    volume_available: float = 0.0 # µL
    unit: str = "ng/uL"


@dataclass
class DilutionStep:
    """Single step in a dilution scheme."""
    step_number: int
    sample_id: str
    source_volume_uL: float
    diluent_volume_uL: float
    dilution_factor: float
    resulting_concentration: float
    resulting_volume_uL: float
    source_well: str
    destination_well: str
    uncertainty_propagated: float = 0.0


@dataclass
class DilutionScheme:
    """Complete dilution scheme for a set of samples."""
    target_concentration: float
    target_volume: float
    unit: str
    steps: List[DilutionStep] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_diluent_needed: float = 0.0
    total_sample_needed: float = 0.0


class NormalizationEngine:
    """Automated dilution scheme generation for sample normalization."""

    # Minimum pipetting volumes for accuracy
    MIN_PIPETTE_VOLUME = 1.0   # µL
    MAX_PIPETTE_VOLUME = 200.0 # µL
    OPTIMAL_VOLUME_RANGE = (10.0, 150.0)

    def __init__(self, dead_volume: float = 5.0):
        if not math.isfinite(dead_volume) or dead_volume < 0:
            raise ValueError("dead_volume must be a finite non-negative number")
        self.dead_volume = dead_volume

    def calculate_simple_dilution(
        self,
        sample: SampleConcentration,
        target_concentration: float,
        target_volume: float,
    ) -> DilutionStep:
        """Calculate a single dilution step from source to target concentration."""
        if not all(math.isfinite(v) for v in (
            sample.concentration, sample.uncertainty, sample.volume_available,
            target_concentration, target_volume
        )):
            raise ValueError("Concentrations and volumes must be finite")
        if sample.concentration <= 0 or target_concentration <= 0 or target_volume <= 0:
            raise ValueError("Concentrations and target volume must be positive")
        if sample.uncertainty < 0 or sample.volume_available < 0:
            raise ValueError("Uncertainty and available volume must be non-negative")
        if sample.concentration < target_concentration:
            raise ValueError("A lower-concentration stock cannot reach the target by dilution")
        if sample.concentration == target_concentration:
            # No dilution needed for an exact concentration match
            return DilutionStep(
                step_number=1,
                sample_id=sample.sample_id,
                source_volume_uL=target_volume,
                diluent_volume_uL=0.0,
                dilution_factor=1.0,
                resulting_concentration=sample.concentration,
                resulting_volume_uL=target_volume,
                source_well="",
                destination_well="",
            )

        # C1 * V1 = C2 * V2 => V1 = C2 * V2 / C1
        dilution_factor = sample.concentration / target_concentration
        source_volume = target_volume / dilution_factor
        diluent_volume = target_volume - source_volume

        # Error propagation: δC2/C2 = sqrt((δC1/C1)² + (δV1/V1)² + (δV2/V2)²)
        # Assume volume uncertainty ~2% for pipetting
        vol_uncertainty = 0.02
        if sample.uncertainty > 0 and sample.concentration > 0:
            conc_rel_unc = sample.uncertainty / sample.concentration
            propagated_unc = target_concentration * math.sqrt(
                conc_rel_unc**2 + vol_uncertainty**2 + vol_uncertainty**2
            )
        else:
            propagated_unc = target_concentration * math.sqrt(2) * vol_uncertainty

        return DilutionStep(
            step_number=1,
            sample_id=sample.sample_id,
            source_volume_uL=round(source_volume, 2),
            diluent_volume_uL=round(diluent_volume, 2),
            dilution_factor=round(dilution_factor, 4),
            resulting_concentration=round(target_concentration, 2),
            resulting_volume_uL=round(target_volume, 2),
            source_well="",
            destination_well="",
            uncertainty_propagated=round(propagated_unc, 4),
        )

    def calculate_serial_dilution(
        self,
        initial_concentration: float,
        dilution_factor: float,
        num_steps: int,
        volume_per_step: float = 100.0,
    ) -> List[DilutionStep]:
        """Generate a serial dilution scheme with well mapping."""
        if not all(math.isfinite(v) for v in (initial_concentration, dilution_factor, volume_per_step)):
            raise ValueError("Serial dilution inputs must be finite")
        if initial_concentration <= 0 or dilution_factor <= 1 or volume_per_step <= 0:
            raise ValueError("Use positive concentration/volume and dilution factor above 1")
        if not isinstance(num_steps, int) or not 1 <= num_steps <= 384:
            raise ValueError("num_steps must be an integer between 1 and 384")
        steps = []
        current_conc = initial_concentration

        for i in range(num_steps):
            source_volume = volume_per_step / dilution_factor
            diluent_volume = volume_per_step - source_volume
            current_conc = current_conc / dilution_factor

            # Map to wells (A1->A2->A3 etc.)
            source_well = f"A{i}" if i > 0 else "Stock"
            dest_well = f"A{i + 1}"

            steps.append(DilutionStep(
                step_number=i + 1,
                sample_id=f"serial_dilution_{i + 1}",
                source_volume_uL=round(source_volume, 2),
                diluent_volume_uL=round(diluent_volume, 2),
                dilution_factor=round(dilution_factor, 4),
                resulting_concentration=round(current_conc, 4),
                resulting_volume_uL=round(volume_per_step, 2),
                source_well=source_well,
                destination_well=dest_well,
            ))

        return steps

    def normalize_samples(
        self,
        samples: List[SampleConcentration],
        target_concentration: float,
        target_volume: float,
        well_plate_format: str = "96",
    ) -> DilutionScheme:
        """Normalize a set of samples to a common target concentration."""
        scheme = DilutionScheme(
            target_concentration=target_concentration,
            target_volume=target_volume,
            unit=samples[0].unit if samples else "ng/uL",
        )

        # Determine well plate layout and reject overflow before indexing.
        if well_plate_format not in ("96", "384"):
            raise ValueError("well_plate_format must be '96' or '384'")
        capacity = int(well_plate_format)
        if len(samples) > capacity:
            raise ValueError(f"{len(samples)} samples exceed the {capacity}-well capacity")
        if samples and not all(sample.unit == samples[0].unit for sample in samples):
            raise ValueError("All samples must use the same concentration unit")
        rows = "ABCDEFGH" if well_plate_format == "96" else "ABCDEFGHIJKLMNOP"
        cols = 12 if well_plate_format == "96" else 24

        for idx, sample in enumerate(samples):
            well_row = rows[idx // cols]
            well_col = (idx % cols) + 1
            dest_well = f"{well_row}{well_col}"

            step = self.calculate_simple_dilution(
                sample, target_concentration, target_volume
            )
            step.step_number = idx + 1
            step.source_well = f"Source_{sample.sample_id}"
            step.destination_well = dest_well

            # Generate warnings
            if step.source_volume_uL < self.MIN_PIPETTE_VOLUME:
                scheme.warnings.append(
                    f"Sample {sample.sample_id}: source volume ({step.source_volume_uL} µL) "
                    f"below minimum pipetting volume ({self.MIN_PIPETTE_VOLUME} µL). "
                    f"Consider a pre-dilution step."
                )
            if sample.volume_available > 0 and step.source_volume_uL > sample.volume_available:
                scheme.warnings.append(
                    f"Sample {sample.sample_id}: required volume ({step.source_volume_uL} µL) "
                    f"exceeds available volume ({sample.volume_available} µL)."
                )
            if step.source_volume_uL < self.OPTIMAL_VOLUME_RANGE[0]:
                scheme.warnings.append(
                    f"Sample {sample.sample_id}: source volume ({step.source_volume_uL} µL) "
                    f"below optimal range. Accuracy may be reduced."
                )

            scheme.steps.append(step)
            scheme.total_diluent_needed += step.diluent_volume_uL
            scheme.total_sample_needed += step.source_volume_uL

        return scheme

    def back_calculate_from_target(
        self,
        target_concentration: float,
        target_volume: float,
        stock_concentration: float,
    ) -> Dict[str, Any]:
        """Back-calculate required stock volume and diluent for a target."""
        if not all(math.isfinite(v) for v in (target_concentration, target_volume, stock_concentration)):
            raise ValueError("Concentrations and volume must be finite")
        if min(target_concentration, target_volume, stock_concentration) <= 0:
            raise ValueError("Concentrations and volume must be positive")
        if stock_concentration == target_concentration:
            return {
                "feasible": True, "direct_dilution": True,
                "stock_volume_uL": round(target_volume, 2),
                "diluent_volume_uL": 0.0, "dilution_factor": 1.0,
                "total_volume_uL": round(target_volume, 2),
            }
        if stock_concentration < target_concentration:
            return {
                "feasible": False,
                "reason": "Stock concentration is at or below target concentration",
                "stock_concentration": stock_concentration,
                "target_concentration": target_concentration,
            }

        dilution_factor = stock_concentration / target_concentration
        stock_volume = target_volume / dilution_factor
        diluent_volume = target_volume - stock_volume

        # Check if a serial dilution is needed
        if stock_volume < self.MIN_PIPETTE_VOLUME:
            # Recommend serial dilution
            serial_steps = math.ceil(math.log10(dilution_factor) / math.log10(10))
            intermediate_factor = dilution_factor ** (1.0 / serial_steps)

            return {
                "feasible": True,
                "direct_dilution": False,
                "recommendation": "serial_dilution",
                "serial_steps": serial_steps,
                "intermediate_dilution_factor": round(intermediate_factor, 4),
                "direct_stock_volume_uL": round(stock_volume, 4),
                "reason": f"Direct stock volume ({stock_volume:.4f} µL) below minimum. "
                          f"Use {serial_steps}-step serial dilution with factor {intermediate_factor:.2f} each.",
            }

        return {
            "feasible": True,
            "direct_dilution": True,
            "stock_volume_uL": round(stock_volume, 2),
            "diluent_volume_uL": round(diluent_volume, 2),
            "dilution_factor": round(dilution_factor, 4),
            "total_volume_uL": round(target_volume, 2),
        }

    def generate_dilution_report(self, scheme: DilutionScheme) -> Dict[str, Any]:
        """Generate a summary report for a dilution scheme."""
        return {
            "target_concentration": scheme.target_concentration,
            "target_volume": scheme.target_volume,
            "unit": scheme.unit,
            "total_samples": len(scheme.steps),
            "total_diluent_needed_uL": round(scheme.total_diluent_needed, 2),
            "total_sample_needed_uL": round(scheme.total_sample_needed, 2),
            "warnings": scheme.warnings,
            "warning_count": len(scheme.warnings),
            "steps": [
                {
                    "step": s.step_number,
                    "sample_id": s.sample_id,
                    "source_vol_uL": s.source_volume_uL,
                    "diluent_vol_uL": s.diluent_volume_uL,
                    "dilution_factor": s.dilution_factor,
                    "result_conc": s.resulting_concentration,
                    "dest_well": s.destination_well,
                    "uncertainty": s.uncertainty_propagated,
                }
                for s in scheme.steps
            ],
        }
