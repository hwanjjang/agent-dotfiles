# Resolve empirical uncertainty with a bounded experiment

Use when reading docs/source cannot decide a consequential feasibility question.
Skip building an experiment when existing evidence already resolves it. This
reference extends architect's existing empirical check; it adds no orchestrator,
production implementation mandate or routine approval checkpoint.

1. State the observable question and the evidence that would validate or falsify
   it. Break up independent questions only when useful; prioritize the one most
   likely to invalidate the approach. Reuse the user's stated constraints and
   authorization. Research available approaches before adding dependencies.
2. Bound time, resources and allowed effects. Build the smallest runnable CLI,
   page, endpoint or focused test that exposes the real behavior. Keep code/data
   in the task's ignored scratch directory; use synthetic inputs and existing
   credentials only within authority. Simplicity never justifies embedding
   secrets, touching production or skipping necessary isolation/cleanup.
3. Compare credible approaches with the same inputs and relevant measurements.
   Include an ordinary control and the failure/limit case that could change the
   design. Record commands, versions, inputs, results and surprises; a startup
   message or worker assertion alone does not validate feasibility. Use existing
   arena/host contracts only when independent variants are useful and authorized.
4. Return `VALIDATED`, `PARTIAL` or `INVALIDATED` with the exact conditions and
   evidence. A negative result can successfully answer the question; partial
   success must name remaining constraints. Explain how the finding changes the
   design, including any untested integration between individually tested parts.
5. Stop owned processes and dispose of owned scratch when its evidence is safely
   retained for the task. Preserve a concise result and reproduction reference
   in the design rationale. Prototype code is not automatically production-ready;
   downstream implementation and verification retain their existing owners.

Complete when the design can cite a supported answer or a bounded unresolved gap,
and affected downstream assumptions are updated.

Adapted from Hermes `spike`, itself attributed to GSD's `/gsd-spike` by
Lex Christopherson. [Provenance](../provenance.json) records the selected source;
the [MIT notices](../HERMES-LICENSE) travel with this reference.
