'use strict';
const $ = id => document.getElementById(id);
const node = (tag, text, className) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; };
const {trackKey, latestRows, scoped, providerFor, coverageRows, axis} = Comparison;
const score = r => r.metric.unit === 'fraction' ? r.metric.value * 100 : r.metric.value;
const scoreLabel = r => `${Number(score(r).toFixed(2))}${['fraction', 'percent'].includes(r.metric.unit) ? '%' : ` ${r.metric.unit}`}`;
const safeURL = value => { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; } catch { return null; } };
function scoreElement(record, className) {
  const href = safeURL(record.provenance.location);
  const el = node(href ? 'a' : 'span', scoreLabel(record), className);
  if (href) {
    el.href = href;
    el.target = '_blank';
    el.rel = 'noopener noreferrer';
    el.title = `Original source for ${record.model.name}`;
    el.setAttribute('aria-label', `${record.model.name}: ${scoreLabel(record)} — open original source`);
  }
  return el;
}
let data, latest;
const visibleRows = () => scoped(latest, data.reference_policy, $('reference-view').value);
function option(value, text) { const el = node('option', text); el.value = value; return el; }
function selectBenchmark(name) { $('benchmark').value = name; tracks(); render(); }
function tracks() {
  const records = visibleRows().filter(r => r.benchmark.name === $('benchmark').value);
  const groups = new Map(records.map(r => [trackKey(r), r]));
  $('track').replaceChildren(...[...groups].sort((a,b) => a[1].metric.name.localeCompare(b[1].metric.name)).map(([key,r]) => option(key, `${r.benchmark.revision} · ${r.benchmark.task_set} · ${r.metric.name} (${r.metric.unit})`)));
  const primary=data.reference_policy.primary_metric;
  if ($('benchmark').value===primary.benchmark) {
    const preferred=[...groups].find(([,r])=>r.benchmark.revision===primary.preferred_reference.revision && r.benchmark.task_set===primary.preferred_reference.task_set && r.metric.name===primary.preferred_reference.metric);
    if(preferred) $('track').value=preferred[0];
  }
  if (!groups.size) $('track').append(option('', 'No numeric observations imported'));
  $('track').disabled = !groups.size;
}
function render() {
  const selected = $('benchmark').value;
  const catalog = data.catalog.find(c => c.name === selected);
  document.querySelectorAll('.coverage button').forEach(button => { const active = button.dataset.name === selected; button.classList.toggle('active',active); button.setAttribute('aria-pressed',String(active)); });
  const query = $('search').value.toLowerCase();
  const trackRows = visibleRows().filter(r => r.benchmark.name === selected && trackKey(r) === $('track').value);
  const records = trackRows.filter(r => ($('provider').value === 'all' || providerFor(r,data.model_registry) === $('provider').value) && r.model.name.toLowerCase().includes(query) && ($('origin').value === 'all' || r.kind === $('origin').value));
  records.sort((a,b) => (a.metric.direction === 'lower' ? 1 : -1) * (score(a)-score(b)) || a.model.name.localeCompare(b.model.name));
  $('chart').replaceChildren(); $('rows').replaceChildren();
  $('chart-title').textContent = records.length ? `${selected} · ${records[0].metric.name}` : selected;
  $('count').textContent = `${records.length} observations`;
  $('empty').hidden = records.length > 0;
  $('empty').textContent = visibleRows().some(r => r.benchmark.name === selected) ? 'No observations match these filters.' : `${catalog?.coverage || 'No observations recorded.'} ${latest.some(r => r.benchmark.name === selected) ? 'Historical observations are available under All references & history.' : ''} Missing scores are not zero.`;
  const {min,max,span,percent}=axis(trackRows);
  $('axis-label').textContent = records.length ? `Axis: ${min} to ${max}${percent ? '%' : ` ${records[0].metric.unit} (relative scale)`}` : '';
  const coverage=coverageRows(trackRows,data.model_registry,$('provider').value);
  $('model-coverage-summary').textContent=`Model coverage on this track: ${coverage.filter(m=>m.observations.length).length} / ${coverage.length} tracked families have a verified score`;
  $('model-coverage').replaceChildren(...coverage.map(m=>{
    const tr=node('tr');
    const scores=node('td');
    if (!m.observations.length) scores.textContent='No verified score on this track';
    m.observations.forEach((r,i)=>{ if(i) scores.append(document.createTextNode(' · ')); scores.append(scoreElement(r)); });
    tr.append(node('td',m.provider),node('td',m.name),scores);
    return tr;
  }));
  for (const r of records) {
    const row = node('div',undefined,'bar-row'); row.setAttribute('role','listitem');
    const label = node('div',r.model.name,'bar-label');
    label.append(node('small',`${providerFor(r,data.model_registry)} · ${r.kind === 'local' ? r.model.quantization : 'Published reference'} · ${r.protocol.harness}`));
    const track = node('div',undefined,'bar-track'); const bar = node('div',undefined,`bar${r.kind === 'external' ? ' reference' : ''}`);
    bar.style.width = `${Math.abs(score(r))/span*100}%`; bar.style.left = `${((score(r)<0 ? score(r) : 0)-min)/span*100}%`; track.append(bar); if(min<0) { const zero=node('i',undefined,'zero-line');zero.style.left=`${-min/span*100}%`;track.append(zero); } track.setAttribute('aria-hidden','true');
    row.append(label,track,scoreElement(r,'bar-score')); $('chart').append(row);
    const tr = node('tr'); const modelCell = node('td',r.model.name); modelCell.append(node('small',r.model.quantization));
    const source = node('td'); const href = safeURL(r.provenance.location);
    if (href) { const a = node('a','Original source ↗'); a.href=href; a.target='_blank'; a.rel='noopener noreferrer'; source.append(a); }
    const details = node('details'); details.append(node('summary','Protocol & caveats'),node('pre',JSON.stringify(r,null,2))); source.append(details);
    const dateCell = node('td',r.provenance.retrieved_at); dateCell.append(node('small','Retrieval, not evaluation date'));
    const scoreCell=node('td'); scoreCell.append(scoreElement(r));
    tr.append(modelCell,scoreCell,node('td',r.protocol.harness),node('td',r.kind === 'local' ? 'Local measurement' : r.provenance.type),dateCell,source); $('rows').append(tr);
  }
}
async function start() {
  try {
    const embedded=$('evaluation-data');
    if (embedded) data=JSON.parse(embedded.textContent);
    else { const response=await fetch('data.json'); if (!response.ok) throw new Error(`HTTP ${response.status}`); data=await response.json(); }
    latest=latestRows(data.observations);
    const names=[...new Set([...data.catalog.map(c=>c.name),...latest.map(r=>r.benchmark.name)])];
    $('benchmark').replaceChildren(...names.map(name=>option(name,name)));
    $('provider').append(...[...new Set(data.model_registry.map(m=>m.provider))].sort().map(p=>option(p,p)));
    const localCount=latest.filter(r=>r.kind==='local').length;
    $('status').textContent=`${data.model_registry.length} tracked model families · ${data.reference_policy.required_providers.length} required provider groups · ${latest.filter(r=>r.kind==='external').length} reference metrics · ${localCount} local measurements`;
    $('build-date').textContent=`Built ${data.built_at}`;
    const reviewed=new Date(`${data.reference_policy.reviewed_at}T00:00:00Z`);
    const age=Math.max(0,Math.floor((Date.now()-reviewed.getTime())/86400000));
    const overdue=age>data.reference_policy.review_interval_days;
    $('cohort-review').textContent=`Reference cohort reviewed ${data.reference_policy.reviewed_at} · ${overdue ? 'Review overdue; do not assume current frontier coverage.' : 'Selected verified sources; model and source coverage is incomplete.'}`;
    $('cohort-review').classList.toggle('overdue',overdue);
    function coverage() {
      $('coverage').replaceChildren();
      for (const c of data.catalog) {
        const count=visibleRows().filter(r=>r.benchmark.name===c.name).length;
        const historical=latest.filter(r=>r.benchmark.name===c.name).length;
        const button=node('button'); button.type='button'; button.dataset.name=c.name;
        button.append(node('span',c.area,'category'),node('span',c.name,'name'),node('span',count ? `${count} visible metric observations` : historical ? 'Historical coverage only in this view' : 'Numeric import pending','availability'),node('span',c.coverage,'coverage-note'));
        button.addEventListener('click',()=>selectBenchmark(c.name)); $('coverage').append(button);
      }
    }
    coverage();
    $('reference-view').addEventListener('change',()=>{coverage();tracks();render();});
    $('benchmark').addEventListener('change',()=>{ tracks(); render(); });
    for (const id of ['track','origin','provider']) $(id).addEventListener('change',render);
    $('search').addEventListener('input',render);
    selectBenchmark(names.includes(data.reference_policy.primary_metric.benchmark) ? data.reference_policy.primary_metric.benchmark : names[0]);
  } catch(error) { $('status').textContent='Could not load evaluation data. Please reload or check the data.json artifact.'; $('empty').hidden=false; $('empty').textContent=error.message; }
}
start();
