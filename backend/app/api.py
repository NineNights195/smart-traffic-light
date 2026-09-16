from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .simulation import SimulationService


class VehicleRequest(BaseModel):
    lane: int = Field(ge=1, le=2)
    count: int = Field(default=1, ge=1, le=20)


class PedestrianRequest(BaseModel):
    zone: str = "waiting_left"
    count: int = Field(default=1, ge=1, le=20)


class SensorRequest(BaseModel):
    available: bool


app = FastAPI(
    title="Smart Traffic Light Simulation API",
    version="1.0.0",
    description="Educational traffic-control simulation; not for real roads.",
)
simulation = SimulationService()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/state")
def get_state() -> dict[str, object]:
    return simulation.state()


@app.post("/api/simulation/vehicles")
def add_vehicles(request: VehicleRequest) -> dict[str, object]:
    return simulation.add_vehicles(lane=request.lane, count=request.count)


@app.post("/api/simulation/pedestrians")
def add_pedestrians(request: PedestrianRequest) -> dict[str, object]:
    try:
        return simulation.add_pedestrians(zone=request.zone, count=request.count)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/simulation/sensor")
def set_sensor(request: SensorRequest) -> dict[str, object]:
    return simulation.set_sensor_available(available=request.available)


@app.post("/api/simulation/reset")
def reset_simulation() -> dict[str, object]:
    return simulation.reset()

