from dataclasses import replace

import pytest

from app.config import TrafficConfig
from app.models import (
    ControllerState,
    PedestrianSignal,
    Phase,
    SensorSnapshot,
    VehicleLight,
)
from app.state_machine import StateMachine


def snapshot(
    *,
    now: float,
    waiting: int = 0,
    crossing: int = 0,
    outside: int = 0,
    lane_1: int = 0,
    lane_2: int = 0,
    available: bool = True,
    captured_at: float | None = None,
) -> SensorSnapshot:
    return SensorSnapshot(
        vehicle_queue_by_lane={1: lane_1, 2: lane_2},
        people_waiting_zone=waiting,
        people_on_crosswalk=crossing,
        people_outside_zones=outside,
        sensor_available=available,
        captured_at=now if captured_at is None else captured_at,
    )


def enter_ped_walk(machine: StateMachine) -> None:
    machine.update(snapshot=snapshot(now=0, waiting=1), now=0)
    machine.update(snapshot=snapshot(now=5, waiting=1), now=5)
    assert machine.phase is Phase.VEHICLE_YELLOW
    machine.update(snapshot=snapshot(now=8, waiting=1), now=8)
    assert machine.phase is Phase.ALL_RED_TO_PED
    machine.update(snapshot=snapshot(now=9, waiting=1), now=9)
    assert machine.phase is Phase.PED_WALK


def enter_vehicle_green_after_ped_cycle(
    machine: StateMachine,
    *,
    queued_vehicles: int,
) -> ControllerState:
    enter_ped_walk(machine)
    machine.update(snapshot=snapshot(now=13), now=13)
    machine.update(snapshot=snapshot(now=14.5), now=14.5)
    assert machine.phase is Phase.PED_CLEARANCE
    machine.update(snapshot=snapshot(now=20.5), now=20.5)
    assert machine.phase is Phase.ALL_RED_TO_VEHICLE
    state = machine.update(
        snapshot=snapshot(now=21.5, lane_1=queued_vehicles),
        now=21.5,
    )
    assert machine.phase is Phase.VEHICLE_GREEN
    return state


def test_initial_state_is_vehicle_green() -> None:
    machine = StateMachine(now=10)

    state = machine.update(snapshot=snapshot(now=10), now=10)

    assert state.phase is Phase.VEHICLE_GREEN
    assert state.vehicle_light is VehicleLight.GREEN
    assert state.pedestrian_signal is PedestrianSignal.DONT_WALK


def test_people_outside_zones_do_not_request_pedestrian_phase() -> None:
    machine = StateMachine(now=0)

    machine.update(snapshot=snapshot(now=0, outside=4), now=0)
    state = machine.update(snapshot=snapshot(now=10, outside=4), now=10)

    assert state.phase is Phase.VEHICLE_GREEN


def test_single_detection_frame_does_not_change_phase() -> None:
    machine = StateMachine(now=0)

    machine.update(snapshot=snapshot(now=0, waiting=1), now=0)
    state = machine.update(snapshot=snapshot(now=2, waiting=0), now=2)
    state = machine.update(snapshot=snapshot(now=6, waiting=0), now=6)

    assert state.phase is Phase.VEHICLE_GREEN


def test_person_confirm_and_green_target_are_both_required() -> None:
    machine = StateMachine(now=0)

    machine.update(snapshot=snapshot(now=0, waiting=1), now=0)
    before_confirm = machine.update(snapshot=snapshot(now=1.4, waiting=1), now=1.4)
    before_minimum = machine.update(snapshot=snapshot(now=2, waiting=1), now=2)
    after_both = machine.update(snapshot=snapshot(now=5, waiting=1), now=5)

    assert before_confirm.phase is Phase.VEHICLE_GREEN
    assert before_minimum.phase is Phase.VEHICLE_GREEN
    assert after_both.phase is Phase.VEHICLE_YELLOW


def test_vehicles_and_people_still_pass_through_yellow() -> None:
    machine = StateMachine(now=0)

    machine.update(snapshot=snapshot(now=0, waiting=1, lane_1=5), now=0)
    state = machine.update(snapshot=snapshot(now=5, waiting=1), now=5)

    assert state.phase is Phase.VEHICLE_YELLOW
    assert state.vehicle_light is VehicleLight.YELLOW


