---
name: writing-for-agents
description: Write or revise agent-consumed skills, policies and instruction entry points with precise triggers, focused steps and observable completion criteria.
---

# Write instructions agents can use

Use for maintaining instruction sources, not for ordinary product prose or for
adding process to every development task. Input: intended behavior, target agent
environment and existing authoritative instructions. Output: a focused document
with reachable references and reviewed behavior. Follow the host's skill-creator
contract when creating or changing a skill.

1. **Locate the owner.** Find where the rule already lives. Edit that authority
   and link to it instead of creating another copy. Preserve the user's task,
   authorization boundaries and existing entry-point conventions.
2. **Make the trigger discriminating.** A description or context pointer should
   say what the document does and when to read it. Cover distinct cases without
   repeating synonyms. Narrow wording that would trigger on unrelated work.
3. **Keep the main path readable.** Put shared steps in the entry point. Move
   substantial branch-specific references beside the skill and link them at the
   decision that needs them. Keep a rule's definition and exceptions together.
   Avoid forcing readers to load every supporting file for a small task.
4. **Define observable completion.** State the input, expected result and evidence
   that distinguishes done from not done. Match procedural detail to actual risk;
   avoid fixed counts or approval checkpoints that do not resolve a real decision.
5. **Prune and verify.** Remove duplicate, stale and generic instructions that
   do not change behavior. Refer to discoverable project commands rather than
   maintaining a competing command list. Check links, dependencies and relevant
   invocation metadata; exercise representative scenarios when behavior changes.

Discovery metadata, implicit invocation, hooks and tool APIs differ by client.
Check the target's current documentation and actual discovery; do not treat one
client's frontmatter semantics as a universal standard. Structural validation
does not establish that an agent selects or follows a skill.

For this repository, AGENTS.md remains the maintenance authority and CLAUDE.md its
small importing entry point. Other projects retain their own layout. This skill
does not authorize installing or changing account instructions.

Source and adaptations: [provenance](provenance.json). License: [MIT](LICENSE).
