![turkish-casefold-evasion](assets/banner.png)

# turkish-casefold-evasion

**`"İGNORE".lower()` is not `"ignore"`. Your keyword filter just let the injection through.**

Most hand-rolled prompt-injection filters do the same thing: `text.lower()` and then check for
trigger substrings like `"ignore all previous instructions"`. That is silently broken for Turkish.
Python's locale-independent `str.lower()` maps the Turkish dotted capital **İ** (U+0130) to
`i` + a **combining dot above** (U+0307) — not plain `i`:

```python
>>> "İGNORE ALL PREVIOUS INSTRUCTIONS".lower()
'i̇gnore all previous instructions'          # note the extra dot on the first i
>>> "ignore all previous instructions" in "İGNORE ALL PREVIOUS INSTRUCTIONS".lower()
False                                          # the filter misses it
```

The dotless **ı** (U+0131) and Unicode confusables (Cyrillic/Greek/fullwidth lookalikes) do the
same. To a multilingual LLM the text still reads as the instruction; to your filter it's invisible.

This repo **measures the bypass**, ships the **evasion dataset**, and gives the **one-line fix**.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![tests](https://img.shields.io/badge/tests-6%20passing-brightgreen)](tests/)
[![deps](https://img.shields.io/badge/dependencies-zero-red)](tcfeval/core.py)
[![🤗 dataset](https://img.shields.io/badge/🤗%20dataset-turkish--casefold--evasion-yellow)](https://huggingface.co/datasets/fevziegeyurtsevenler/turkish-casefold-evasion)

---

## 📉 The finding

Applying three Turkish-flavoured evasions to 15 common trigger phrases, against a typical
`lower()`-and-substring filter:

| Evasion | Bypass rate vs naive filter ↑(attacker) | Caught after the fix |
|---------|:---------------------------------------:|:--------------------:|
| dotless-i (`i→ı`, `I→İ`) | **91%** | 100% |
| confusable (Cyrillic/Greek lookalikes) | **100%** | 100% |
| combining-mark (`i` + U+0307) | **91%** | 100% |
| **overall** | **94.6%** | **100%** |

**94.6% of case-folded/confusable evasions slipped past the naive filter; the one-line fix caught
all of them.** Reproduce with `python build_study.py` (writes `study.json` + the dataset).

> Note: this targets **naive keyword/regex** filters. Modern **ML guards** (e.g. ProtectAI's
> deberta) are far more robust to these tricks — see the companion study
> [guard-blindspots-tr](https://github.com/fevziegeyurtsevenler/guard-blindspots-tr). If you rely
> on a keyword/regex layer at all, though, this bypass applies to you.

## 🩹 The fix (one function)

Normalize **before** matching — NFKC, fold confusables, strip combining marks, then `casefold()`:

```python
from tcfeval.core import normalize

def hardened_filter(text, triggers):
    norm = normalize(text)
    return any(normalize(t) in norm for t in triggers)

normalize("İGNORE")   # -> 'ignore'
normalize("ıgnore")   # -> 'ignore'
```

`tcfeval.core.normalize()` is dependency-free and safe to drop in front of any existing
keyword/regex prompt-injection check.

## 📦 Dataset

`data/evasion_dataset.jsonl` — every (trigger, evasion) pair with whether it bypassed the naive
filter and was caught by the hardened one. Also on the Hub:

```python
from datasets import load_dataset
ds = load_dataset("fevziegeyurtsevenler/turkish-casefold-evasion")
```

Fields: `trigger`, `evasion`, `evaded_text`, `original_caught_by_naive`,
`evaded_caught_by_naive`, `evaded_caught_by_hardened`, `bypassed_naive_filter`.

## ⚖️ Honesty & limits

- The 94.6% is against a **naive `lower()`+substring** filter — a common but weak design. It is not
  a claim about ML-based guards, which mostly resist these tricks.
- `normalize()` reduces confusable/casefold evasion; it is **not** a full prompt-injection defense.
  Combine it with semantic detection, sandboxing, and egress control.
- The confusable map is a high-value subset, not the entire Unicode confusables table.

## 🔗 Related AltaySec work

- 🛡️ [guard-blindspots-tr](https://github.com/fevziegeyurtsevenler/guard-blindspots-tr) — how ML guards handle the same Turkish tricks
- 🏁 [guardrail-arena](https://github.com/fevziegeyurtsevenler/guardrail-arena) — two-axis multilingual guardrail benchmark
- 🕵️ [uncloak](https://github.com/fevziegeyurtsevenler/uncloak) — hidden/invisible-Unicode prompt-injection scanner
- 🌐 [AltaySec](https://altaysec.com.tr) · [Açık Kaynak Lab](https://altaysec.com.tr/acik-kaynak)

## Citation

```bibtex
@misc{yurtsevenler2026turkishcasefold,
  title  = {turkish-casefold-evasion: Bypassing Naive Prompt-Injection Filters with Turkish Case-Folding},
  author = {Yurtsevenler, Fevzi Ege},
  year   = {2026}, publisher = {AltaySec},
  howpublished = {\url{https://github.com/fevziegeyurtsevenler/turkish-casefold-evasion}}
}
```

Apache-2.0 · built by **[AltaySec](https://altaysec.com.tr)** — Türkçe-first AI/LLM security.
