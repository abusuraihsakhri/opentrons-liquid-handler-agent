"""
Protocol Optimization & Dead Volume Minimization for Opentrons Liquid Handler.
Optimizes liquid class parameters for accurate liquid transfers with dead volume prediction.
"""
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class LiquidClassParams:
    """Liquid class parameters for aspiration/dispense optimization."""
    aspiration_speed: float = 100.0       # µL/s
    dispense_speed: float = 100.0         # µL/s
    touch_tip_angle: float = 10.0         # degrees
    touch_tip_distance: float = 2.0       # mm
    mix_cycles: int = 3
    mix_volume: float = 50.0              # µL
    air_gap: float = 5.0                  # µL
    blow_out_volume: float = 0.0          # µL
    pre_wet: bool = True


@dataclass
class WellGeometry:
    """Well geometry parameters for dead volume prediction."""
    well_type: str = "96-flat"            # 96-flat, 96-round, 384-flat, deep-well
    total_volume: float = 360.0           # µL
    bottom_radius: float = 3.27           # mm
    top_radius: float = 3.43              # mm
    well_depth: float = 10.67             # mm
    dead_volume_coefficient: float = 0.05 # fraction of total volume


@dataclass
class TransferResult:
    """Result of a simulated liquid transfer."""
    target_volume: float
    actual_volume: float
    accuracy_percent: float
    precision_cv: float
    dead_volume_remaining: float
    liquid_class: LiquidClassParams
    warnings: List[str] = field(default_factory=list)


