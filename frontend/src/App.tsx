import { Component, useCallback, useEffect, useState, type CSSProperties } from 'react'
import { simulationApi } from './api'
import type { SimulationState } from './types'
import './App.css'

const POLL_INTERVAL_MS = 350
const GOLDEN_ANGLE = 137.508

const CONFIGURATION_ROWS = [
  ['min_green', 'MIN_GREEN', 's', 'Base vehicle-green service window'],
  ['max_green', 'MAX_GREEN', 's', 'Hard upper bound for the active green window'],
  ['time_per_vehicle', 'TIME_PER_VEHICLE', 's', 'Service and discharge time per vehicle'],
  ['person_confirm', 'PERSON_CONFIRM', 's', 'Continuous waiting-zone presence required'],
  ['no_person_confirm', 'NO_PERSON_CONFIRM', 's', 'Continuous empty controlled zones required'],
  ['yellow_duration', 'YELLOW_DURATION', 's', 'Fixed vehicle-yellow interval'],
  ['all_red_to_ped_duration', 'ALL_RED_TO_PED_DURATION', 's', 'Safety buffer before pedestrian walk'],
  ['all_red_to_vehicle_duration', 'ALL_RED_TO_VEHICLE_DURATION', 's', 'Safety buffer before vehicle green'],
  ['min_ped_walk', 'MIN_PED_WALK', 's', 'Minimum pedestrian walk interval'],
  ['max_ped_walk', 'MAX_PED_WALK', 's', 'Walk timeout when vehicle demand exists'],
  ['crosswalk_distance_m', 'CROSSWALK_DISTANCE_M', 'm', 'Crossing distance used for clearance'],
  ['walking_speed_mps', 'WALKING_SPEED_MPS', 'm/s', 'Assumed pedestrian walking speed'],
  ['pedestrian_clearance_duration', 'PEDESTRIAN_CLEARANCE_DURATION', 's', 'Derived clearance time (distance ÷ speed)'],
  ['flash_interval', 'FLASH_INTERVAL', 's', 'Signal flash interval'],
  ['sensor_max_age', 'SENSOR_MAX_AGE', 's', 'Maximum sensor snapshot age'],
  ['pedestrian_entry_delay', 'PEDESTRIAN_ENTRY_DELAY', 's', 'Delay before a new pedestrian starts crossing'],
  ['sensor_fault_vehicle_light', 'SENSOR_FAULT_VEHICLE_LIGHT', '', 'Vehicle signal during a sensor fault'],
  ['sensor_fault_pedestrian_signal', 'SENSOR_FAULT_PEDESTRIAN_SIGNAL', '', 'Pedestrian signal during a sensor fault'],
  ['freeze_movement_on_sensor_fault', 'FREEZE_MOVEMENT_ON_SENSOR_FAULT', '', 'Freeze simulated entities during a fault'],
] as const satisfies ReadonlyArray<readonly [keyof SimulationState['config'], string, string, string]>

interface VisualEntity {
  id: number
  hue: number
}

let nextVisualEntityId = 1

function createVisualEntity(): VisualEntity {
  const id = nextVisualEntityId++
  return {
    id,
    hue: Math.round((id * GOLDEN_ANGLE) % 360),
  }
}

function formatSeconds(value: number | null) {
  return value === null ? '—' : `${value.toFixed(1)}s`
}

function formatConfigValue(value: number | string | boolean, unit: string) {
  if (typeof value === 'boolean') return value ? 'Enabled' : 'Disabled'
  return `${value}${unit ? ` ${unit}` : ''}`
}

interface EntityStackProps {
  count: number
  kind: 'car' | 'person'
  limit?: number
}

interface EntityStackState {
  count: number
  entities: VisualEntity[]
}

class EntityStack extends Component<EntityStackProps, EntityStackState> {
  state: EntityStackState = {
    count: this.props.count,
    entities: Array.from({ length: this.props.count }, createVisualEntity),
  }

  static getDerivedStateFromProps(
    props: EntityStackProps,
    state: EntityStackState,
  ): EntityStackState | null {
    if (props.count === state.count) return null

    const entities = [...state.entities]
    const difference = props.count - state.count
    if (difference > 0) {
      entities.push(
        ...Array.from({ length: difference }, createVisualEntity),
      )
    } else {
      entities.splice(0, -difference)
    }

    return { count: props.count, entities }
  }

