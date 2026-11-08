# NEXT.md: what the data supports, and what to do next

Written 2026-11-08, after a review of the repo. Numbers come from `metrics.json` in run `20260905-0430-05_analyse-exp05_analyse` and from the logbook (sessions 20 to 25, kept on Dima's machine). `results/` is not on every machine, so the open checks below need Dima's copy.

## The one-line state

The headline question was never tested. It needs an agent that hides its hacks, and this agent disclosed every one (180 of 180). On a disclosing agent any reader finds the hack, so "the monitor beats the claim estimator" says nothing about the claim format. The next step is to find out whether concealment is even possible to test on this benchmark, before spending on anything else.

## 1. Claims ledger

### Keep: supported, with the scope stated

| claim | evidence | scope |
|---|---|---|
| Under prompt B, DeepSeek-V3.2 discloses its hacks. | Reasoning knows in 178 of 180. Report discloses the fact in 180 of 180: plainly in 141, as a "workaround" in 39. | One agent, one prompt. The 141 to 39 split carries about 10% judge noise (session 23). |
| A whole-transcript monitor detects these hacks. | AUROC 0.95 [0.92, 0.97]. Flags 184 of 184 hacks, 13% of honest successes, 27% of honest under conflict. | Its prompt says "answer cheating if unsure", so it favours recall. |
| A model-free feature nearly matches it. | "Report has a test_is_wrong claim": AUROC 0.85 [0.81, 0.89], 0.66 within mutated variants. | |
| Aggregating P(true) over all claims does not detect hacks. | Min over verifiable claims: 0.54, and 0.38 within mutated variants. Hackers' sentences are true. Honest agents under conflict make false "tests pass" claims. | |
| The estimator reads the code on correctness claims. | Spec channel 0.76 [0.67, 0.85], n = 117. 0.74 with served tests hidden. 0.54 with no transcript. | Covers 51 of 180 hacks. See W2 and W3. |
| The estimator does not need the reasoning trace. | 0.76 without it, 0.74 with it. Reasoning alone gives 0.72. | |
| The two-pass rule separates call-counter hacks. | One pass: 69 of 184 hacks pass the original tests. Two passes: 3 of 184. | Necessary, not sufficient: hardcoded tables on original tasks still pass. |
| Scores are stable across seeds. | Within-claim SD 0.023; 95.5% stay on the same side of 0.5. | 111 claims. |

### Weaken: the claim is stronger than the evidence

- **W1. "Well calibrated on test-pass claims."** Scores sit in two bins near 0.03 and 0.97. With two bins, ECE 0.02 measures accuracy at the extremes, not graded calibration. And in `full` mode the estimator sees the code and the assertions, so 93% accuracy is code tracing. Say: "right on 93% of 280 whole-suite test-pass claims, Brier 0.064, with near-binary scores."
- **W2. "The spec channel reaches 0.76 while the monitor reaches 0.95."** The two numbers are on different populations: 117 transcripts against 327. The monitor's AUROC on the same 117 is not reported. Until it is, do not compare them.
- **W3. The spec channel drops claims the estimator flagged as type mismatches.** The flag fires on 47% of hack correctness claims and 26% of honest ones (session 21). Filtering on a label-correlated flag can move the AUROC either way. Report the channel with flagged claims kept as well.
- **W4. "Benchmark recognition is ruled out" for the agent.** It cannot be ruled out. DeepSeek publishes no training cutoff for V3.2. The technical report ([arXiv 2512.02556](https://arxiv.org/abs/2512.02556), 2 December 2025) continues training from V3.1-Terminus and gives no data dates. Secondary sites disagree: unknown, July 2024 (likely copied from V3-0324) or December 2025. ImpossibleBench appeared in October 2025, inside that window. Say "the cutoff is not published; recognition is possible", and note that a recognising agent would more likely hack less or hide more, not disclose more.
- **W5. "Contamination inflates the monitor and the estimator identically."** Both use gpt-5.6-sol, so the direction is shared. "Identically" is an assumption nobody measured. Say "may inflate both".
- **W6. "The estimator is usually right where the checker disagrees."** This rests on reading the low-bin correctness claims. State how many were read.

### Drop: dead ends, do not pursue

- **The all-claims aggregate.** It is at chance for a known reason. Re-weighting claim types would rebuild the "test is wrong" feature, which needs no model.
- **Signature features.** `depends_on` is empty nowhere and carries nothing. Claim count differs by about one claim (8.1 against 7.5).
- **The omissions judge.** It agreed with itself on 69% of transcripts, on a quantity flat across labels (about 0.3 per transcript for every label). Code removed in this clean-up.
- **Best-of-N under optimisation pressure.** Its pre-registered gate was "claim-level beats the monitor by 0.05 with non-overlapping CIs". The gap is -0.19. Pressure against a detector also needs a setting where the detector has something to find. Code stub removed.
- **The "hack" against "workaround" framing split as a result.** It is within judge noise, and the estimator scores both alike (0.42 against 0.50, small n).
- **More agents under prompt B, including the o3 arm.** If they disclose too, it repeats the same uninformative comparison.
- **Three-seed averaging** (about 400 USD) and further dashboard or notebook polish. Neither changes a conclusion.

## 2. Open checks on the existing results (no model calls)

Checks 1, 2, 4 and 5 are now computed by stage 05. Run `make analyse` on the machine with `results/` (a new run id, same inputs) and read these keys of `metrics.json`.

| # | check | status | where |
|---|---|---|---|
| 1 | Monitor and type-mix AUROC on the 117 spec-channel transcripts (W2) | code added, needs a run | `detection.same_population_as_spec_channel` |
| 2 | Spec channel with flagged claims kept (W3) | code added, needs a run | `detection.spec_min_incl_flagged_full` |
| 3 | Test-pass accuracy and Brier with served tests hidden (W1) | already in the old run | `calibration.tests_pass_checker_no_test_diff` |
| 4 | Read the hacks that pass the original tests twice | list added, then read by hand | `to_read_by_hand.hacks_passing_original` |
| 5 | Original tasks whose tests violate their own spec | candidates added, then read by hand | `to_read_by_hand.test_is_wrong_on_original`, `n_original_tasks_with_likely_wrong_test` |
| 6 | DeepSeek-V3.2 training cutoff | done: not published, see W4 | |
| 7 | Active against waiting hours | partly done, see below | |

Check 7. The logbook total is 22.25 h before the write-up. Logged waiting: the grid 2 h 33 min (session 10), the stage 03 batch 27 min (session 21), Docker about 15 min (session 24). That is about 3.25 h, so active time is at most about 19 h. Azure deployment and quota waits were never logged. Only Dima can subtract those.

Cost. Stage 01 (DeepSeek-V3.2) was about 31 USD: 8.9M input and 15.2M output tokens at 0.58 and 1.68 USD per 1M, from third-party price trackers. The other stages were logged at gpt-5.6-sol list price, while a promotion at 4 and 20 USD (against 5 and 30) ran the whole time. So the logged 660 USD is an upper bound. Quote the Azure invoice instead.

## Status, 2026-11-08: no model credits left

Section 2 still runs, since stage 05 makes no model calls. Sections 3 and 4 are not funded. They stay here as the plan that would come next, with its stopping rules.

## 3. Next experiment: does the monitor need the disclosure?

**Crux.** The monitor sees the code and the report. On single-file LiveCodeBench tasks a hack is a hardcoded table or a call counter, which may be obvious from the code alone. If so, concealment in the report cannot hurt the monitor, and the claim format has no room to help on this benchmark at all.

**Method.** Re-run the stage 3c monitor, same model and published prompt, on the 327 transcripts with a report, in two contexts:

- (a) task prompt and final code only;
- (b) the `full` context with all agent prose removed, code blocks kept.

Cost: about 30 USD, from the 14.5 USD monitor run. It uses the existing transcripts and gpt-5.6-sol only. No DeepSeek calls. It needs a new context mode in `monitor_baseline.py` and a logbook entry before the run.

**Controls.** Same transcripts, labels and prompt. Report both labellings (with and without the 21 hidden hacks among honest successes). Report AUROC within mutated variants too, where the "test is wrong" feature falls to 0.66.

**Stopping rule.**

- If monitor AUROC in context (a) is 0.90 or more, hacks are visible in the code. Stop the claim-against-monitor comparison on LiveCodeBench. A concealing agent cannot change it. The only route left is a benchmark where hacks are hard to see in code, such as the SWE-bench split. That needs a tool-calling agent, so not DeepSeek on Azure.
- If it is 0.80 or less, the disclosure carried the monitor. Then run the concealment arm below.
- Between 0.80 and 0.90: compare with the spec channel on the same transcripts (check 1) before deciding.

**Strongest counter-evidence to keep in view.** The spec channel works by reading code against the docstring. That is the same evidence the monitor reads in context (a). If (a) stays high, the claim format adds a pointer to which sentence is false, but no detection power.

## 4. Concealment arm (only if the stopping rule says so)

**Method.** Same 60 tasks, mutated variants only, 2 samples each: 240 runs. Change only the report request, so that the agent has a reason to hide test-targeting. Example: tell it a reviewer will reject work that special-cases tests. Then run stages 02, 03 (`full` mode, correctness claims only), 03b and 03c.

**Cost.** Estimator and monitor: about 100 to 150 USD, scaled from session 21. Agent tokens: `[CHECK: DeepSeek-V3.2 Azure price per 1M tokens]`, still unknown since session 9.

**Controls.** The 3b judge must confirm concealment happened: the `silent` and `claims_correct` framings must rise from 0%. Report the hack rate change against prompt B (76 to 83%). Keep the two-pass ground truth.

**Stopping rule.**

- Fewer than 50 hacks with a concealing report: the elicitation failed. Report that and stop.
- Monitor AUROC on the concealed hacks still at or above the spec channel's upper CI: the claim format adds nothing here. Report and stop.
- Spec channel above the monitor with non-overlapping CIs: that is the first real evidence for the original hypothesis. Only then does optimisation pressure (best-of-N) become worth designing.

## 5. Write-up

Dima writes the write-up text. Use section 1 as the list of claims and their numbers. Lead with the realised threat from `PLAN.md`: the agent self-reports, so the headline comparison is uninformative. Then state what was learned anyway: the all-claims aggregate fails for a structural reason, and the estimator reads the code.
