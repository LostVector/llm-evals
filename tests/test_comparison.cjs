const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {trackKey, latestRows, scoped, coverageRows, axis} = require('../site/compare.js');
const records = JSON.parse(fs.readFileSync('data/references/current-frontier-2026-11-11.json','utf8'));
const policy = JSON.parse(fs.readFileSync('data/reference_policy.json','utf8'));
const registry = JSON.parse(fs.readFileSync('data/model_registry.json','utf8'));

test('default cohort excludes historical records regardless of retrieval recency', () => {
  const archived=structuredClone(records[0]);archived.id='historical';archived.provenance.retrieved_at='2099-01-01';
  const local=structuredClone(records[0]);local.id='local';local.kind='local';
  assert.equal(scoped([archived],policy,'featured').length,0);
  assert.equal(scoped([archived],policy,'all').length,1);
  assert.equal(scoped([local],policy,'featured').length,1);
});
test('source-specific HLE protocols remain distinct tracks', () => {
  const hle=records.filter(r=>r.benchmark.name==='HLE-Diamond');
  assert.ok(new Set(hle.map(trackKey)).size>=2);
});
test('registry shows missing scores instead of zeros for each selected track', () => {
  const index=records.filter(r=>r.benchmark.name==='AA Intelligence Index');
  const rows=coverageRows(index,registry,'Moonshot / Kimi');
  assert.equal(rows.find(m=>m.id==='kimi-k3').observations.length,0);
  assert.ok(rows.find(m=>m.id==='kimi-k3.1-pro').observations.length>0);
});
test('signed index scores have a visible negative range', () => {
  const signed=records.filter(r=>r.benchmark.name==='AA-Omniscience');
  const range=axis(signed);
  assert.equal(range.min,-12);
  assert.ok(range.max>0);
  assert.equal(range.percent,false);
  assert.deepEqual(axis(records.filter(r=>r.benchmark.name==='Terminal-Bench')), {min:0,max:100,percent:true,span:100});
});
test('latest selection is independent of JSON key order', () => {
  const older=structuredClone(records[0]);
  const newer=structuredClone(records[0]);newer.id='new';newer.provenance.retrieved_at='2026-11-12';
  newer.model=Object.fromEntries(Object.entries(newer.model).reverse());
  assert.deepEqual(latestRows([older,newer]).map(r=>r.id),['new']);
});
