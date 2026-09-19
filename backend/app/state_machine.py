from __future__ import annotations

from .config import DEFAULT_CONFIG, TrafficConfig
from .models import (
    ControllerState,
    PedestrianSignal,
    Phase,
    SensorSnapshot,
    VehicleLight,
)


class StateMachine:
    """Pure traffic-control domain logic with an injected monotonic clock value."""

    def __init__(
        self,
        *,
        now: float,
        config: TrafficConfig = DEFAULT_CONFIG,
    ) -> None:
        self.config = config
        self.phase = Phase.VEHICLE_GREEN
        self.phase_started_at = now
        self.target_green_duration = config.min_green
        self.person_detect_started_at: float | None = None
        self.no_person_started_at: float | None = None
        self.ped_walk_waiting_for_vehicle = False
        self.transition_reason = "Controller initialized with vehicle green"

    def reset(self, *, now: float) -> None:
        self.phase = Phase.VEHICLE_GREEN
        self.phase_started_at = now
        self.target_green_duration = self.config.min_green
        self.person_detect_started_at = None
        self.no_person_started_at = None
        self.ped_walk_waiting_for_vehicle = False
        self.transition_reason = "Simulation reset"

    def calculate_target_green(self, *, total_vehicle_queue: int) -> float:
        requested = total_vehicle_queue * self.config.time_per_vehicle
        return min(self.config.max_green, max(self.config.min_green, requested))

    def update(
        self,
        *,
        snapshot: SensorSnapshot | None,
        now: float,
    ) -> ControllerState:
        sensor_error = self._sensor_error(snapshot=snapshot, now=now)
        if sensor_error is not None:
            if self.phase is not Phase.SENSOR_FAULT:
                self._transition(
                    to=Phase.SENSOR_FAULT,
                    now=now,
                    reason=sensor_error,
                )
            else:
                self.transition_reason = sensor_error
            return self.current_state(snapshot=snapshot, now=now)

        assert snapshot is not None
        if self.phase is Phase.SENSOR_FAULT:
            self._transition(
                to=Phase.ALL_RED_TO_VEHICLE,
                now=now,
                reason="Sensor recovered; enforcing all-red safety buffer",
            )
            return self.current_state(snapshot=snapshot, now=now)

        if self.phase is Phase.VEHICLE_GREEN:
            elapsed = now - self.phase_started_at
            queue_clearance_target = min(
                self.config.max_green,
                elapsed
                + snapshot.total_vehicle_queue * self.config.time_per_vehicle,
            )
            self.target_green_duration = max(
                self.target_green_duration,
                queue_clearance_target,
            )

            if snapshot.people_waiting_zone > 0:
                if self.person_detect_started_at is None:
                    self.person_detect_started_at = now
                confirmed = (
                    now - self.person_detect_started_at
                    >= self.config.person_confirm
                )
                green_window_complete = (
                    now - self.phase_started_at >= self.target_green_duration
                )
                if confirmed and green_window_complete:
                    self._transition(
                        to=Phase.VEHICLE_YELLOW,
                        now=now,
                        reason=(
                            "Vehicle-green service window completed for "
                            "confirmed pedestrian request"
                        ),
                    )
            else:
                self.person_detect_started_at = None

        elif self.phase is Phase.VEHICLE_YELLOW:
            if now - self.phase_started_at >= self.config.yellow_duration:
                self._transition(
                    to=Phase.ALL_RED_TO_PED,
                    now=now,
                    reason="Vehicle yellow interval completed",
                )

        elif self.phase is Phase.ALL_RED_TO_PED:
            if (
                now - self.phase_started_at
                >= self.config.all_red_to_ped_duration
            ):
                self._transition(
                    to=Phase.PED_WALK,
                    now=now,
                    reason="All-red pedestrian buffer completed",
                )

        elif self.phase is Phase.PED_WALK:
            elapsed = now - self.phase_started_at
            if elapsed >= self.config.max_ped_walk:
                pedestrians_present = (
                    snapshot.people_waiting_zone > 0
                    or snapshot.people_on_crosswalk > 0
                )
                vehicles_present = snapshot.total_vehicle_queue > 0
                if self.ped_walk_waiting_for_vehicle:
                    if vehicles_present:
                        self._transition(
                            to=Phase.PED_CLEARANCE,
                            now=now,
                            reason=(
                                "Vehicle detected after extended pedestrian "
                                "walk"
                            ),
                        )
                elif pedestrians_present and not vehicles_present:
                    self.ped_walk_waiting_for_vehicle = True
                    self.transition_reason = (
                        "Pedestrian walk extended until a vehicle is detected"
                    )
                else:
                    self._transition(
                        to=Phase.PED_CLEARANCE,
                        now=now,
                        reason="Maximum pedestrian walk guard reached",
                    )
            elif elapsed >= self.config.min_ped_walk:
                nobody_in_controlled_zones = (
                    snapshot.people_waiting_zone == 0
                    and snapshot.people_on_crosswalk == 0
                )
                if nobody_in_controlled_zones:
                    if self.no_person_started_at is None:
                        self.no_person_started_at = now
                    elif (
                        now - self.no_person_started_at
                        >= self.config.no_person_confirm
                    ):
                        self._transition(
                            to=Phase.PED_CLEARANCE,
                            now=now,
                            reason="Controlled pedestrian zones remained clear",
                        )
                else:
                    self.no_person_started_at = None

        elif self.phase is Phase.PED_CLEARANCE:
            if (
                now - self.phase_started_at
                >= self.config.pedestrian_clearance_duration
            ):
                self._transition(
                    to=Phase.ALL_RED_TO_VEHICLE,
                    now=now,
                    reason="Distance-based pedestrian clearance completed",
                )

        elif self.phase is Phase.ALL_RED_TO_VEHICLE:
            if (
                now - self.phase_started_at
                >= self.config.all_red_to_vehicle_duration
            ):
                self._transition(
                    to=Phase.VEHICLE_GREEN,
                    now=now,
                    reason="All-red vehicle buffer completed",
                    snapshot=snapshot,
                )

        return self.current_state(snapshot=snapshot, now=now)

    def current_state(
        self,
        *,
        snapshot: SensorSnapshot | None,
        now: float,
    ) -> ControllerState:
        elapsed = max(0.0, now - self.phase_started_at)
        sensor_age = (
            None if snapshot is None else max(0.0, now - snapshot.captured_at)
        )
        sensor_error = self._sensor_error(snapshot=snapshot, now=now)
        vehicle_light, pedestrian_signal = self._signals()
        flash_on = (
            self.phase in {Phase.PED_CLEARANCE, Phase.SENSOR_FAULT}
            and int(elapsed / self.config.flash_interval) % 2 == 0
        )
        return ControllerState(
            phase=self.phase,
            vehicle_light=vehicle_light,
            pedestrian_signal=pedestrian_signal,
            phase_elapsed=elapsed,
            time_remaining=self._time_remaining(elapsed=elapsed),
            target_green_duration=self.target_green_duration,
            pedestrian_clearance_duration=(
                self.config.pedestrian_clearance_duration
            ),
            transition_reason=self.transition_reason,
            sensor_status="OK" if sensor_error is None else sensor_error,
            sensor_age=sensor_age,
            flash_on=flash_on,
        )

    def _sensor_error(
        self,
        *,
        snapshot: SensorSnapshot | None,
        now: float,
    ) -> str | None:
        if snapshot is None:
            return "Sensor snapshot missing"
        if not snapshot.sensor_available:
            return "Sensor unavailable"
        if now - snapshot.captured_at > self.config.sensor_max_age:
            return "Sensor data stale"
        return None

    def _transition(
        self,
        *,
        to: Phase,
        now: float,
        reason: str,
        snapshot: SensorSnapshot | None = None,
    ) -> None:
        self.phase = to
        self.phase_started_at = now
        self.person_detect_started_at = None
        self.no_person_started_at = None
        self.ped_walk_waiting_for_vehicle = False
        self.transition_reason = reason
        if to is Phase.VEHICLE_GREEN:
            vehicle_count = 0 if snapshot is None else snapshot.total_vehicle_queue
            self.target_green_duration = self.calculate_target_green(
                total_vehicle_queue=vehicle_count
            )

    def _signals(self) -> tuple[VehicleLight, PedestrianSignal]:
        if self.phase is Phase.SENSOR_FAULT:
            return VehicleLight.FLASHING_YELLOW, PedestrianSignal.OFF
        if self.phase is Phase.VEHICLE_GREEN:
            return VehicleLight.GREEN, PedestrianSignal.DONT_WALK
        if self.phase is Phase.VEHICLE_YELLOW:
            return VehicleLight.YELLOW, PedestrianSignal.DONT_WALK
        if self.phase is Phase.PED_WALK:
            return VehicleLight.RED, PedestrianSignal.WALK
        if self.phase is Phase.PED_CLEARANCE:
            return VehicleLight.RED, PedestrianSignal.FLASHING_DONT_WALK
        return VehicleLight.RED, PedestrianSignal.DONT_WALK

    def _time_remaining(self, *, elapsed: float) -> float | None:
        durations = {
            Phase.VEHICLE_GREEN: self.target_green_duration,
            Phase.VEHICLE_YELLOW: self.config.yellow_duration,
            Phase.ALL_RED_TO_PED: self.config.all_red_to_ped_duration,
            Phase.PED_WALK: self.config.max_ped_walk,
            Phase.PED_CLEARANCE: self.config.pedestrian_clearance_duration,
            Phase.ALL_RED_TO_VEHICLE: self.config.all_red_to_vehicle_duration,
        }
        duration = durations.get(self.phase)
        if duration is None:
            return None
        return max(0.0, duration - elapsed)
