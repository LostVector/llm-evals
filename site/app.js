'use strict';
const $ = id => document.getElementById(id);
const node = (tag, text, className) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; };
const trackKey = r => JSON.stringify([r.benchmark, r.metric.name, r.metric.unit, r.metric.direction]);
const identity = r => JSON.stringify([trackKey(r), r.model, r.protocol.harness, r.protocol.harness_revision, r.kind]);
const score = r => r.metric.unit === 'fraction' ? r.metric.value * 100 : r.metric.value;
const scoreLabel = r => `${Number(score(r).toFixed(2))}${['fraction', 'percent'].includes(r.metric.unit) ? '%' : ` ${r.metric.unit}`}`;
const safeURL = value => { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; } catch { return null; } };
let data, latest;
function option(value, text) { const el = node('option', text); el.value = value; return el; }
function selectBenchmark(name) { $('benchmark').value = name; tracks(); render(); }
function tracks() {
  const records = latest.filter(r => r.benchmark.name === $('benchmark').value);
  const groups = new Map(records.map(r => [trackKey(r), r]));
  $('track').replaceChildren(...[...groups].sort((a,b) => a[1].metric.name.localeCompare(b[1].metric.name)).map(([key,r]) => option(key, `${r.benchmark.revision} · ${r.benchmark.task_set} · ${r.metric.name} (${r.metric.unit})`)));
  if (!groups.size) $('track').append(option('', 'No numeric observations imported'));
  $('track').disabled = !groups.size;
}
function render() {
  const selected = $('benchmark').value;
  const catalog = data.catalog.find(c => c.name === selected);
  document.querySelectorAll('.coverage button').forEach(button => { const active = button.dataset.name === selected; button.classList.toggle('active',active); button.setAttribute('aria-pressed',String(active)); });
  const query = $('search').value.toLowerCase();
  const records = latest.filter(r => r.benchmark.name === selected && trackKey(r) === $('track').value && r.model.name.toLowerCase().includes(query) && ($('origin').value === 'all' || r.kind === $('origin').value));
  records.sort((a,b) => (a.metric.direction === 'lower' ? 1 : -1) * (score(a)-score(b)) || a.model.name.localeCompare(b.model.name));
  $('chart').replaceChildren(); $('rows').replaceChildren();
  $('chart-title').textContent = records.length ? `${selected} · ${records[0].metric.name}` : selected;
  $('count').textContent = `${records.length} observations`;
  $('empty').hidden = records.length > 0;
  $('empty').textContent = latest.some(r => r.benchmark.name === selected) ? 'No observations match these filters.' : `${catalog?.coverage || 'No observations recorded.'} Missing scores are not zero.`;
  const percent = records.every(r => ['percent','fraction'].includes(r.metric.unit));
  const max = percent ? 100 : Math.max(...records.map(score),1);
  for (const r of records) {
    const row = node('div',undefined,'bar-row'); row.setAttribute('role','listitem');
    const label = node('div',r.model.name,'bar-label');
    label.append(node('small',`${r.kind === 'local' ? r.model.quantization : 'Published reference'} · ${r.protocol.harness}`));
    const track = node('div',undefined,'bar-track'); const bar = node('div',undefined,`bar${r.kind === 'external' ? ' reference' : ''}`);
    bar.style.width = `${Math.max(0,Math.min(100,score(r)/max*100))}%`; track.append(bar); track.setAttribute('aria-hidden','true');
    row.append(label,track,node('span',scoreLabel(r),'bar-score')); $('chart').append(row);
    const tr = node('tr'); const modelCell = node('td',r.model.name); modelCell.append(node('small',r.model.quantization));
    const source = node('td'); const href = safeURL(r.provenance.location);
    if (href) { const a = node('a','Original source ↗'); a.href=href; a.target='_blank'; a.rel='noopener noreferrer'; source.append(a); }
    const details = node('details'); details.append(node('summary','Protocol & caveats'),node('pre',JSON.stringify(r,null,2))); source.append(details);
    const dateCell = node('td',r.provenance.retrieved_at); dateCell.append(node('small','Retrieval, not evaluation date'));
    tr.append(modelCell,node('td',scoreLabel(r)),node('td',r.protocol.harness),node('td',r.kind === 'local' ? 'Local measurement' : r.provenance.type),dateCell,source); $('rows').append(tr);
  }
}
async function start() {
  try {
    const embedded=$('evaluation-data');
    if (embedded) data=JSON.parse(embedded.textContent);
    else { const response=await fetch('data.json'); if (!response.ok) throw new Error(`HTTP ${response.status}`); data=await response.json(); }
    const dedup=new Map();
    for (const r of data.observations) { const key=identity(r), old=dedup.get(key); if (!old || r.provenance.retrieved_at >= old.provenance.retrieved_at) dedup.set(key,r); }
    latest=[...dedup.values()];
    const names=[...new Set([...data.catalog.map(c=>c.name),...latest.map(r=>r.benchmark.name)])];
    $('benchmark').replaceChildren(...names.map(name=>option(name,name)));
    const localCount=latest.filter(r=>r.kind==='local').length;
    $('status').textContent=`${names.length} benchmark families · ${latest.filter(r=>r.kind==='external').length} reference metrics · ${localCount} local measurements`;
    $('build-date').textContent=`Built ${data.built_at}`;
    for (const c of data.catalog) {
      const count=latest.filter(r=>r.benchmark.name===c.name).length;
      const button=node('button'); button.type='button'; button.dataset.name=c.name;
      button.append(node('span',c.area,'category'),node('span',c.name,'name'),node('span',count ? `${count} metric observations` : 'Numeric import pending','availability'),node('span',c.coverage,'coverage-note'));
      button.addEventListener('click',()=>selectBenchmark(c.name)); $('coverage').append(button);
    }
    $('benchmark').addEventListener('change',()=>{ tracks(); render(); });
    for (const id of ['track','origin']) $(id).addEventListener('change',render);
    $('search').addEventListener('input',render);
    selectBenchmark(names[0]);
  } catch(error) { $('status').textContent='Could not load evaluation data. Please reload or check the data.json artifact.'; $('empty').hidden=false; $('empty').textContent=error.message; }
}
start();
