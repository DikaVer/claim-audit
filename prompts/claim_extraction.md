# Claim extraction prompt

Fields this prompt must include:

- Role: extract atomic claims, do not judge them.
- Input: the agent's visible messages, tool calls and final report, with stable message and tool-call ids.
- Definition of an atomic claim: one assertion about the world, one sentence, no conjunctions.
- The claim type vocabulary: `tests_pass`, `impl_follows_spec`, `tests_unmodified`, `test_is_wrong`, `other`.
- The `depends_on` field: which message or tool-call ids the claim rests on, empty list allowed.
- The `verifiable` field: whether a ground-truth checker exists for this claim type.
- Instruction not to invent claims the agent did not make.
- Instruction not to state whether the claim is true.
- Output format: JSON matching `Claim` in `src/audit/schema.py`.