def test_yellow_all_red_and_ped_walk_sequence() -> None:
    machine = StateMachine(now=0)

    machine.update(snapshot=snapshot(now=0, waiting=1), now=0)
    yellow = machine.update(snapshot=snapshot(now=5, waiting=1), now=5)
    all_red = machine.update(snapshot=snapshot(now=8, waiting=1), now=8)
    walk = machine.update(snapshot=snapshot(now=9, waiting=1), now=9)

    assert [yellow.phase, all_red.phase, walk.phase] == [
        Phase.VEHICLE_YELLOW,
        Phase.ALL_RED_TO_PED,
        Phase.PED_WALK,
    ]


def test_pedestrian_clearance_always_flashes_dont_walk() -> None:
    machine = StateMachine(now=0)
    enter_ped_walk(machine)

    machine.update(snapshot=snapshot(now=13), now=13)
    clearance = machine.update(snapshot=snapshot(now=14.5), now=14.5)

    assert clearance.phase is Phase.PED_CLEARANCE
    assert clearance.vehicle_light is VehicleLight.RED
    assert clearance.pedestrian_signal is PedestrianSignal.FLASHING_DONT_WALK


def test_clearance_duration_uses_distance_and_speed_not_people_count() -> None:
    short = TrafficConfig(crosswalk_distance_m=6, walking_speed_mps=1)
    long = replace(short, crosswalk_distance_m=7, walking_speed_mps=0.8)

    assert short.pedestrian_clearance_duration == 6
    assert long.pedestrian_clearance_duration == 9

    first = StateMachine(now=0, config=short)
    second = StateMachine(now=0, config=short)
    enter_ped_walk(first)
    enter_ped_walk(second)
    first.update(snapshot=snapshot(now=13, crossing=1), now=13)
    second.update(snapshot=snapshot(now=13, crossing=12), now=13)

    assert first.current_state(snapshot=snapshot(now=13), now=13).pedestrian_clearance_duration == 6
    assert second.current_state(snapshot=snapshot(now=13), now=13).pedestrian_clearance_duration == 6


def test_no_person_confirmation_resets_when_a_person_reappears() -> None:
    machine = StateMachine(now=0)
    enter_ped_walk(machine)

    machine.update(snapshot=snapshot(now=13), now=13)
    machine.update(snapshot=snapshot(now=14, crossing=1), now=14)
    machine.update(snapshot=snapshot(now=15), now=15)
    still_walking = machine.update(snapshot=snapshot(now=16.4), now=16.4)
    clearance = machine.update(snapshot=snapshot(now=16.5), now=16.5)

    assert still_walking.phase is Phase.PED_WALK
    assert clearance.phase is Phase.PED_CLEARANCE


@pytest.mark.parametrize(
    ("waiting", "crossing"),
    [(1, 0), (0, 1), (1, 1)],
)
def test_ped_walk_stays_active_after_timeout_until_a_vehicle_appears(
    waiting: int,
    crossing: int,
) -> None:
    machine = StateMachine(now=0)
    enter_ped_walk(machine)

    timed_out = machine.update(
        snapshot=snapshot(now=39, waiting=waiting, crossing=crossing),
        now=39,
    )
    still_walking = machine.update(snapshot=snapshot(now=45), now=45)
    vehicle_arrived = machine.update(
        snapshot=snapshot(now=46, lane_1=1),
        now=46,
    )

    assert timed_out.phase is Phase.PED_WALK
    assert timed_out.time_remaining == 0
    assert (
        timed_out.transition_reason
        == "Pedestrian walk extended until a vehicle is detected"
    )
    assert still_walking.phase is Phase.PED_WALK
    assert vehicle_arrived.phase is Phase.PED_CLEARANCE


def test_ped_walk_timeout_still_applies_when_a_vehicle_is_waiting() -> None:
    machine = StateMachine(now=0)
    enter_ped_walk(machine)

    state = machine.update(
        snapshot=snapshot(now=39, waiting=1, crossing=1, lane_1=1),
        now=39,
    )

    assert state.phase is Phase.PED_CLEARANCE


@pytest.mark.parametrize(
    ("queue", "expected"),
    [(0, 5), (1, 5), (3, 5), (5, 5), (10, 10), (100, 15)],
)
def test_queue_controls_bounded_green_target(queue: int, expected: float) -> None:
    machine = StateMachine(now=0)

    target = machine.calculate_target_green(
        total_vehicle_queue=queue,
    )

    assert target == expected
    assert 5 <= target <= 15


