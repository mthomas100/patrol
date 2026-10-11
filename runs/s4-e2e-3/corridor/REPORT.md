# Patrol e2e report: corridor

**Result: PASS**

Command: `tests/e2e.sh --scene m2 --seed 1`; total wall time 219 s. Versions: {"python": "3.12.14", "mujoco": "3.15.0", "clef": "clef-flash-mlx (mlx-community/clef-flash-8bit @ dfa0993, upstream Cloudflare/clef-flash @ 17f0b0a)", "llm": "qwen38 via llama-swap :8090", "git": "116bd21"}.

Thresholds: {"min_recall": 0.5, "max_false_alarms": 1, "min_clef_share": 0.8, "max_llm_fraction": 0.1} (justified in DECISIONS.md, M3).

## Checks

- [x] offline tests pass
- [x] mission: corridor completed
- [x] mission: returned home
- [x] mission: recall >= 0.5
- [x] mission: false alarms <= 1
- [x] mission: every flag has a photo
- [x] mission: every flag has an LLM note
- [x] mission: Clef decided >= 80% of decisions (measured 98%)
- [x] LLM fraction reported and <= 10% (measured 5.6%)
- [x] decision latency reported (median 528.3 ms, p90 829.7 ms)
- [x] mission: spoken command heard and routed by Clef to revisit_last_flag ('Go back and look at that insulator again.' -> revisit_last_flag CLEF)
- [x] mission: revisit_last_flag executed by the drone
- [x] mission: every note read aloud (7/7 with a WAV)
- [x] voice: spoken command heard and routed by Clef to return_home ('Patrol, return home now.' -> return_home CLEF)
- [x] voice: return_home executed by the drone
- [x] voice: drone came home because the operator asked (operator asked)
- [x] corridor completed under 30% dropped decisions
- [x] returned home
- [x] dropped decisions shown as FALLBACK (43 ticks)
- [x] no flag decided by a FALLBACK answer

## Steps

| step | wall s | detail |
|---|---|---|
| offline tests (pytest) | 1.4 | `pytest.log` |
| mission: m2 seed 1, Clef + qwen38 notes read aloud, spoken revisit after the first flag | 122.2 | `mission/REPORT.md` |
| voice mission: spoken 'return home' at tick 60 | 35.0 | `voice/REPORT.md` |
| fault mission: 30% of decisions dropped | 60.2 | `faults/REPORT.md` |

## Preflight

```
{
 "clef_ok": true,
 "clef_wait_s": 0.0,
 "hold_status": "open: model calls pass; qwen38 (ready) loaded",
 "memory_free": "System-wide memory free percentage: 15%",
 "qwen38": "ok: OK",
 "qwen38_s": 0.3
}
```
