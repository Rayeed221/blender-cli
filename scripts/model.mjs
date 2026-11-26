#!/usr/bin/env node
// Model pipeline: models/<name>/build.py -> build/<name>/{<name>.blend, preview.png, render.png, <name>.glb, report.json}
//
//   node scripts/model.mjs new <name>                 scaffold models/<name>/build.py from the template
//   node scripts/model.mjs build <name>... | --all    build, lint, preview and export
//   node scripts/model.mjs list                       list models
//
// build options:
//   --formats glb,fbx,obj,stl,usd   export formats (default glb)
//   --render                         also make a Cycles beauty render (render.png)
//   --samples N   --res WxH          render quality (default 64, 1280x1280)
//   --no-preview                     skip the 4-view workbench contact sheet
//   --fail-on error|warn|none        verify gate (default error)
//
// Every step is a blender-cli command; its JSON lands in report.json.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const MODELS = join(ROOT, 'models');
const BUILD = join(ROOT, 'build');
const CLI = join(ROOT, 'blender-cli');
const NAME_RE = /^[a-z0-9][a-z0-9-_]*$/;

function parse(argv) {
  const opts = { formats: ['glb'], render: false, samples: 64, res: '1280x1280', preview: true, failOn: 'error' };
  const pos = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--formats') opts.formats = argv[++i].split(',').map(s => s.trim()).filter(Boolean);
    else if (a === '--render') opts.render = true;
    else if (a === '--samples') opts.samples = Number(argv[++i]);
    else if (a === '--res') opts.res = argv[++i];
    else if (a === '--no-preview') opts.preview = false;
    else if (a === '--fail-on') opts.failOn = argv[++i];
    else if (a === '--all') opts.all = true;
    else if (a.startsWith('--')) die(`unknown option ${a}`);
    else pos.push(a);
  }
  return { cmd: pos[0], names: pos.slice(1), opts };
}

function die(msg) { console.error(`model: ${msg}`); process.exit(2); }

function listModels() {
  return readdirSync(MODELS, { withFileTypes: true })
    .filter(d => d.isDirectory() && !d.name.startsWith('_') && existsSync(join(MODELS, d.name, 'build.py')))
    .map(d => d.name).sort();
}

function cli(args) {
  const r = spawnSync(process.execPath, [CLI, ...args], {
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
    env: { ...process.env, MODELKIT_PATH: join(MODELS, '_lib') },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let out;
  try { out = JSON.parse(r.stdout); } catch { out = { ok: false, error: 'non-JSON output', stdout: r.stdout, stderr: r.stderr }; }
  return out;
}

function step(report, label, args, { required = true } = {}) {
  process.stderr.write(`  ${label.padEnd(10)} `);
  const t = Date.now();
  const out = cli(args);
  report.steps[label] = out;
  const ok = out.ok !== false;
  process.stderr.write(`${ok ? 'ok ' : 'FAIL'} ${((Date.now() - t) / 1000).toFixed(1)}s\n`);
  if (!ok) {
    process.stderr.write(`    ${out.error || 'failed'}${out.hint ? `\n    hint: ${out.hint}` : ''}\n`);
    if (out.trace) process.stderr.write(out.trace.split('\n').slice(-6).map(l => `    ${l}`).join('\n') + '\n');
    if (required) throw new Error(`${label} failed`);
  }
  return out;
}

function build(name, opts) {
  const src = join(MODELS, name, 'build.py');
  if (!existsSync(src)) die(`no such model: models/${name}/build.py`);
  const out = join(BUILD, name);
  mkdirSync(out, { recursive: true });
  const blend = join(out, `${name}.blend`);
  const report = { model: name, built_at: new Date().toISOString(), outputs: {}, steps: {} };
  console.error(`\n▸ ${name}`);
  try {
    const run = step(report, 'build', ['run', src, '--save', blend, '--no-backup']);
    report.model_facts = run.result;
    report.outputs.blend = blend;

    const ver = step(report, 'verify', ['verify', '--blend', blend, '--fail-on', opts.failOn]);
    report.verify_summary = ver.result?.summary ?? ver.summary;

    if (opts.preview) {
      const p = join(out, 'preview.png');
      step(report, 'preview', ['snapshot', '--blend', blend, '--out', p, '--views', 'front,right,top,persp',
        '--res', '512x512', '--shading', 'material'], { required: false });
      report.outputs.preview = p;
    }
    if (opts.render) {
      const p = join(out, 'render.png');
      step(report, 'render', ['render', '--blend', blend, '--out', p, '--engine', 'cycles', '--device', 'cpu',
        '--samples', String(opts.samples), '--res', opts.res], { required: false });
      report.outputs.render = p;
    }
    for (const fmt of opts.formats) {
      const p = join(out, `${name}.${fmt}`);
      step(report, `export:${fmt}`, ['export', p, '--blend', blend, '--selected'], { required: false });
      report.outputs[fmt] = p;
    }
    report.ok = Object.values(report.steps).every(s => s.ok !== false);
  } catch (e) {
    report.ok = false;
    report.error = e.message;
  }
  writeFileSync(join(out, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  const f = report.model_facts || {};
  console.error(`  ${report.ok ? '✔' : '✘'} ${f.vertices ?? '?'} verts, ${f.triangles ?? '?'} tris, ` +
    `${(f.dimensions_m || []).join(' × ')} m  →  build/${name}/`);
  return report;
}

function scaffold(name) {
  if (!name || !NAME_RE.test(name)) die('model names are lowercase, digits, - or _ (e.g. office-chair)');
  const dir = join(MODELS, name);
  if (existsSync(dir)) die(`models/${name} already exists`);
  mkdirSync(dir, { recursive: true });
  const tpl = readFileSync(join(MODELS, '_template', 'build.py'), 'utf8').replaceAll('__NAME__', name);
  writeFileSync(join(dir, 'build.py'), tpl);
  console.log(`created models/${name}/build.py\nbuild it with: npm run model -- build ${name}`);
}

const { cmd, names, opts } = parse(process.argv.slice(2));
if (cmd === 'new') scaffold(names[0]);
else if (cmd === 'list') console.log(listModels().join('\n'));
else if (cmd === 'build') {
  const targets = opts.all ? listModels() : names;
  if (!targets.length) die('build what? give model names or --all');
  const results = targets.map(n => build(n, opts));
  const failed = results.filter(r => !r.ok).map(r => r.model);
  console.log(JSON.stringify({ ok: failed.length === 0, built: results.map(r => r.model), failed }));
  process.exit(failed.length ? 1 : 0);
} else {
  console.error(readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 14).map(l => l.replace(/^\/\/ ?/, '')).join('\n'));
  process.exit(cmd ? 2 : 0);
}
