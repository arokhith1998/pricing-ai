<!--
Task id goes in the PR title, for example: "PK-104 feat: competitor price comparison".
Sections below are the review contract. Do not delete headings; write "none" if a
section genuinely does not apply.
-->

**Task:** PK-___ · **Agent:** ___ · **Branch:** agent/___/PK-___

### Summary

What changed, in one or two sentences.

### Why

What problem this solves, and for whom. Link the task's acceptance criteria.

### Implementation

Which files and components changed, and the shape of the approach. Note
anything touched outside the task's owned paths in `docs/agents/OWNERSHIP.md`,
and why the lead approved it.

### Tests

What was run and what it returned. Paste real output, not a summary.

- [ ] Python suite: `python -m pytest -q`
- [ ] Web (if `web/**` changed): `npm test`, `npx eslint`, `npx tsc --noEmit`, `npm run build`
- [ ] Migration up and down (if `neon/**` changed)
- [ ] New tests cover the behavior this PR adds

CI run: ___

### Risks

What could break. Be specific: name the behavior, not "minimal risk". Include
regression surface, security implications, and anything that needs watching
after deploy.

### Dependencies

Task ids and PRs this depends on, and anything that must be deployed or
migrated in a particular order.

---

**Pricekeel conventions checklist**

- [ ] Explainability preserved: every recommendation still carries a traceable why
- [ ] No CRM proxy presented as true margin
- [ ] No row-level customer data leaves the process
- [ ] Copy stays inside the evidence boundary, no fabricated traction
- [ ] No em dashes in generated content
