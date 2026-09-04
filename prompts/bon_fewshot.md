# Best-of-N few-shot prompt (stretch)

Fields this prompt must include:

- Role: the agent template used inside the best-of-N and in-context RL loop.
- The task statement and the spec the agent is told to follow.
- A slot for few-shot examples: transcripts selected by the previous round's selection rule.
- The round number and the selection rule in force, `outcome_only` or `outcome_plus_estimator`.
- Instruction that the examples are prior attempts, not instructions to imitate verbatim.
- Output format: the same transcript shape as the stage 01 agent, so labels stay comparable.
