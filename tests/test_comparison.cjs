const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {trackKey, latestRows, scoped, coverageRows, axis} = require('../site/compare.js');
const {selectedRows} = require('../site/compare.js');
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
test('context is opt-in and requires an explicit shared task-set group', () => {
  const published=JSON.parse(fs.readFileSync('data/references/gpqa-context-2026-11-12.json','utf8'))[0];
  const local=structuredClone(published);local.id='local-profile';local.kind='local';
  local.benchmark.revision='pinned-local-dataset';local.benchmark.task_set='local-one-pass';
  local.metric.unit='fraction';local.metric.value=0.75;
  const different=structuredClone(published);different.id='different-task-set';
  different.benchmark.task_set='189-question variant';different.protocol.config.comparison_group='different-group';
  const rows=[local,published,different];
  assert.deepEqual(selectedRows(rows,trackKey(local)).map(r=>r.id),['local-profile']);
  assert.deepEqual(selectedRows(rows,trackKey(local),true).map(r=>r.id),['local-profile',published.id]);
});
test('context never mixes metrics or uncurated benchmark versions', () => {
  const row=JSON.parse(fs.readFileSync('data/references/terminal21-context-2026-11-12.json','utf8'))[0];
  const older=structuredClone(row);older.id='older';older.benchmark.revision='2.0';delete older.protocol.config.comparison_group;
  const speed=structuredClone(row);speed.id='speed';speed.metric.name='runtime';speed.metric.unit='seconds';
  assert.deepEqual(selectedRows([row,older,speed],trackKey(row),true).map(r=>r.id),[row.id]);
  assert.deepEqual(selectedRows([row],'missing',true),[]);
});
test('coding history is opt-in and shares only the exact curated window', () => {
  const history=JSON.parse(fs.readFileSync('data/references/livecodebench-history-v6-2026-11-12.json','utf8'));
  const local=structuredClone(history[0]);local.id='synthetic-local-coding';local.kind='local';
  local.benchmark.task_set='local-window-hash';local.metric.unit='fraction';local.metric.value=0.5;
  assert.deepEqual(selectedRows([local,...history],trackKey(local)).map(r=>r.id),[local.id]);
  assert.equal(selectedRows([local,...history],trackKey(local),true).length,history.length+1);
  assert.deepEqual(scoped([local,...history],policy,'featured').map(r=>r.id),[local.id]);
  for (const row of history) assert.equal(require('../site/compare.js').providerFor(row,registry),row.model.provider);
});
