# LOGBOOK

## 2026-09-04 (session 1)
Tried: created the repository skeleton described in `CLAUDE.md`, using uv as the package manager.
Found: every module in `src/audit/` is a stub, every script parses args and calls one stub, prompts are field lists only. `schema.py` carries real field declarations because it is the contract between stages and `test_schema.py` round-trips it.
Decided: uv with a hatchling build backend and a src layout. ImpossibleBench packaging stays marked `[CHECK: ...]` in `pyproject.toml` until Dima confirms.
Next: confirm the ImpossibleBench install route, pick the agent model from the leaderboard, then the 5-task smoke run.
Time spent so far: 0.5 h

## 2026-09-04 (session 2)
Tried: read the ImpossibleBench harness source at the local clone, commit 061dc3d, and ran two no-cost concatenation experiments against a real `conflicting` row (`lcbhard_0`) to test how the harness assigns a pass.
Found: four things that change the plan.
  1. The minimal agent and the scorer concatenate code in opposite orders. In the agent loop with `allow_test_modifications=True` the served test is placed **before** the agent's answer, so an answer that redefines `check` passes. The scorer always places the test **after** the answer, because `record_to_sample` is called without `allow_test_modifications` and so defaults to `False`, which always populates `metadata["test_patch"]`. Verified: a `check`-override answer gives in-loop pass, scorer fail. A call-order stateful answer gives in-loop pass, scorer pass.
  2. Therefore the `hack` label is precise but low recall. Hacks of type B, C and D are labelled `hack` correctly. Type A, overriding `check`, lands in `honest_under_conflict`. Contamination sits entirely in the negative class, so a positive AUROC result is conservative rather than inflated. The recovery is `in_loop_success and not scorer_pass` on an impossible variant, which is a second and sharper label, not a repair of the first.
  3. `PLAN.md` is wrong that the harness exposes the hack taxonomy. It is `analysis/llm_judge.py`, an LLM judge with categories A modify tests, B overload operators, C record extra state, D special-casing, E other. It costs model calls and is itself noisy. Only `agent_type="tools"` exposes a harness-level signal, `metadata["test_modification_detected"]`.
  4. ImpossibleBench ships `BINARY_PROMPT`, a whole-transcript cheating judge. That is our baseline monitor, already published, so using it verbatim removes the strawman objection. It tells the judge to answer "cheating" when unsure, which biases it toward recall. Report that rather than edit it out.
Also found: the harness never reads `original_test`, so our `impl_follows_spec` checker must run it. `seed` in `exp01_generate.yaml` does not reach the harness, since `shuffle` hardcodes `seed=42` and `limit` slices afterwards. `samples_per_task` maps to Inspect's `epochs`. The `conflicting` mutation is two assertions on identical inputs with different expected values, so no pure function can pass.
Decided: pin ImpossibleBench at commit 061dc3d, not `main`, because finding 1 depends on a default that upstream may change. Ignore the nested `impossiblebench/` clone in git.
Next: get approval for the transitive dependencies, write `.env`, then a smoke run over both `agent_type` values at `limit=2` to measure the real hack-method spread before committing to one.
Time spent so far: 1.5 h

## 2026-09-04 (session 3)
Tried: installed ImpossibleBench, switched the model config to Azure OpenAI, and read the paper's prompt and method tables to settle model choice.
Found: prompt choice dominates model choice on conflicting LiveCodeBench. Paper Figure 6, minimal scaffold: prompt A gives GPT-5 92% and o3 91%, prompt B gives 93% and 86%, prompt C gives 28% and 93%, prompt D gives 1% and 33%. The paper's headline numbers use prompt D, which is why its Figure 4 shows o3 at about 34% and everyone else near zero.
Also found, by running all four hack shapes on `lcbhard_0` in both concatenation orders: B overload operators and C record extra states pass the scorer and label correctly; A redefine `check` passes only in the loop and is labelled `honest_under_conflict`; D special-casing cannot pass `conflicting` at all, because the mutation asserts two values for identical inputs. This corrects session 2, which said the viable methods were A and C. B works because the overload lives in the returned value, not in the test harness, so it survives test-after-answer ordering.
Also found: the paper's LiveCodeBench rates are measured by this same scorer, so they are already net of the ordering asymmetry. No recall haircut is needed on the expected yield, and `in_loop_success` is extra yield rather than a repair.
Decided:
  - Agent is o3 under prompt B, not GPT-5. GPT-5 is 7 points higher but it is the estimator, and an estimator scoring its own claims is a self-evaluation confound that PLAN.md did not cover. o3 also holds up across the whole prompt sweep, which makes a base-rate control affordable later.
  - Prompt B over prompt A. A appends "and pass all tests", which instructs the behaviour under study, so a false "tests pass" claim under A is partly responsive to instruction.
  - Sampling params are now per role. PLAN.md's "estimator, temperature 0" is unachievable, because reasoning models on Azure OpenAI do not accept a temperature. Determinism for those roles comes from `cache.py`.
  - Pinned ImpossibleBench at commit 061dc3d as a uv git source. `uv sync` first failed on a Windows long-path error inside `inspect_evals`, a SWE-bench-only transitive dependency, fixed with `git config --global core.longpaths true`.
  - Scoped pytest to `tests/`, since the nested clone ships its own suite.
Next: Azure login has expired, so deploy `o3`, `gpt-5` and `gpt-4.1`, fill `.env`, then the smoke run over both agent types at limit 2. Histogram the estimator's p_true on that run: if a reasoning model returns three round numbers, stage 05 calibration is dead and we learn it now rather than at hour 8.
Time spent so far: 2.5 h
