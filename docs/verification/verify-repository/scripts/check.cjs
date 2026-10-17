#!/usr/bin/env node
// Repository-only verifier; requires an already available Playwright package.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');

async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 1 || args[0] === '--help') {
    console.log('Usage: node docs/verification/verify-repository/scripts/check.cjs NEW_EVIDENCE_DIR\nRequires Playwright and Chromium; optional VERIFY_BROWSER_CHANNEL or VERIFY_BROWSER_EXECUTABLE. Run from the repository root.');
    if (args[0] !== '--help') process.exitCode = 2;
    return;
  }
  const root = process.cwd();
  const output = path.resolve(args[0]);
  fs.mkdirSync(output); // Refuse to overwrite a prior run.
  const report = {started: new Date().toISOString(), outcomes: [], cleanup: 'not-started'};
  let browser;
  let failure;
  let activeScenario = null;
  const files = ['docs/map/catalog.json', 'docs/map/index.html', 'docs/map/viewer.template.html', 'scripts/build_map.py'];
  report.verifier = crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex');
  const hashes = () => Object.fromEntries(files.map(p => [p, crypto.createHash('sha256').update(fs.readFileSync(path.join(root, p))).digest('hex')]));
  try {
    report.candidate = hashes();
    activeScenario = 'map-freshness';
    const cli = spawnSync('python3', ['scripts/build_map.py', '--check'], {cwd: root, encoding: 'utf8'});
    fs.writeFileSync(path.join(output, 'map-check.txt'), `${cli.stdout || ''}${cli.stderr || ''}`);
    report.outcomes.push({scenario: 'map-freshness', command: 'python3 scripts/build_map.py --check', exit: cli.status, result: cli.status === 0 ? 'passed' : 'failed'});
    assert.equal(cli.status, 0, 'Doctor failed: map source and generated viewer must agree.');
    activeScenario = 'browser-readiness';
    const {chromium} = require('playwright');
    report.playwright = require('playwright/package.json').version;
    const options = {headless: true};
    if (process.env.VERIFY_BROWSER_EXECUTABLE) options.executablePath = process.env.VERIFY_BROWSER_EXECUTABLE;
    else if (process.env.VERIFY_BROWSER_CHANNEL) options.channel = process.env.VERIFY_BROWSER_CHANNEL;
    browser = await chromium.launch(options);
    report.browser = browser.version();
    report.cleanup = 'pending';
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    page.setDefaultTimeout(10000);
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(root, 'docs/map/index.html')).href);
    await page.locator('#search').waitFor({state: 'visible'});
    const catalog = JSON.parse(fs.readFileSync('docs/map/catalog.json', 'utf8'));
    assert.equal(await page.locator('[data-id]').count(), catalog.entries.length, 'Initial catalog coverage');
    await page.screenshot({path: path.join(output, 'catalog.png'), fullPage: true});
    activeScenario = 'catalog-search';
    // Drive real search and selection, including the empty-result recovery path.
    await page.locator('#search').fill('no-such-capability-unique-probe');
    assert.equal(await page.locator('[data-id]').count(), 0);
    await page.locator('#search').fill('create-verification-skill');
    await page.locator('[data-id="create-verification-skill"]').click();
    assert.match(await page.locator('#detail .usage').innerText(), /Launch|launch/);
    await page.screenshot({path: path.join(output, 'verification-search.png'), fullPage: true});
    await page.locator('#search').fill('');
    assert.equal(await page.locator('[data-id]').count(), catalog.entries.length);
    report.outcomes.push({scenario: 'catalog-search', result: 'passed', evidence: 'verification-search.png'});
    activeScenario = 'catalog-source';
    for (const id of ['create-verification-skill', 'maintain-verification-skill', 'repository-verifier']) {
      await page.locator(`[data-id="${id}"]`).click();
      assert.ok((await page.locator('#detail .usage').innerText()).trim());
      const source = catalog.entries.find(e => e.id === id).source;
      const hrefs = await page.locator('#detail a').evaluateAll(nodes => nodes.map(n => n.getAttribute('href')));
      assert.ok(hrefs.includes('../../' + source), `Expected source link for ${id}`);
      assert.ok(fs.statSync(path.join(root, source)).isFile());
    }
    await page.screenshot({path: path.join(output, 'verification-detail.png'), fullPage: true});
    report.outcomes.push({scenario: 'catalog-source', result: 'passed', evidence: 'verification-detail.png'});
    activeScenario = 'integrity';
    assert.deepEqual(errors, [], 'Browser page errors');
    assert.deepEqual(hashes(), report.candidate, 'Verification changed maintained map source');
  } catch (error) {
    failure = error;
    report.error = error.message;
    if (activeScenario && !report.outcomes.some(item => item.scenario === activeScenario && item.result === 'failed')) {
      report.outcomes.push({scenario: activeScenario, result: 'failed', reason: error.message});
    }
  } finally {
    if (browser) {
      try { await browser.close(); report.cleanup = browser.isConnected() ? 'failed' : 'passed'; }
      catch (error) { report.cleanup = 'failed'; report.cleanupError = error.message; failure ||= error; }
    } else report.cleanup = 'no-browser-created';
    if (!failure) {
      try {
        for (const name of ['catalog.png', 'verification-search.png', 'verification-detail.png', 'map-check.txt']) {
          assert.ok(fs.statSync(path.join(output, name)).size > 0, `Missing retained evidence: ${name}`);
        }
        assert.notEqual(report.cleanup, 'failed', 'Browser cleanup failed');
      } catch (error) { failure = error; report.error = error.message; }
    }
    for (const scenario of ['map-freshness', 'catalog-search', 'catalog-source']) {
      if (!report.outcomes.some(item => item.scenario === scenario)) {
        report.outcomes.push({scenario, result: 'not-run', reason: 'Earlier prerequisite or scenario failed.'});
      }
    }
    report.finished = new Date().toISOString();
    report.result = failure ? 'failed' : 'passed';
    fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify(report, null, 2) + '\n');
  }
  assert.ok(fs.existsSync(path.join(output, 'result.json')), 'Proof must survive cleanup');
  if (failure) throw failure;
  console.log('PASS: map freshness, catalog search/recovery, usage/source links; isolated browser closed, evidence retained.');
}
main().catch(error => {console.error(error.message); process.exitCode = 1;});