class ProtocolOptimizer:
    """Optimize liquid handling protocols for accuracy and dead volume minimization."""

    # Liquid viscosity categories
    VISCOSITY_FACTORS = {
        "aqueous": 1.0,
        "glycerol_10": 1.15,
        "glycerol_50": 1.45,
        "ethanol": 0.85,
        "dmso": 1.30,
        "oil": 2.50,
        "serum": 1.20,
    }

    # Well geometry lookup
    WELL_GEOMETRIES = {
        "96-flat": WellGeometry("96-flat", 360.0, 3.27, 3.43, 10.67, 0.05),
        "96-round": WellGeometry("96-round", 340.0, 3.0, 3.43, 10.67, 0.07),
        "384-flat": WellGeometry("384-flat", 80.0, 1.75, 1.93, 3.64, 0.08),
        "deep-well": WellGeometry("deep-well", 2000.0, 3.43, 3.43, 41.5, 0.03),
        "1536-flat": WellGeometry("1536-flat", 12.0, 0.87, 0.97, 1.52, 0.12),
    }

    def __init__(self):
        self.transfer_log: List[TransferResult] = []

    def predict_dead_volume(self, well_type: str, current_volume: float) -> Dict[str, Any]:
        """Predict position-dependent dead volume for a given well type."""
        geo = self.WELL_GEOMETRIES.get(well_type)
        if geo is None:
            return {"error": f"Unknown well type: {well_type}",
                    "available_types": list(self.WELL_GEOMETRIES.keys())}

        dead_vol = geo.total_volume * geo.dead_volume_coefficient
        recoverable = max(0.0, current_volume - dead_vol)
        recovery_fraction = recoverable / current_volume if current_volume > 0 else 0.0

        # Position-dependent correction based on meniscus height
        fill_fraction = current_volume / geo.total_volume
        if fill_fraction < 0.1:
            position_penalty = 0.15
        elif fill_fraction < 0.3:
            position_penalty = 0.05
        else:
            position_penalty = 0.0

        effective_dead = dead_vol * (1.0 + position_penalty)

        return {
            "well_type": well_type,
            "theoretical_dead_volume_uL": round(dead_vol, 2),
            "effective_dead_volume_uL": round(effective_dead, 2),
            "current_volume_uL": round(current_volume, 2),
            "recoverable_volume_uL": round(recoverable, 2),
            "recovery_fraction": round(recovery_fraction, 4),
            "position_penalty": round(position_penalty, 4),
            "fill_fraction": round(fill_fraction, 4),
        }

    def optimize_liquid_class(
        self,
        volume: float,
        viscosity: str = "aqueous",
        well_type: str = "96-flat",
        tip_type: str = "300µL",
    ) -> LiquidClassParams:
        """Optimize liquid class parameters for target volume and liquid properties."""
        viscosity_factor = self.VISCOSITY_FACTORS.get(viscosity, 1.0)
        geo = self.WELL_GEOMETRIES.get(well_type, self.WELL_GEOMETRIES["96-flat"])

        # Scale aspiration speed by volume and viscosity
        base_asp_speed = 100.0  # µL/s
        volume_factor = min(1.0, volume / 200.0)
        asp_speed = base_asp_speed * volume_factor / viscosity_factor
        disp_speed = asp_speed * 0.8  # dispense slightly slower for accuracy

        # Air gap scales with viscosity
        air_gap = max(2.0, 5.0 * viscosity_factor)

        # Mix cycles based on volume
        if volume < 10:
            mix_cycles = 5
            mix_volume = volume * 0.8
        elif volume < 50:
            mix_cycles = 3
            mix_volume = volume * 0.5
        else:
            mix_cycles = 2
            mix_volume = min(volume * 0.3, 100.0)

        # Touch tip parameters
        touch_tip_distance = max(1.0, 2.0 / viscosity_factor)

        return LiquidClassParams(
            aspiration_speed=round(asp_speed, 1),
            dispense_speed=round(disp_speed, 1),
            touch_tip_angle=10.0,
            touch_tip_distance=round(touch_tip_distance, 1),
            mix_cycles=mix_cycles,
            mix_volume=round(mix_volume, 1),
            air_gap=round(air_gap, 1),
            blow_out_volume=max(0.0, volume * 0.1),
            pre_wet=(volume > 20),
        )

    def simulate_transfer(
        self,
        target_volume: float,
        liquid_class: Optional[LiquidClassParams] = None,
        viscosity: str = "aqueous",
        well_type: str = "96-flat",
        n_replicates: int = 1,
    ) -> TransferResult:
        """Simulate a liquid transfer and predict accuracy/precision."""
        if liquid_class is None:
            liquid_class = self.optimize_liquid_class(target_volume, viscosity, well_type)

        viscosity_factor = self.VISCOSITY_FACTORS.get(viscosity, 1.0)

        # Accuracy model: deviation increases with small volumes and high viscosity
        base_accuracy = 0.98
        volume_penalty = max(0.0, (10.0 - target_volume) * 0.005)
        viscosity_penalty = (viscosity_factor - 1.0) * 0.02
        pre_wet_bonus = 0.01 if liquid_class.pre_wet else 0.0

        accuracy = base_accuracy - volume_penalty - viscosity_penalty + pre_wet_bonus
        accuracy = max(0.85, min(1.02, accuracy))

        actual_volume = target_volume * accuracy

        # Precision CV model
        base_cv = 1.0  # %
        cv_volume = max(0.0, (20.0 - target_volume) * 0.15)
        cv_viscosity = (viscosity_factor - 1.0) * 1.5
        precision_cv = base_cv + cv_volume + cv_viscosity

        # Dead volume
        dead_info = self.predict_dead_volume(well_type, 300.0)

        warnings = []
        if target_volume < 5:
            warnings.append("Volume below 5µL: accuracy may be significantly reduced")
        if viscosity_factor > 1.5:
            warnings.append("High viscosity liquid: consider slower aspiration speeds")
        if precision_cv > 5.0:
            warnings.append(f"Predicted CV ({precision_cv:.1f}%) exceeds typical acceptance criteria (5%)")

        result = TransferResult(
            target_volume=target_volume,
            actual_volume=round(actual_volume, 2),
            accuracy_percent=round(accuracy * 100, 2),
            precision_cv=round(precision_cv, 2),
            dead_volume_remaining=dead_info["effective_dead_volume_uL"],
            liquid_class=liquid_class,
            warnings=warnings,
        )
        self.transfer_log.append(result)
        return result

    def generate_protocol_report(self) -> Dict[str, Any]:
        """Generate a summary report of all simulated transfers."""
        if not self.transfer_log:
            return {"status": "no_transfers_simulated"}

        accuracies = [r.accuracy_percent for r in self.transfer_log]
        cvs = [r.precision_cv for r in self.transfer_log]
        all_warnings = []
        for r in self.transfer_log:
            all_warnings.extend(r.warnings)

        return {
            "total_transfers": len(self.transfer_log),
            "mean_accuracy_percent": round(sum(accuracies) / len(accuracies), 2),
            "mean_cv_percent": round(sum(cvs) / len(cvs), 2),
            "worst_accuracy_percent": round(min(accuracies), 2),
            "worst_cv_percent": round(max(cvs), 2),
            "total_warnings": len(all_warnings),
            "unique_warnings": list(set(all_warnings)),
            "all_within_spec": all(95 <= a <= 105 for a in accuracies) and all(c <= 5.0 for c in cvs),
        }
