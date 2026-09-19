from app.models import Phase
from app.simulation import SimulationService


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_vehicle_queue_represents_waiting_vehicles_and_drains_on_green() -> None:
    clock = FakeClock()
    simulation = SimulationService(clock=clock)

    added = simulation.add_vehicles(lane=1, count=3)
    clock.advance(1)
    moved = simulation.state()

    assert added["vehicle_queue_by_lane"] == {"1": 3, "2": 0}
    assert moved["vehicle_queue_by_lane"] == {"1": 2, "2": 0}
    assert moved["total_vehicle_queue"] == 2


def test_sensor_fault_freezes_entities_and_uses_fallback() -> None:
    clock = FakeClock()
    simulation = SimulationService(clock=clock)
    simulation.add_vehicles(lane=1, count=2)

    fault = simulation.set_sensor_available(available=False)
    clock.advance(5)
    still_faulted = simulation.state()

    assert fault["phase"] == Phase.SENSOR_FAULT.value
    assert fault["vehicle_light"] == "FLASHING_YELLOW"
    assert fault["pedestrian_signal"] == "OFF"
    assert still_faulted["vehicle_queue_by_lane"] == {"1": 2, "2": 0}


def test_sensor_recovery_does_not_skip_buffer() -> None:
    clock = FakeClock()
    simulation = SimulationService(clock=clock)
    simulation.set_sensor_available(available=False)

    recovered = simulation.set_sensor_available(available=True)
    clock.advance(1)
    green = simulation.state()

    assert recovered["phase"] == Phase.ALL_RED_TO_VEHICLE.value
    assert green["phase"] == Phase.VEHICLE_GREEN.value


def test_reset_restores_controller_and_all_simulation_counts() -> None:
    clock = FakeClock()
    simulation = SimulationService(clock=clock)
    simulation.add_vehicles(lane=2, count=4)
    simulation.add_pedestrians(zone="waiting_left", count=3)
    simulation.set_sensor_available(available=False)

    reset = simulation.reset()

    assert reset["phase"] == Phase.VEHICLE_GREEN.value
    assert reset["vehicle_queue_by_lane"] == {"1": 0, "2": 0}
    assert reset["people_waiting_zone"] == 0
    assert reset["people_on_crosswalk"] == 0
    assert reset["sensor_available"] is True
    assert reset["sensor_status"] == "OK"


def test_waiting_pedestrians_move_to_crosswalk_during_walk_phase() -> None:
    clock = FakeClock()
    simulation = SimulationService(clock=clock)
    simulation.add_pedestrians(zone="waiting_left", count=2)

    clock.advance(5)
    simulation.state()
    clock.advance(3)
    simulation.state()
    clock.advance(1)
    walking = simulation.state()

    assert walking["phase"] == Phase.PED_WALK.value
    assert walking["people_waiting_zone"] == 0
    assert walking["people_on_crosswalk"] == 2


def test_pedestrians_added_during_walk_wait_before_entering_crosswalk() -> None:
    clock = FakeClock()
    simulation = SimulationService(clock=clock)
    simulation.add_pedestrians(zone="waiting_left", count=2)

    clock.advance(5)
    simulation.state()
    clock.advance(3)
    simulation.state()
    clock.advance(1)
    simulation.state()

    added_during_walk = simulation.add_pedestrians(zone="waiting_right", count=1)
    clock.advance(1.4)
    still_waiting = simulation.state()
    clock.advance(0.1)
    joined_crosswalk = simulation.state()

    assert added_during_walk["phase"] == Phase.PED_WALK.value
    assert added_during_walk["people_waiting_zone"] == 1
    assert added_during_walk["people_on_crosswalk"] == 2
    assert still_waiting["people_waiting_zone"] == 1
    assert still_waiting["people_on_crosswalk"] == 2
    assert joined_crosswalk["people_waiting_zone"] == 0
    assert joined_crosswalk["people_on_crosswalk"] == 3
