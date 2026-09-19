export type Phase =
  | 'VEHICLE_GREEN'
  | 'VEHICLE_YELLOW'
  | 'ALL_RED_TO_PED'
  | 'PED_WALK'
  | 'PED_CLEARANCE'
  | 'ALL_RED_TO_VEHICLE'
  | 'SENSOR_FAULT'

export type VehicleLight = 'RED' | 'YELLOW' | 'GREEN' | 'FLASHING_YELLOW'
export type PedestrianSignal =
  | 'OFF'
  | 'DONT_WALK'
  | 'WALK'
  | 'FLASHING_DONT_WALK'

export interface SimulationState {
  phase: Phase
  vehicle_light: VehicleLight
  pedestrian_signal: PedestrianSignal
  phase_elapsed: number
  time_remaining: number | null
  target_green_duration: number
  pedestrian_clearance_duration: number
  transition_reason: string
  sensor_status: string
  sensor_age: number | null
  flash_on: boolean
  vehicle_queue_by_lane: Record<'1' | '2', number>
  total_vehicle_queue: number
  people_waiting_zone: number
  people_on_crosswalk: number
  people_outside_zones: number
  sensor_available: boolean
  captured_at: number
}