  render() {
    const { count, kind, limit = 8 } = this.props
    const shown = this.state.entities.slice(0, limit)
    return (
      <div className={`${kind}-stack`} aria-label={`${count} ${kind}s`}>
        {shown.map((entity) => (
          <span
            className={kind}
            key={entity.id}
            style={{ '--entity-hue': entity.hue } as CSSProperties}
            aria-hidden="true"
          >
            <i /><b />
          </span>
        ))}
        {count > limit && <span className="overflow-count">+{count - limit}</span>}
      </div>
    )
  }
}

function VehicleSignal({ state }: { state: SimulationState }) {
  return (
    <div className="vehicle-signal" aria-label={`Vehicle light ${state.vehicle_light}`}>
      {(['RED', 'YELLOW', 'GREEN'] as const).map((light) => (
        <span
          key={light}
          className={`bulb ${light.toLowerCase()} ${
            state.vehicle_light === light
            || (state.vehicle_light === 'FLASHING_YELLOW'
              && light === 'YELLOW'
              && state.flash_on)
              ? 'active'
              : ''
          }`}
        />
      ))}
    </div>
  )
}

function PedestrianLight({ state }: { state: SimulationState }) {
  const stopIlluminated =
    state.pedestrian_signal === 'DONT_WALK'
    || (state.pedestrian_signal === 'FLASHING_DONT_WALK' && state.flash_on)
  return (
    <div className="pedestrian-light" aria-label={`Pedestrian signal ${state.pedestrian_signal}`}>
      <span className={`ped-icon stop ${stopIlluminated ? 'active' : ''}`}>✋</span>
      <span className={`ped-icon walk ${state.pedestrian_signal === 'WALK' ? 'active' : ''}`}>●</span>
    </div>
  )
}

function Intersection({ state }: { state: SimulationState }) {
  return (
    <section className="intersection-card" aria-label="Intersection simulation">
      <div className="scene-heading">
        <div>
          <span className="eyebrow">Live intersection</span>
          <h2>Two-lane crossing</h2>
        </div>
        <span className={`live-pill ${state.sensor_available ? '' : 'fault'}`}>
          <i /> {state.sensor_available ? 'Sensor live' : 'Movement frozen'}
        </span>
      </div>

      <div className={`intersection ${state.phase === 'SENSOR_FAULT' ? 'frozen' : ''}`}>
        <div className="waiting-zone">
          <span className="zone-label">Waiting zone</span>
          <EntityStack count={state.people_waiting_zone} kind="person" />
        </div>

        <div className="signal-cluster">
          <VehicleSignal state={state} />
          <PedestrianLight state={state} />
        </div>

        <div className="road">
          <div className="lane lane-one">
            <span className="lane-label">LANE 1</span>
            <EntityStack count={state.vehicle_queue_by_lane['1']} kind="car" />
            <span className="direction">→</span>
          </div>
          <div className="center-line" />
          <div className="lane lane-two">
            <span className="lane-label">LANE 2</span>
            <EntityStack count={state.vehicle_queue_by_lane['2']} kind="car" />
            <span className="direction">→</span>
          </div>
          <div className="crosswalk" aria-label="Crosswalk">
            {Array.from({ length: 7 }, (_, index) => <i key={index} />)}
            <div className="crosswalk-people">
              <EntityStack count={state.people_on_crosswalk} kind="person" limit={10} />
            </div>
          </div>
          <div className="stop-line" />
        </div>
      </div>
    </section>
  )
}

function Metric({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </div>
  )
}

