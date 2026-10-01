# injlab: prompt-injection defense lab

A small, dependency-free lab that answers one question with numbers:
**which defenses actually stop indirect prompt injection against a tool-using agent, and what do they cost?**

An agent can fetch web pages, send e-mail and run shell commands (all *simulated*, nothing real is executed).
Attack pages hide instructions in the content the agent reads. Each defense layer is measured for
attack success rate (ASR), benign utility (false positives) and latency.

## Quick start

```bash
pip install -e .
python -m injlab.eval                                   # offline mock model
python -m pytest                                        # sanity tests
python -m injlab.eval --backend lmstudio --model <name> --trials 5   # real local model
```

## Defense layers

| Layer | Idea | Weakness |
|---|---|---|
| `classifier` | detect injection patterns in external content | bypassed by obfuscation (base64), blocks legit text about injections |
| `spotlight` | mark untrusted text with a random delimiter | only helps if the model respects it (needs a real backend to measure) |
| `policy` | deterministic allowlist on tool calls | needs a well-designed policy; does not depend on the model |

## Results (mock model, deterministic)

| defense | attack success rate | benign utility |
|---|---|---|
| none | 100% | 100% |
| classifier | 25% | 50% |
| spotlight | 100% | 100% |
| policy | 0% | 100% |
| classifier+policy | 0% | 50% |
| all | 0% | 50% |

Takeaways: the classifier misses the base64 attack **and** blocks a harmless security article
(false positive). The deterministic policy stops every attack without hurting utility.
Spotlighting shows no effect here **by design**: the mock ignores delimiters, so this layer must be
evaluated on a real model.

## Limitations (please read)

- The mock model is a gullible stand-in. It validates the harness, not real-world robustness.
  Real numbers come from `--backend lmstudio` (nondeterministic: use several `--trials`).
- 4 attacks and 2 benign tasks is a starting point, not a benchmark.
- No defense here is complete. The design principle is *limit the damage when a layer fails*.

## Roadmap

- [ ] Run against 2-3 real local models and add their tables
- [ ] Replace the heuristic classifier with a fine-tuned small model (compare accuracy, size, latency)
- [ ] Real sandbox for `run_shell` (container, no network, no secrets)
- [ ] Human-approval layer for high-risk tools
- [ ] Import public datasets / AgentDojo tasks, add more attack families
- [ ] Plot ASR vs. utility trade-off
