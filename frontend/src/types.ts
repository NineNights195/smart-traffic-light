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

export interface SimulationConfig {
  min_green: number
  max_green: number
  time_per_vehicle: number
  person_confirm: number
  no_person_confirm: number
  yellow_duration: number
  all_red_to_ped_duration: number
  all_red_to_vehicle_duration: number
  min_ped_walk: number
  max_ped_walk: number
  crosswalk_distance_m: number
  walking_speed_mps: number
  flash_interval: number
  sensor_max_age: number
  pedestrian_entry_delay: number
  sensor_fault_vehicle_light: string
  sensor_fault_pedestrian_signal: string
  freeze_movement_on_sensor_fault: boolean
  pedestrian_clearance_duration: number
}

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
  config: SimulationConfig
}