def test_new_vehicle_queue_extends_green_target_up_to_maximum() -> None:
    machine = StateMachine(now=0)

    started = enter_vehicle_green_after_ped_cycle(
        machine,
        queued_vehicles=3,
    )
    medium_arrival = machine.update(
        snapshot=snapshot(now=23.5, lane_2=5),
        now=23.5,
    )
    large_arrival = machine.update(
        snapshot=snapshot(now=24.5, lane_2=100),
        now=24.5,
    )

    assert started.target_green_duration == 5
    assert medium_arrival.target_green_duration == 7
    assert large_arrival.target_green_duration == 15


def test_pedestrian_waits_for_green_target_before_transition() -> None:
    machine = StateMachine(now=0)
    started = enter_vehicle_green_after_ped_cycle(
        machine,
        queued_vehicles=10,
    )

    machine.update(snapshot=snapshot(now=22, waiting=1), now=22)
    after_minimum = machine.update(
        snapshot=snapshot(now=26.5, waiting=1),
        now=26.5,
    )
    before_target = machine.update(
        snapshot=snapshot(now=31.4, waiting=1),
        now=31.4,
    )
    target_complete = machine.update(
        snapshot=snapshot(now=31.5, waiting=1),
        now=31.5,
    )

    assert started.target_green_duration == 10
    assert after_minimum.phase is Phase.VEHICLE_GREEN
    assert before_target.phase is Phase.VEHICLE_GREEN
    assert target_complete.phase is Phase.VEHICLE_YELLOW


def test_new_cars_delay_pedestrian_only_long_enough_to_clear_queue() -> None:
    machine = StateMachine(now=0)
    enter_vehicle_green_after_ped_cycle(
        machine,
        queued_vehicles=3,
    )

    machine.update(snapshot=snapshot(now=22, waiting=1), now=22)
    extended = machine.update(
        snapshot=snapshot(now=26, waiting=1, lane_1=3),
        now=26,
    )
    before_extended_target = machine.update(
        snapshot=snapshot(now=28.9, waiting=1),
        now=28.9,
    )
    target_complete = machine.update(
        snapshot=snapshot(now=29, waiting=1),
        now=29,
    )

    assert extended.target_green_duration == 7.5
    assert before_extended_target.phase is Phase.VEHICLE_GREEN
    assert target_complete.phase is Phase.VEHICLE_YELLOW


@pytest.mark.parametrize(
    "bad_snapshot",
    [
        None,
        snapshot(now=0, available=False),
        snapshot(now=0, captured_at=0),
    ],
)
def test_missing_unavailable_or_stale_sensor_enters_fault(
    bad_snapshot: SensorSnapshot | None,
) -> None:
    machine = StateMachine(now=0)
    now = 3 if bad_snapshot and bad_snapshot.sensor_available else 0

    state = machine.update(snapshot=bad_snapshot, now=now)

    assert state.phase is Phase.SENSOR_FAULT
    assert state.vehicle_light is VehicleLight.FLASHING_YELLOW
    assert state.pedestrian_signal is PedestrianSignal.OFF


def test_sensor_fault_flashes_vehicle_yellow() -> None:
    machine = StateMachine(now=0)

    flash_on = machine.update(
        snapshot=snapshot(now=0, available=False),
        now=0,
    )
    flash_off = machine.update(
        snapshot=snapshot(now=0.5, available=False),
        now=0.5,
    )

    assert flash_on.flash_on is True
    assert flash_off.flash_on is False


def test_sensor_recovery_uses_all_red_buffer_before_green() -> None:
    machine = StateMachine(now=0)
    machine.update(snapshot=snapshot(now=0, available=False), now=0)

    recovered = machine.update(snapshot=snapshot(now=1), now=1)
    still_buffering = machine.update(snapshot=snapshot(now=1.9), now=1.9)
    green = machine.update(snapshot=snapshot(now=2), now=2)

    assert recovered.phase is Phase.ALL_RED_TO_VEHICLE
    assert recovered.vehicle_light is VehicleLight.RED
    assert still_buffering.phase is Phase.ALL_RED_TO_VEHICLE
    assert green.phase is Phase.VEHICLE_GREEN
