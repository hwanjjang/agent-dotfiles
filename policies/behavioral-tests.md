# Test observable behavior

Scope: writing, changing, or reviewing automated tests.

- Exercise the interface used by callers, users, or external systems.
- Derive expected results from the requirement or an independent worked example,
  not the implementation under test.
- A test should fail when the promised behavior breaks and survive an internal
  refactor that preserves that behavior.
- External effects, failure types, and idempotency can be observable contracts.
  An internal helper's call sequence usually is not.
- Prefer concrete cases that expose a plausible defect. Avoid tests that only
  compare copied constants, prompt wording, or fixtures to themselves.
- Match testing effort to the change; a reversible prose edit normally needs
  inspection and link checks rather than a new test suite.

Adapted from pstack's `principle-test-behavior-not-implementation` at revision
`ac4e25a0064cd600afdd605208bad72748cb019a`:
https://github.com/cursor/plugins/blob/ac4e25a0064cd600afdd605208bad72748cb019a/pstack/skills/principle-test-behavior-not-implementation/SKILL.md

Local changes: condensed the method into a portable policy and added proportional
verification for documentation changes. The examples and full source remain upstream.

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
