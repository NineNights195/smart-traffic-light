import type { SimulationState } from './types'

const API_ROOT = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const simulationApi = {
  state: (signal?: AbortSignal) =>
    request<SimulationState>('/state', { signal }),
  addVehicles: (lane: 1 | 2, count = 1) =>
    request<SimulationState>('/simulation/vehicles', {
      method: 'POST',
      body: JSON.stringify({ lane, count }),
    }),
  addPedestrians: (count = 1) =>
    request<SimulationState>('/simulation/pedestrians', {
      method: 'POST',
      body: JSON.stringify({ zone: 'waiting_left', count }),
    }),
  setSensor: (available: boolean) =>
    request<SimulationState>('/simulation/sensor', {
      method: 'POST',
      body: JSON.stringify({ available }),
    }),
  reset: () =>
    request<SimulationState>('/simulation/reset', { method: 'POST' }),
}

