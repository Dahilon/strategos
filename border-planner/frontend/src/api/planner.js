import service from './index'

export const getConfig = () => service.get('/api/planner/config')

export const runSimulation = (scenarioId, planId, mode = 'agents') =>
  service.post('/api/planner/simulate', { scenario_id: scenarioId, plan_id: planId, mode })

export const runMatrix = (scenarioId, numRuns = 2, mode = 'agents') =>
  service.post('/api/planner/run-matrix', { scenario_id: scenarioId, num_runs: numRuns, mode })

export const getResults = (scenarioId) =>
  service.get(`/api/planner/results/${scenarioId}`)
