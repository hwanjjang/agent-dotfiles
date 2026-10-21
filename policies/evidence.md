# Evidence before completion

Scope: shared execution guidance for tasks that produce or change an artifact.

- Define completion in terms of the requested observable result.
- For source-heavy research or documents, use
  [grounded-citations](../skills/grounded-citations/SKILL.md) when a retrieved-source
  register and supporting quotes would make claims checkable. Incidental lookups
  need no ledger; citation checks do not establish the truth of a claim.
- Verify the actual artifact or behavior at the relevant revision. Compilation,
  successful copying, and worker self-reports establish only what they directly check.
- Reuse adequate evidence. Add a focused reproduction, test, or direct inspection
  where the change creates uncertainty; do not add checks merely to lengthen a list.
- Record what was checked, its result, and material limits. Missing evidence is
  an explicit gap, never an inferred pass.
- For an authorized instruction or skill installation/update, verify the intended
  source, discovery and applicable execution or hook behavior in each intended
  client. Copied files or matching links alone do not establish a working setup;
  report unavailable client checks explicitly.
- After integration or a changed assumption, recheck affected claims on the new
  artifact. Keep private raw evidence out of public source.

Adapted from pstack's `principle-prove-it-works` at revision
`ac4e25a0064cd600afdd605208bad72748cb019a`:
https://github.com/cursor/plugins/blob/ac4e25a0064cd600afdd605208bad72748cb019a/pstack/skills/principle-prove-it-works/SKILL.md

Local changes: scoped evidence to the request, allowed reuse, removed dependency
on an unbundled reporting skill, and clarified integrated-revision checks.
Client verification requirements are adapted from AK-authored account guidance,
supplied for public reuse under the repository [MIT license](../LICENSE).

## Upstream license

MIT License

Copyright (c) 2026 Lauren Tan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
