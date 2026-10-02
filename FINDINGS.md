# Findings

## TL;DR

On a real, fairly capable local model (**Gemma 3 12B QAT**), an undefended agent was hijacked in **80%** of attack runs.
Only the **deterministic tool policy** reduced that to **0%**, in every combination, at no measured utility cost.
The **classifier** removed most of the attacks (80% -> 20%) but left exactly the ones it has no pattern for.
**Spotlighting** helped a little (80% -> 56%) but the effect is within noise.
Defense overhead is negligible next to model inference time.

> Soft layers (classifier, spotlighting) reduce the odds. Only a layer that does not depend on the model (the tool policy) gives a guarantee.

## Setup

| | |
|---|---|
| model | `google-gemma-3-12b-it-qat-small-fix` (LM Studio, quantization-aware 4-bit) |
| run | `python -m injlab.eval --backend lmstudio --model <name> --trials 5` |
| attacks | 5 (direct override, HTML comment, e-mail exfiltration, base64, markdown comment) x 5 trials = **25 attack runs per row** |
| benign tasks | 2 x 5 trials = **10 runs per row** |
| temperature | 0.0 (default of this version) |

## Results

Counts are back-calculated from the printed percentages (56% is only possible as 14/25, which also confirms 25 attack runs per row).

| defense | attack success rate | benign utility | avg ms/run |
|---|---|---|---|
| none | 80% (20/25) | 50% (5/10) | 14329 |
| classifier | 20% (5/25) | 50% (5/10) | 13646 |
| spotlight | 56% (14/25) | 70% (7/10) | 13405 |
| policy | **0%** (0/25) | 50% (5/10) | 14917 |
| classifier+policy | **0%** (0/25) | 50% (5/10) | 12910 |
| all | **0%** (0/25) | 50% (5/10) | 13674 |

## What the numbers say

**1. The undefended model is very easy to hijack (80%).**
Gemma 12B followed injected instructions in 4 of 5 attack families. For comparison, `qwen2.5-coder-7b-instruct` fell for 2 of 5 in an earlier run.
A hypothesis worth testing with more models: *better instruction following can mean more hijackable*, because the model is also better at obeying injected text.
Two models are not enough to claim this.

**2. The tool policy is the only layer with a guarantee (0/25, p < 0.001 vs. undefended).**
It does not read the content and does not care whether the model was fooled; it checks the *action*.
Its utility equals the undefended baseline, so no cost is measurable here. `classifier+policy` and `all` add nothing on top of `policy` in these numbers:
the soft layers only matter when the policy is incomplete or too permissive.

**3. The classifier works exactly as far as its patterns reach (80% -> 20%, p < 0.001).**
It blocks the three attacks that match a pattern (direct override, HTML comment, e-mail exfiltration) and cannot see base64 or markdown comments.
Because the classifier does not touch those two pages, the remaining 5/25 must come from them, so on this model one of the two evasion attacks works in every trial.
(Assuming temperature 0 is effectively deterministic, the undefended 20/25 then implies the three pattern-detectable attacks succeed 5/5 each.)
This is also why the classifier looked *perfect* (0%) on the Qwen model: that model happened to ignore the two attacks the classifier misses.
**A defense's measured effectiveness depends on which attacks the model falls for, so it has to be measured per model.**

**4. Spotlighting gives a partial, noisy reduction (80% -> 56%, p ~ 0.13).**
Not statistically distinguishable from no defense at this sample size, and the runs are not independent samples (same 5 pages, temperature 0).
Notably it is the only row with a count that is not a multiple of 5, because the delimiter is random per run, which changes the prompt even at temperature 0.
On Qwen it looked much stronger; on Gemma it is weak. Spotlighting is **model-dependent**, and should be treated as hardening, never as a boundary.

**5. Latency overhead is negligible.**
All rows are within roughly 13-15 s per run. The defenses themselves cost microseconds; the small differences come from the number of model steps
(for example, a removed page means no hijack steps), not from the defense code.

## What these results do not show

- **The false-positive cost of the classifier is not measurable yet.** Benign utility is already only 50% *without any defense*, so the classifier
  (50%) cannot look worse. The mock model showed the real effect (100% -> 50%: it blocks a harmless security article).
  The baseline is low most likely because the check requires an exact snippet in the e-mail and a real model paraphrases it.
- **Spotlight's 70% utility is not a real gain.** A defense that only adds delimiters should not improve utility; 7/10 vs. 5/10 is noise (p ~ 0.65).
- **The policy's 0% is partly by construction.** The attacks target shell execution and external e-mail, which are exactly what the policy forbids.
  It has not been tested against attacks that abuse *allowed* actions, and in a real product the shell allowlist would not be empty.
- **5 attacks and 2 benign tasks, one model, one quantization.** Percentages are precise-looking but rest on very few distinct cases.
- Tool results are fed back to the model as user messages, which probably makes it more obedient to injected text than a native tool-calling API.

## Practical takeaways

1. **Start with least privilege on tools.** A deterministic policy (allowlisted commands, recipient domains, no secrets in outgoing text) is the cheapest layer that actually holds.
2. **Use the classifier as a cheap pre-filter, not a boundary.** It catches the lazy attacks and misses anything new; expect false positives on security content.
3. **Treat spotlighting as optional hardening.** Measure it on the exact model you deploy.
4. **Measure per model.** The same layer looked perfect on one model and leaky on another.
5. **Assume every soft layer will fail** and design so that a failure does limited damage.

## Next experiments (highest value first)

1. Print per-attack and per-benign-task breakdowns (v0.2 does for attacks) to confirm which evasion attack worked on Gemma.
2. Fix the benign-utility check (semantic instead of exact snippet) so the classifier's false-positive cost becomes visible.
3. Re-run with `--temperature 0.7 --trials 5` to get real variance, ideally on 3+ models of different size.
4. Save full traces to verify that spotlighting changes behavior and not just the number of tool calls.
5. Add attacks that abuse allowed actions, to find the policy's real weak spot.
