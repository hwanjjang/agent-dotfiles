#!/usr/bin/env node
// Test the adopted super-board canvas with AK SDLC data; keep the original map untouched.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');

async function main() {
  if (process.argv.length !== 3 || process.argv[2] === '--help') {
    console.log('Usage: node docs/verification/verify-repository/scripts/check-workflow.cjs NEW_EVIDENCE_DIR\nRequires existing Playwright and Chromium. Optional VERIFY_BROWSER_CHANNEL or VERIFY_BROWSER_EXECUTABLE. Run from repository root.');
    if (process.argv[2] !== '--help') process.exitCode = 2;
    return;
  }
  const output = path.resolve(process.argv[2]);
  fs.mkdirSync(output);
  const files = ['docs/map/catalog.json', 'docs/map/index.html', 'docs/map/viewer.template.html', 'scripts/build_map.py', 'docs/map/workflow.json', 'docs/map/workflow.template.html', 'docs/map/workflow.html', 'scripts/build_workflow.py'];
  for (const name of fs.readdirSync('docs/map/vendor/super-board')) {
    const file = 'docs/map/vendor/super-board/' + name;
    if (fs.statSync(file).isFile()) files.push(file);
  }
  const hashes = () => Object.fromEntries(files.map(f => [f, crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')]));
  const report = {scenario: 'workflow-map', started: new Date().toISOString(), candidate: hashes(), checks: []};
  const check = name => report.checks.push(name);
  let browser, failure;
  try {
    for (const script of ['build_map.py', 'build_workflow.py']) {
      const result = spawnSync('python3', ['scripts/' + script, '--check'], {encoding: 'utf8'});
      fs.writeFileSync(path.join(output, script + '.txt'), result.stdout + result.stderr);
      assert.equal(result.status, 0, script + ' freshness');
    }
    const {chromium} = require('playwright');
    browser = await chromium.launch({headless: true, ...(process.env.VERIFY_BROWSER_EXECUTABLE ? {executablePath: process.env.VERIFY_BROWSER_EXECUTABLE} : process.env.VERIFY_BROWSER_CHANNEL ? {channel: process.env.VERIFY_BROWSER_CHANNEL} : {})});
    report.browser = browser.version();
    const page = await browser.newPage({viewport: {width: 1600, height: 1000}});
    page.setDefaultTimeout(10000);
    const errors = [], requests = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', req => {if (/^https?:/.test(req.url())) requests.push(req.url());});
    const url = pathToFileURL(path.resolve('docs/map/workflow.html')).href;
    const workflow = JSON.parse(fs.readFileSync('docs/map/workflow.json'));
    await page.goto(url);
    const ids = await page.locator('.sh[data-id]').evaluateAll(nodes => nodes.map(n => n.dataset.id));
    assert.deepEqual(ids, [...workflow.stages.map(s => 'stage:' + s.id), 'any:anytime']);
    const skillIds = await page.locator('.nd').evaluateAll(nodes => [...new Set(nodes.map(n => n.dataset.id))].sort());
    assert.deepEqual(skillIds, Object.keys(workflow.node_labels).sort());
    assert.equal(await page.locator('.ch[data-grp="intent"]').count(), 2, 'Interview alternatives must not become a sequential chain');
    assert.equal(await page.locator('.arr[data-grp="intent"]').count(), 0);
    await page.screenshot({path: path.join(output, 'workflow-desktop.png'), fullPage: true});
    check('All canonical route stages and mapped items; alternative branches');
    const close = async () => {await page.keyboard.press('Escape');assert.equal(await page.locator('#pop').evaluate(d => d.open), false);};
    await page.locator('.sh[data-id="any:anytime"]').click();
    assert.match(await page.locator('#pop').innerText(), /Not tied to one stage/);
    assert.doesNotMatch(await page.locator('#pop').innerText(), /undefined/);
    await close();
    await page.locator('.sh[data-id="stage:merge"]').click();
    assert.match(await page.locator('#pop').innerText(), /explicit merge authority/);
    await close();
    await page.locator('.ch[data-id="cat:correction-methods"]').click();
    await page.locator('#pop .xa').click();
    assert.match(await page.locator('#pop').innerText(), /self-verification.*PR review/);
    await close();
    await page.locator('.nd[data-id="grill-me"]').first().click();
    assert.match(await page.locator('#pop').innerText(), /consequential decision/);
    await page.locator('#pop .xa').click();
    assert.ok(await page.locator('#pop a[href="../../skills/grill-me/SKILL.md"]').isVisible());
    assert.match(await page.locator('#pop').innerText(), /Load skills\/grill-me\/SKILL.md/);
    assert.match(await page.locator('#pop').innerText(), /Use grill-me to clarify the export feature/);
    assert.match(await page.locator('#pop').innerText(), /AK adaptation:/);
    assert.ok(await page.locator('#pop a[href="../../skills/grill-me/provenance.json"]').isVisible());
    await close();
    for (const [id, expected] of [
      ['grill-with-docs', /preserve agreed domain terms/],
      ['architect', /design-only by default/],
      ['to-spec', /Do not publish tickets/],
      ['tdd', /pstack-derived TDD method only/]
    ]) {
      await page.locator('.nd[data-id="' + id + '"]').first().click();
      await page.locator('#pop .xa').click();
      assert.match(await page.locator('#pop').innerText(), expected);
      if (id === 'improvement-case') {
        const detail = await page.locator('#pop').innerText();
        assert.match(detail, /Only instruction cases are eligible/);
        assert.match(detail, /outcome cases require an actual failed tool/);
        assert.match(detail, /Caller triage is not automated diagnosis/);
        assert.match(detail, /not automatic sanitization/);
      }
      assert.ok(await page.locator('#pop a[href*="super-board/blob/"]').first().isVisible());
      if (id === 'grill-with-docs') {
        await page.locator('#pop').screenshot({path: path.join(output, 'workflow-rich-detail.png'), animations: 'disabled'});
        await page.locator('#pop a[href*="super-board/blob/"]').first().scrollIntoViewIfNeeded();
        await page.locator('#pop').screenshot({path: path.join(output, 'workflow-rich-sources.png'), animations: 'disabled'});
      }
      await close();
    }
    check('Enriched examples, flows, local adaptations and pinned reference/provenance links');
    for (const [id, expected] of [
      ['archify', /passing finalize receipt is automated evidence/],
      ['code-review-and-quality', /Provider selection, shared roles, fallback/],
      ['issue-writing', /Problem \/ Goal, Required changes and Completion criteria/],
      ['planning-and-task-breakdown', /Separate task blockers from PR base dependencies/],
      ['planning-with-files', /tool subprocess setting PLAN_ID does not bind/],
      ['screenshot-manual', /Render and inspect/],
      ['sdlc', /pre-merge means verified readiness without merge authority/i]
    ]) {
      await page.locator('.nd[data-id="' + id + '"]').first().click();
      await page.locator('#pop .xa').click();
      assert.match(await page.locator('#pop').innerText(), expected);
      if (id === 'improvement-case') {
        const detail = await page.locator('#pop').innerText();
        assert.match(detail, /Only instruction cases are eligible/);
        assert.match(detail, /outcome cases require an actual failed tool/);
        assert.match(detail, /Caller triage is not automated diagnosis/);
        assert.match(detail, /not automatic sanitization/);
      }
      assert.ok(await page.locator('#pop a[href="../../skills/' + id + '/provenance.json"]').isVisible());
      if (id === 'screenshot-manual' || id === 'sdlc') {
        await page.locator('#pop a[href="../../skills/' + id + '/provenance.json"]').scrollIntoViewIfNeeded();
        await page.locator('#pop').screenshot({path: path.join(output, id + '-detail.png'), animations: 'disabled'});
      }
      await close();
    }
    check('All seven remaining skill explanations, concrete examples and public provenance links');
    for (const [id, source, expected] of [
      ['policy-communication', 'policies/communication.md', /preserv.*meaning/i],
      ['policy-execution', 'policies/execution.md', /recorded baseline/],
      ['account-source', 'account/README.md', /preview or explicitly applied account change/i],
      ['planning-hooks', 'account/hooks/README.md', /native account activation remains a separate check/i],
      ['reviewer-runtime', 'skills/sdlc/references/host-adapters.md', /without duplicate reviewers/]
    ]) {
      await page.locator('.nd[data-id="' + id + '"]').first().click();
      await page.locator('#pop .xa').click();
      assert.match(await page.locator('#pop').innerText(), expected);
      if (id === 'improvement-case') {
        const detail = await page.locator('#pop').innerText();
        assert.match(detail, /Only instruction cases are eligible/);
        assert.match(detail, /outcome cases require an actual failed tool/);
        assert.match(detail, /Caller triage is not automated diagnosis/);
        assert.match(detail, /not automatic sanitization/);
      }
      assert.ok(await page.locator('#pop a[href="../../' + source + '"]').isVisible());
      if (id === 'planning-hooks') {
        await page.locator('#pop').screenshot({path: path.join(output, 'planning-hooks-detail.png'), animations: 'disabled'});
      }
      await close();
    }
    check('Account sources, policy triggers, reviewer continuity and delivery versus native activation boundaries');
    await page.locator('.ch[data-id="any:improvement"]').click();
    assert.match(await page.locator('#pop').innerText(), /1 Observe.*2 Reproduce.*3 Candidate.*4 Eval.*5 Review.*6 Deploy/);
    assert.match(await page.locator('#pop').innerText(), /not extra mandatory PR stages/);
    await close();
    for (const [id, expected, source] of [
      ['observation-store', /synthetic|Synthetic/, 'account/observation/README.md'],
      ['improvement-case', /caller triage.*are available/, 'docs/decisions/account-improvement-loop.md'],
      ['improvement-candidate', /manual|Manual/, 'docs/decisions/account-improvement-loop.md'],
      ['improvement-eval', /This tool launches no model or command/, 'docs/decisions/evaluation-accounting.md'],
      ['improvement-review', /It never merges or installs/, 'docs/decisions/promotion-recommendations.md'],
      ['improvement-deploy', /automatic eval-to-deployment integration remains planned/, 'docs/decisions/account-improvement-loop.md']
    ]) {
      await page.locator('.nd[data-id="' + id + '"]').first().click();
      await page.locator('#pop .xa').click();
      assert.match(await page.locator('#pop').innerText(), expected);
      if (id === 'improvement-case') {
        const detail = await page.locator('#pop').innerText();
        assert.match(detail, /Only instruction cases are eligible/);
        assert.match(detail, /outcome cases require an actual failed tool/);
        assert.match(detail, /Caller triage is not automated diagnosis/);
        assert.match(detail, /not automatic sanitization/);
      }
      if (id === 'improvement-eval') {
        const detail = await page.locator('#pop').innerText();
        assert.match(detail, /4\. Eval \/ offline/);
        assert.match(detail, /Offline accounting is available/);
        assert.match(detail, /live runner and independent holdout qualification remain planned/);
      }
      if (id === 'improvement-review') {
        const detail = await page.locator('#pop').innerText();
        assert.match(detail, /5\. Review \/ diagnostic/);
        assert.match(detail, /Diagnostic recommendations are available/);
        assert.match(detail, /live promotion gate and operational eligibility remain unavailable/);
      }
      assert.ok(await page.locator('#pop a[href="../../' + source + '"]').isVisible());
      await close();
    }
    await page.locator('#q').fill('eval');
    assert.equal(await page.locator('.nd[data-id="improvement-eval"]').evaluate(n => n.classList.contains('dim')), false);
    await page.locator('#q').fill('');
    check('Separate six-step improvement cycle, honest capability status, eval search and authoritative sources');
    await page.locator('#q').fill('glossary');
    assert.equal(await page.locator('.nd[data-id="domain-modeling"]').evaluate(n => n.classList.contains('dim')), false);
    assert.equal(await page.locator('.nd[data-id="tdd"]').first().evaluate(n => n.classList.contains('dim')), true);
    await page.locator('.nd[data-id="domain-modeling"]').click();
    assert.match(await page.locator('#pop').innerText(), /glossary/);
    await close();
    await page.locator('#q').fill('no-such-workflow-unique-probe');
    assert.equal(await page.locator('.nd:not(.dim)').count(), 0);
    await page.locator('#q').fill('');
    assert.equal(await page.locator('.nd.dim').count(), 0);
    check('Stage/category/skill dialogs, conditions, usage/source links and search dimming/recovery');
    let before = await page.locator('#map').getAttribute('viewBox');
    await page.locator('#cv-in').click();
    assert.notEqual(await page.locator('#map').getAttribute('viewBox'), before);
    await page.locator('#cv-out').click();
    await page.locator('#cv-fit').click();
    before = await page.locator('#map').getAttribute('viewBox');
    const canvas = await page.locator('#sc').boundingBox();
    await page.mouse.move(canvas.x + 30, canvas.y + 40);
    await page.mouse.down();await page.mouse.move(canvas.x + 130, canvas.y + 80, {steps: 10});await page.mouse.up();
    assert.notEqual(await page.locator('#map').getAttribute('viewBox'), before, 'Pan changes camera');
    await page.locator('#cv-reset').click();
    const node = page.locator('.nd[data-id="how"][data-grp="investigation"]');
    const box = await node.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();await page.mouse.move(box.x + box.width / 2 + 30, box.y + box.height / 2 + 30, {steps: 10});await page.mouse.up();
    assert.match(await node.getAttribute('transform'), /translate/);
    await page.reload();
    assert.match(await node.getAttribute('transform'), /translate/);
    await page.locator('#cv-reset').click();
    assert.equal(await node.getAttribute('transform'), null);
    await page.locator('#fsb').click();
    assert.ok(await page.evaluate(() => document.fullscreenElement?.id === 'hero' || document.getElementById('hero').classList.contains('exp')));
    await page.locator('#fsb').click();
    check('Original zoom, Fit, pan, drag persistence, Reset layout and full screen');
    await page.locator('#sbtt').click();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.screenshot({path: path.join(output, 'workflow-dark.png'), fullPage: true});
    await page.goto(url + '#skill-domain-modeling');
    await page.locator('#pop[open]').waitFor();
    assert.match(await page.locator('#pop').innerText(), /domain-modeling/);
    await page.screenshot({path: path.join(output, 'workflow-dialog.png')});
    await close();
    await page.setViewportSize({width: 390, height: 844});
    await page.locator('#cv-fit').click();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No mobile page overflow');
    await page.locator('#sbtt').click();
    await page.screenshot({path: path.join(output, 'workflow-mobile.png'), fullPage: true});
    await page.goto(url + '#skill-grill-me');
    await page.locator('#pop[open]').waitFor();
    const modal = await page.locator('#pop').boundingBox();
    assert.ok(modal.x >= 0 && modal.x + modal.width <= 391);
    await page.screenshot({path: path.join(output, 'workflow-mobile-dialog.png')});
    await close();
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, [], 'Offline viewer must not make network requests');
    assert.deepEqual(hashes(), report.candidate, 'Verification must not mutate either map');
    check('Theme, skill deep links, mobile canvas/dialog, offline operation and source integrity');
  } catch (error) {failure = error; report.error = error.message;}
  finally {
    if (browser) {
      try {await browser.close(); report.cleanup = browser.isConnected() ? 'failed' : 'passed';}
      catch (error) {failure ||= error; report.cleanup = 'failed'; report.cleanupError = error.message;}
    } else report.cleanup = 'no-browser-created';
    report.result = failure ? 'failed' : 'passed';
    report.finished = new Date().toISOString();
    fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify(report, null, 2) + '\n');
  }
  if (failure) throw failure;
  console.log('PASS: workflow-map; isolated browser closed, evidence retained.');
}
main().catch(error => {console.error(error.message); process.exitCode = 1;});
