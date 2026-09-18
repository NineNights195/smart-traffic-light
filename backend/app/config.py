from dataclasses import dataclass
from math import ceil


MIN_GREEN = 5.0
MAX_GREEN = 20.0
TIME_PER_VEHICLE = 3.0
PERSON_CONFIRM = 1.5
NO_PERSON_CONFIRM = 1.5
YELLOW_DURATION = 3.0
ALL_RED_TO_PED_DURATION = 1.0
ALL_RED_TO_VEHICLE_DURATION = 1.0
MIN_PED_WALK = 4.0
MAX_PED_WALK = 30.0
CROSSWALK_DISTANCE_M = 6.0
WALKING_SPEED_MPS = 1.0
FLASH_INTERVAL = 0.5
SENSOR_MAX_AGE = 2.0
PEDESTRIAN_ENTRY_DELAY = 1.5


@dataclass(frozen=True, slots=True)
class TrafficConfig:
    """All timing and safety policy values for the educational simulation."""

    min_green: float = MIN_GREEN
    max_green: float = MAX_GREEN
    time_per_vehicle: float = TIME_PER_VEHICLE
    person_confirm: float = PERSON_CONFIRM
    no_person_confirm: float = NO_PERSON_CONFIRM
    yellow_duration: float = YELLOW_DURATION
    all_red_to_ped_duration: float = ALL_RED_TO_PED_DURATION
    all_red_to_vehicle_duration: float = ALL_RED_TO_VEHICLE_DURATION
    min_ped_walk: float = MIN_PED_WALK
    max_ped_walk: float = MAX_PED_WALK
    crosswalk_distance_m: float = CROSSWALK_DISTANCE_M
    walking_speed_mps: float = WALKING_SPEED_MPS
    flash_interval: float = FLASH_INTERVAL
    sensor_max_age: float = SENSOR_MAX_AGE
    vehicle_discharge_interval: float = 1.0
    pedestrian_entry_delay: float = PEDESTRIAN_ENTRY_DELAY

    # Simulation policy, not a standard for real road infrastructure.
    sensor_fault_vehicle_light: str = "RED"
    sensor_fault_pedestrian_signal: str = "DONT_WALK"
    freeze_movement_on_sensor_fault: bool = True

    @property
    def pedestrian_clearance_duration(self) -> int:
        if self.walking_speed_mps <= 0:
            raise ValueError("walking_speed_mps must be greater than zero")
        return ceil(self.crosswalk_distance_m / self.walking_speed_mps)


DEFAULT_CONFIG = TrafficConfig()
