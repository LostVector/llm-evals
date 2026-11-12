'use strict';
// Pure selection helpers shared by the page and offline checks.
const Comparison = (() => {
  const trackKey = r => JSON.stringify([r.benchmark.name, r.benchmark.revision, r.benchmark.split, r.benchmark.task_set, r.metric.name, r.metric.unit, r.metric.direction]);
  const identity = r => JSON.stringify([trackKey(r), r.model.name, r.model.revision, r.model.quantization, r.model.artifact, r.model.artifact_sha256 || '', r.protocol.harness, r.protocol.harness_revision, r.kind]);
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
  return {trackKey, identity, contextGroup, selectedRows, latestRows, scoped, modelInfo, providerFor, coverageRows, axis};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = Comparison;
