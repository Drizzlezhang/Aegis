#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

const root = process.cwd();
const tier = process.env.DEVKIT_INIT_TIER || 'bootstrap';
const projectYamlPath = path.join(root, '.devkit', 'project.yaml');

const ignoreDirs = new Set([
  '.git',
  '.next',
  '.venv',
  'venv',
  'node_modules',
  '__pycache__',
  '.pytest_cache',
  '.mypy_cache',
  '.ruff_cache',
]);

function exists(file) {
  return fs.existsSync(path.join(root, file));
}

function sha256(file) {
  if (!file) return '';
  const fullPath = path.join(root, file);
  if (!fs.existsSync(fullPath) || !fs.statSync(fullPath).isFile()) return '';
  const digest = crypto.createHash('sha256').update(fs.readFileSync(fullPath)).digest('hex');
  return `sha256:${digest}`;
}

function walk(dir, visitor) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (ignoreDirs.has(entry.name)) continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(fullPath, visitor);
    } else {
      visitor(fullPath);
    }
  }
}

function findFirst(names) {
  let found = '';
  walk(root, (fullPath) => {
    if (found) return;
    if (names.includes(path.basename(fullPath))) {
      found = path.relative(root, fullPath);
    }
  });
  return found;
}

function getGitRemote() {
  try {
    return execSync('git config --get remote.origin.url', { cwd: root, encoding: 'utf8' }).trim();
  } catch (_) {
    return '';
  }
}

function countLocAndModules() {
  let loc = 0;
  const modules = new Set();
  const codeExts = new Set(['.py', '.ts', '.tsx', '.js', '.jsx', '.sh', '.css']);
  walk(root, (fullPath) => {
    const rel = path.relative(root, fullPath);
    const ext = path.extname(fullPath);
    if (!codeExts.has(ext)) return;
    if (rel.startsWith('.claude/') || rel.startsWith('.trae/')) return;
    try {
      loc += fs.readFileSync(fullPath, 'utf8').split('\n').length;
      const first = rel.split(path.sep)[0];
      if (first) modules.add(first);
    } catch (_) {}
  });
  return { loc, moduleCount: modules.size };
}

function detect() {
  const packageJson = findFirst(['package.json']);
  const lockfile = findFirst(['package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'bun.lockb']);
  const goMod = findFirst(['go.mod']);
  const pyproject = findFirst(['pyproject.toml']);
  const hasClaudeMd = exists('CLAUDE.md');
  const hasCursorRules = exists('.cursorrules') || exists('.cursor/rules');
  const hasWeb = packageJson && packageJson.startsWith('web/');
  const languages = [];
  const frameworks = [];

  if (pyproject) languages.push('python');
  if (exists('scripts') || findFirst(['.sh'])) languages.push('shell');
  if (packageJson) languages.push('typescript');
  if (pyproject) frameworks.push('fastapi');
  if (hasWeb) frameworks.push('nextjs');

  const { loc, moduleCount } = countLocAndModules();
  const remote = getGitRemote();
  const isInternal = /bytedance|byted/i.test(remote);
  const enabledPlugins = [];
  const claudeSettings = path.join(root, '.claude', 'settings.json');
  if (fs.existsSync(claudeSettings)) {
    try {
      const settings = JSON.parse(fs.readFileSync(claudeSettings, 'utf8'));
      for (const [name, enabled] of Object.entries(settings.enabledPlugins || {})) {
        if (enabled) enabledPlugins.push(name.split('@')[0]);
      }
    } catch (_) {}
  }

  return {
    packageJsonHash: sha256(packageJson),
    lockfileHash: sha256(lockfile),
    goModHash: sha256(goMod),
    pyprojectHash: sha256(pyproject),
    gitRemote: remote,
    languages,
    frameworks,
    loc,
    moduleCount,
    isInternal,
    hasClaudeMd,
    hasCursorRules,
    enabledPlugins,
  };
}

function readExisting() {
  if (!fs.existsSync(projectYamlPath)) return '';
  return fs.readFileSync(projectYamlPath, 'utf8');
}

function valueFor(existing, key) {
  const match = existing.match(new RegExp(`${key}:\\s*(.*)`));
  return match ? match[1].trim().replace(/^"|"$/g, '') : '';
}

function render(data, managedBy = 'devkit') {
  return `schema_version: 1
scanned_at: ${new Date().toISOString()}
ttl_seconds: 604800
fingerprint:
  package_json_hash: ${data.packageJsonHash ? data.packageJsonHash : '""'}
  lockfile_hash: ${data.lockfileHash ? data.lockfileHash : '""'}
  go_mod_hash: ${data.goModHash ? data.goModHash : '""'}
  pyproject_hash: ${data.pyprojectHash ? data.pyprojectHash : '""'}
  git_remote: ${data.gitRemote}
project:
  name: aegis-trader
  language: [${data.languages.join(', ')}]
  framework: [${data.frameworks.join(', ')}]
  scale: ${data.loc > 30000 ? 'L' : data.loc > 10000 ? 'M' : 'S'}
  loc: ${data.loc}
  module_count: ${data.moduleCount}
  is_monorepo: false
byted_signals:
  strong: ${data.isInternal ? '[git_remote]' : '[]'}
  weak: []
  is_internal: ${data.isInternal}
ai_configs:
  has_claude_md: ${data.hasClaudeMd}
  has_cursor_rules: ${data.hasCursorRules}
  installed_skills: [devkit-go, devkit-init]
  enabled_plugins: [${data.enabledPlugins.join(', ')}]
  mcp_servers: []
  managed_by: ${managedBy}
context_budget:
  xs: 3000
  s: 5000
  m: 30000
  l: 80000
`;
}

function audit(data) {
  const existing = readExisting();
  const checks = [
    ['package_json_hash', data.packageJsonHash],
    ['lockfile_hash', data.lockfileHash],
    ['go_mod_hash', data.goModHash],
    ['pyproject_hash', data.pyprojectHash],
    ['git_remote', data.gitRemote],
  ];
  const drift = checks.filter(([key, next]) => valueFor(existing, key) !== next);
  if (drift.length === 0) {
    console.log('devkit audit: OK - fingerprint unchanged');
    return;
  }
  console.log('devkit audit: DRIFT');
  for (const [key, next] of drift) {
    console.log(`- ${key}: ${valueFor(existing, key) || '(missing)'} -> ${next || '(empty)'}`);
  }
}

const data = detect();

if (tier === 'silent') {
  console.log(fs.existsSync(projectYamlPath) ? 'devkit silent: project.yaml present' : 'devkit silent: project.yaml missing');
} else if (tier === 'audit') {
  audit(data);
} else {
  fs.mkdirSync(path.dirname(projectYamlPath), { recursive: true });
  fs.writeFileSync(projectYamlPath, render(data, tier === 'adopt' ? 'user' : 'devkit'));
  console.log(`devkit detect: wrote ${path.relative(root, projectYamlPath)}`);
}
