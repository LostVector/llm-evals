'use strict';
// Pure selection helpers shared by the page and offline checks.
const Comparison = (() => {
  const trackKey = r => JSON.stringify([r.benchmark.name, r.benchmark.revision, r.benchmark.split, r.benchmark.task_set, r.metric.name, r.metric.unit, r.metric.direction]);
  const canonical = value => value && typeof value === 'object' ? (Array.isArray(value) ? value.map(canonical) : Object.fromEntries(Object.keys(value).sort().map(key => [key,canonical(value[key])]))) : value;
  const recoveryIdentity = config => config?.response_recovery ? ['partial_regeneration', ...['selection','reasoning_budget_tokens','retained_responses','regenerated_responses','previously_missing_responses'].map(k => config.response_recovery[k] ?? null)] : null;
  const identity = r => JSON.stringify([trackKey(r), r.model.name, r.model.revision, r.model.quantization, r.model.artifact, r.model.artifact_sha256 || '', canonical(r.model.artifact_parts || null), r.protocol.harness, r.protocol.harness_revision, r.protocol.backend, r.protocol.backend_revision, r.protocol.hardware, r.kind, r.protocol.config?.kv_cache_precision || null, r.protocol.config?.observed_sampling_defaults?.min_p ?? null, recoveryIdentity(r.protocol.config), canonical(r.protocol.config?.generation || null), canonical(r.protocol.config?.reasoning || null)]);
  const contextGroup = r => typeof r.protocol.config === 'object' ? r.protocol.config.comparison_group : undefined;
  function selectedRows(records, key, includeContext = false) {
    const exact = records.filter(r => trackKey(r) === key);
    if (!includeContext || !exact.length) return exact;
    const groups = new Set(exact.map(contextGroup).filter(Boolean));
    const seed = exact[0];
    const unit = r => ['fraction','percent'].includes(r.metric.unit) ? 'percentage' : r.metric.unit;
    return records.filter(r => trackKey(r) === key || (groups.has(contextGroup(r)) &&
      r.benchmark.name === seed.benchmark.name && r.metric.name === seed.metric.name &&
      r.metric.direction === seed.metric.direction && unit(r) === unit(seed)));
  }
  function latestRows(records) {
    const dedup = new Map();
    for (const r of records) { const key = identity(r), old = dedup.get(key); if (!old || r.provenance.retrieved_at >= old.provenance.retrieved_at) dedup.set(key, r); }
    return [...dedup.values()];
  }
  function scoped(records, policy, mode) {
    if (mode === 'all') return records;
    const featured = new Set(policy.featured_observation_ids);
    return records.filter(r => r.kind === 'local' || featured.has(r.id));
  }
  const modelInfo = (r, registry) => registry.find(m => m.source_labels.includes(r.model.name));
  const providerFor = (r, registry) => modelInfo(r, registry)?.provider || r.model.provider || 'Other / unclassified';
  function coverageRows(records, registry, provider = 'all') {
    return registry.filter(m => provider === 'all' || m.provider === provider).map(m => ({...m, observations: records.filter(r => m.source_labels.includes(r.model.name))}));
  }
  function axis(records) {
    const values=records.map(r => r.metric.unit === 'fraction' ? r.metric.value * 100 : r.metric.value);
    const percent=records.every(r => ['fraction','percent'].includes(r.metric.unit));
    const min=percent ? 0 : Math.min(0,...values);
    const max=percent ? 100 : Math.max(0,...values,1);
    return {min,max,percent,span:max-min};
  }
  const suiteTracks = [
    {name: 'LiveCodeBench', label: 'Coding (131)', group: 'livecodebench-v6-feb-apr-2025-131', n: 131},
    {name: 'BFCL V4', label: 'Tool use (200)', group: 'bfcl-v4-multi-turn-base-local-fc-medium8k', n: 200},
    {name: 'SWE-bench Pro V2 HARD-51', label: 'Repository work (12)', group: 'hard51-maintenance-12-v1', n: 12},
    {name: 'GPQA Diamond', label: 'Science regression (198)', group: 'gpqa-diamond-198', n: 198},
    {name: 'HLE-Diamond', label: 'HLE text pilot (40)', group: 'hle-diamond-text-pilot-v1', n: 40},
  ];
  const suiteLineup = [
    ['Qwen3.8-Flash-Next', 'Halogen v2 native HGN'],
    ...['IQ3_S', 'IQ3_XXS', 'IQ2_XS', 'Q2_0'].map(quant => ['Qwen3.8-Flash-Next', `GSQ-RCO ${quant}`]),
    ['Inkling 2 Mini', 'Q8_0'],
    ['Qwen3.8 27B', 'UD-Q4_K_XL'],
    ['Qwen3.6 35B A3B', 'UD-Q4_K_XL'],
  ];
  function suiteRows(records) {
    const local = latestRows(records.filter(r => r.kind === 'local'));
    return suiteLineup.map(([model, quant]) => ({
      model, quant,
      cells: suiteTracks.map(track => local.filter(r =>
        r.model.name === model && r.model.quantization === quant &&
        r.benchmark.name === track.name && contextGroup(r) === track.group &&
        r.metric.n === track.n && r.measurements?.completed === track.n &&
        r.measurements?.total === track.n)),
    }));
  }
  return {trackKey, identity, contextGroup, selectedRows, latestRows, scoped, modelInfo, providerFor, coverageRows, axis, suiteTracks, suiteRows};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = Comparison;
