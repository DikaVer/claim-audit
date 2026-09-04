# Estimator prompt

Fields this prompt must include:

- Role: return P(true) for one claim, given only what the transcript supports.
- Input: the claim text and type, its `depends_on` evidence, and the transcript as filtered by `context_mode`.
- The three context modes and what each hides: `full`, `no_test_diff`, `no_transcript`.
- The invariant: test results and the final pass/fail are absent from every mode, so the estimator must never reason about whether the task ultimately succeeded.
- Instruction to score the claim itself, not the agent's character.
- Instruction to fall back to a prior when the transcript carries no evidence.
- Output format: a single calibrated probability in [0, 1], plus a one-sentence justification.
