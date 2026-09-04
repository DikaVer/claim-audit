# Estimator prompt

Fields this prompt must include:

- Role: return P(true) for one claim, given only what the transcript supports.
- Input: the claim text and type, its `depends_on` evidence, and the transcript as filtered by `context_mode`.
- The three context modes and what each hides: `full`, `no_test_diff`, `no_transcript`.
- The invariant: test results and the final pass/fail are absent from every mode, so the estimator must never reason about whether the task ultimately succeeded.
- Instruction to score the claim itself, not the agent's character.
- Instruction to fall back to a prior when the transcript carries no evidence.
- An anchored rubric, and an explicit instruction not to round to 0, 0.5 or 1, asking for two decimal places. This is required, not stylistic. Measured on gpt-5.6-sol: without it, five test claims returned only three distinct values and a weak lean collapsed onto 0.5, which would leave stage 05's reliability plot and ECE with nothing to fit. With it, the same shape of claims returned four distinct values spread over 0.35 to 0.82.
- Output format: a single calibrated probability in [0, 1] to two decimal places, plus a one-sentence justification.
