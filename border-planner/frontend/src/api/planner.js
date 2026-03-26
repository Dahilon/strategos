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

export const recommendContainment = (worldId, simulation) =>
  service.post('/api/planner/recommend', {
    world_id: worldId,
    simulation,
  })

export const getExplainability = (worldId, simResultsByPlan, scoresByPlan, recommendedPlanId = null) =>
  service.post('/api/planner/explain', {
    world_id: worldId,
    sim_results_by_plan: simResultsByPlan,
    scores_by_plan: scoresByPlan,
    recommended_plan_id: recommendedPlanId,
  })
