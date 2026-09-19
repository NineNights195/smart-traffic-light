from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class Phase(str, Enum):
    VEHICLE_GREEN = "VEHICLE_GREEN"
    VEHICLE_YELLOW = "VEHICLE_YELLOW"
    ALL_RED_TO_PED = "ALL_RED_TO_PED"
    PED_WALK = "PED_WALK"
    PED_CLEARANCE = "PED_CLEARANCE"
    ALL_RED_TO_VEHICLE = "ALL_RED_TO_VEHICLE"
    SENSOR_FAULT = "SENSOR_FAULT"


class VehicleLight(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    FLASHING_YELLOW = "FLASHING_YELLOW"


class PedestrianSignal(str, Enum):
    OFF = "OFF"
    DONT_WALK = "DONT_WALK"
    WALK = "WALK"
    FLASHING_DONT_WALK = "FLASHING_DONT_WALK"


@dataclass(frozen=True, slots=True)
class SensorSnapshot:
    """Zone-aware sensor data consumed by the traffic-control domain."""

    vehicle_queue_by_lane: Mapping[int, int]
    people_waiting_zone: int
    people_on_crosswalk: int
    people_outside_zones: int
    sensor_available: bool
    captured_at: float

    def __post_init__(self) -> None:
        counts = (
            *self.vehicle_queue_by_lane.values(),
            self.people_waiting_zone,
            self.people_on_crosswalk,
            self.people_outside_zones,
        )
        if any(count < 0 for count in counts):
            raise ValueError("Sensor counts cannot be negative")

    @property
    def total_vehicle_queue(self) -> int:
        return sum(self.vehicle_queue_by_lane.values())


@dataclass(frozen=True, slots=True)
class ControllerState:
    phase: Phase
    vehicle_light: VehicleLight
    pedestrian_signal: PedestrianSignal
    phase_elapsed: float
    time_remaining: float | None
    target_green_duration: float
    pedestrian_clearance_duration: int
    transition_reason: str
    sensor_status: str
    sensor_age: float | None
    flash_on: bool
