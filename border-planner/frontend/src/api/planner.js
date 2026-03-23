import service from './index'

export const getConfig = (worldId = null) =>
  worldId
    ? service.get('/api/planner/config', { params: { world_id: worldId } })
    : service.get('/api/planner/config')

export const runSimulation = (worldId, scenarioId, planId, mode = 'agents') =>
  service.post('/api/planner/simulate', {
    world_id: worldId,
    scenario_id: scenarioId,
    plan_id: planId,
    mode,
  })

export const runMatrix = (worldId, scenarioId, numRuns = 2, mode = 'agents') =>
  service.post('/api/planner/run-matrix', {
    world_id: worldId,
    scenario_id: scenarioId,
    num_runs: numRuns,
    mode,
  })

export const getResults = (scenarioId) =>
  service.get(`/api/planner/results/${scenarioId}`)