function App() {
  const [state, setState] = useState<SimulationState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const nextState = await simulationApi.state(signal)
      setState(nextState)
      setError(null)
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') return
      setError(caught instanceof Error ? caught.message : 'Backend unavailable')
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const initialPoll = window.setTimeout(
      () => void refresh(controller.signal),
      0,
    )
    const interval = window.setInterval(() => void refresh(controller.signal), POLL_INTERVAL_MS)
    return () => {
      window.clearTimeout(initialPoll)
      window.clearInterval(interval)
      controller.abort()
    }
  }, [refresh])

  const runAction = async (action: () => Promise<SimulationState>) => {
    setPending(true)
    try {
      setState(await action())
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Action failed')
    } finally {
      setPending(false)
    }
  }

  if (!state) {
    return (
      <main className="loading-screen">
        <div className="loading-mark">STL</div>
        <h1>Connecting to simulation…</h1>
        <p>{error ?? 'Waiting for the FastAPI backend on port 8000.'}</p>
        <button type="button" onClick={() => void refresh()}>Retry connection</button>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <title>Smart Traffic Light Simulation</title>
      <header className="topbar">
        <div className="brand-mark" aria-hidden="true"><i /><i /><i /></div>
        <div>
          <span className="eyebrow">Educational control lab</span>
          <h1>Smart Traffic Light</h1>
        </div>
        <div className="phase-block">
          <span>Current phase</span>
          <strong>{state.phase.replaceAll('_', ' ')}</strong>
        </div>
      </header>

      {error && <div className="error-banner" role="alert">{error}</div>}
      {state.phase === 'SENSOR_FAULT' && (
        <div className="fault-banner" role="alert">
          <strong>Sensor fault safety fallback active</strong>
          <span>All movement is frozen. Vehicle FLASHING YELLOW · Pedestrian OFF</span>
        </div>
      )}

      <div className="dashboard-grid">
        <Intersection state={state} />

        <aside className="control-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Simulation input</span>
              <h2>Control desk</h2>
            </div>
            <span className="timer">{formatSeconds(state.time_remaining)}</span>
          </div>

          <div className="control-group">
            <span className="control-label">Vehicle queues</span>
            <button disabled={pending} type="button" onClick={() => void runAction(() => simulationApi.addVehicles(1))}>
              <span>Add vehicle</span><b>Lane 1</b><i>＋</i>
            </button>
            <button disabled={pending} type="button" onClick={() => void runAction(() => simulationApi.addVehicles(2))}>
              <span>Add vehicle</span><b>Lane 2</b><i>＋</i>
            </button>
          </div>

          <div className="control-group">
            <span className="control-label">Pedestrian demand</span>
            <button disabled={pending} type="button" className="ped-button" onClick={() => void runAction(() => simulationApi.addPedestrians())}>
              <span>Add pedestrian</span><b>Waiting zone</b><i>＋</i>
            </button>
          </div>

          <div className="control-group safety-controls">
            <span className="control-label">Safety testing</span>
            <button
              disabled={pending}
              type="button"
              className={state.sensor_available ? 'danger-button' : 'restore-button'}
              onClick={() => void runAction(() => simulationApi.setSensor(!state.sensor_available))}
            >
              <span>{state.sensor_available ? 'Simulate fault' : 'Restore sensor'}</span>
              <b>{state.sensor_available ? 'Disable snapshots' : 'Resume snapshots'}</b>
              <i>{state.sensor_available ? '!' : '↻'}</i>
            </button>
            <button disabled={pending} type="button" className="reset-button" onClick={() => void runAction(simulationApi.reset)}>
              Reset simulation
            </button>
          </div>
        </aside>
      </div>

      <section className="telemetry-section">
        <div className="telemetry-heading">
          <div>
            <span className="eyebrow">Backend source of truth</span>
            <h2>Live telemetry</h2>
          </div>
          <p>{state.transition_reason}</p>
        </div>
        <div className="metrics-grid">
          <Metric label="Vehicle light" value={state.vehicle_light} />
          <Metric label="Pedestrian signal" value={state.pedestrian_signal.replaceAll('_', ' ')} />
          <Metric label="Lane 1 queue" value={state.vehicle_queue_by_lane['1']} />
          <Metric label="Lane 2 queue" value={state.vehicle_queue_by_lane['2']} />
          <Metric label="Total queue" value={state.total_vehicle_queue} />
          <Metric label="Waiting zone" value={state.people_waiting_zone} />
          <Metric label="On crosswalk" value={state.people_on_crosswalk} />
          <Metric label="Clearance duration" value={`${state.pedestrian_clearance_duration}s`} note="distance ÷ walking speed" />
          <Metric label="Sensor status" value={state.sensor_status} />
          <Metric label="Sensor age" value={formatSeconds(state.sensor_age)} />
        </div>
      </section>

      <section className="configuration-section" aria-labelledby="configuration-title">
        <div className="configuration-heading">
          <div>
            <span className="eyebrow">Backend source of truth</span>
            <h2 id="configuration-title">Current simulation configuration</h2>
          </div>
          <p>Live values from the active TrafficConfig instance.</p>
        </div>
        <div className="configuration-table-wrap">
          <table className="configuration-table">
            <thead>
              <tr>
                <th scope="col">Setting</th>
                <th scope="col">Current value</th>
                <th scope="col">Meaning</th>
              </tr>
            </thead>
            <tbody>
              {CONFIGURATION_ROWS.map(([key, label, unit, meaning]) => (
                <tr key={key}>
                  <th scope="row"><code>{label}</code></th>
                  <td>{formatConfigValue(state.config[key], unit)}</td>
                  <td>{meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <footer>
        <span>Software simulation · no hardware control</span>
        <span>Portfolio prototype / not for public-road deployment</span>
      </footer>
    </main>
  )
}

export default App
