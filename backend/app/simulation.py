from __future__ import annotations

import time
from dataclasses import asdict
from threading import RLock
from typing import Callable, Protocol

from .config import DEFAULT_CONFIG, TrafficConfig
from .models import Phase, SensorSnapshot
from .state_machine import StateMachine


class SensorAdapter(Protocol):
    """Boundary implemented by simulation now and camera adapters later."""

    def snapshot(self, *, now: float) -> SensorSnapshot | None: ...


class SimulationSensorAdapter:
    def __init__(self, *, now: float) -> None:
        self.vehicle_queue_by_lane = {1: 0, 2: 0}
        self.waiting_pedestrian_ready_times: list[float] = []
        self.people_outside_zones = 0
        self.crosswalk_completion_times: list[float] = []
        self.sensor_available = True
        self.last_capture_at = now

    @property
    def people_waiting_zone(self) -> int:
        return len(self.waiting_pedestrian_ready_times)

    def add_waiting_pedestrians(self, *, count: int, ready_at: float) -> None:
        self.waiting_pedestrian_ready_times.extend(ready_at for _ in range(count))

    def snapshot(self, *, now: float) -> SensorSnapshot:
        if self.sensor_available:
            self.last_capture_at = now
        return SensorSnapshot(
            vehicle_queue_by_lane=dict(self.vehicle_queue_by_lane),
            people_waiting_zone=self.people_waiting_zone,
            people_on_crosswalk=len(self.crosswalk_completion_times),
            people_outside_zones=self.people_outside_zones,
            sensor_available=self.sensor_available,
            captured_at=self.last_capture_at,
        )


class SimulationService:
    """Owns deterministic entities and feeds zone snapshots to the controller."""

    def __init__(
        self,
        *,
        config: TrafficConfig = DEFAULT_CONFIG,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.clock = clock
        self._lock = RLock()
        now = clock()
        self.sensor = SimulationSensorAdapter(now=now)
        self.controller = StateMachine(now=now, config=config)
        self.last_vehicle_release_at = now

    def state(self) -> dict[str, object]:
        with self._lock:
            now = self.clock()
            return self._advance(now=now)

    def add_vehicles(self, *, lane: int, count: int) -> dict[str, object]:
        if lane not in (1, 2):
            raise ValueError("lane must be 1 or 2")
        if count < 1:
            raise ValueError("count must be at least 1")
        with self._lock:
            now = self.clock()
            self._advance(now=now)
            self.sensor.vehicle_queue_by_lane[lane] += count
            return self._advance(now=now)

    def add_pedestrians(self, *, zone: str, count: int) -> dict[str, object]:
        if zone not in {"waiting_left", "waiting_right"}:
            raise ValueError("zone must be waiting_left or waiting_right")
        if count < 1:
            raise ValueError("count must be at least 1")
        with self._lock:
            now = self.clock()
            self._advance(now=now)
            self.sensor.add_waiting_pedestrians(
                count=count,
                ready_at=now + self.config.pedestrian_entry_delay,
            )
            return self._advance(now=now)

    def set_sensor_available(self, *, available: bool) -> dict[str, object]:
        with self._lock:
            self.sensor.sensor_available = available
            return self._advance(now=self.clock())

    def reset(self) -> dict[str, object]:
        with self._lock:
            now = self.clock()
            self.sensor = SimulationSensorAdapter(now=now)
            self.controller.reset(now=now)
            self.last_vehicle_release_at = now
            return self._advance(now=now)

    def _advance(self, *, now: float) -> dict[str, object]:
        snapshot = self.sensor.snapshot(now=now)
        controller_state = self.controller.update(snapshot=snapshot, now=now)

        movement_frozen = (
            controller_state.phase is Phase.SENSOR_FAULT
            and self.config.freeze_movement_on_sensor_fault
        )
        if not movement_frozen:
            self._advance_vehicles(now=now, phase=controller_state.phase)
            self._advance_pedestrians(now=now, phase=controller_state.phase)

        # Publish post-movement counts and let the controller observe the newest
        # simulation snapshot at the same monotonic instant.
        snapshot = self.sensor.snapshot(now=now)
        controller_state = self.controller.update(snapshot=snapshot, now=now)
        return self._serialize(controller_state=controller_state, snapshot=snapshot)

    def _advance_vehicles(self, *, now: float, phase: Phase) -> None:
        if phase is not Phase.VEHICLE_GREEN:
            self.last_vehicle_release_at = now
            return
        intervals = int(
            (now - self.last_vehicle_release_at)
            / self.config.time_per_vehicle
        )
        if intervals <= 0:
            return
        for _ in range(intervals):
            lane = max(
                self.sensor.vehicle_queue_by_lane,
                key=lambda lane_number: (
                    self.sensor.vehicle_queue_by_lane[lane_number],
                    -lane_number,
                ),
            )
            if self.sensor.vehicle_queue_by_lane[lane] == 0:
                break
            self.sensor.vehicle_queue_by_lane[lane] -= 1
        self.last_vehicle_release_at += (
            intervals * self.config.time_per_vehicle
        )

    def _advance_pedestrians(self, *, now: float, phase: Phase) -> None:
        self.sensor.crosswalk_completion_times = [
            completion
            for completion in self.sensor.crosswalk_completion_times
            if completion > now
        ]
        if phase is not Phase.PED_WALK:
            return

        ready_to_cross = [
            ready_at
            for ready_at in self.sensor.waiting_pedestrian_ready_times
            if ready_at <= now
        ]
        if not ready_to_cross:
            return

        self.sensor.waiting_pedestrian_ready_times = [
            ready_at
            for ready_at in self.sensor.waiting_pedestrian_ready_times
            if ready_at > now
        ]
        crossing_duration = self.config.pedestrian_clearance_duration
        self.sensor.crosswalk_completion_times.extend(
            now + crossing_duration for _ in ready_to_cross
        )

    def _serialize(self, *, controller_state, snapshot: SensorSnapshot) -> dict[str, object]:
        state = asdict(controller_state)
        state["phase"] = controller_state.phase.value
        state["vehicle_light"] = controller_state.vehicle_light.value
        state["pedestrian_signal"] = controller_state.pedestrian_signal.value
        state["vehicle_queue_by_lane"] = {
            str(lane): count
            for lane, count in snapshot.vehicle_queue_by_lane.items()
        }
        state["total_vehicle_queue"] = snapshot.total_vehicle_queue
        state["people_waiting_zone"] = snapshot.people_waiting_zone
        state["people_on_crosswalk"] = snapshot.people_on_crosswalk
        state["people_outside_zones"] = snapshot.people_outside_zones
        state["sensor_available"] = snapshot.sensor_available
        state["captured_at"] = snapshot.captured_at
        return state
