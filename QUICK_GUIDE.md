# GraphCodeBERT Quality Scoring - Quick Guide

**One-liner:** Measures code merit (modularity, reusability, style, structure) and contributes 10% to final score.

---

## Score Scale

```
90-100: EXCELLENT - Robust, well-organized code
80-89:  GOOD - Solid code with minor issues
70-79:  ACCEPTABLE - Functional but could improve
60-69:  NEEDS IMPROVEMENT - Significant issues
<60:    POOR - Major code quality concerns
```

---

## 4 Quality Metrics

| Metric          | Weight | Measures                                  |
| --------------- | ------ | ----------------------------------------- |
| **Modularity**  | 25%    | Code organization, separation of concerns |
| **Reusability** | 25%    | Parameterized functions, DRY, composition |
| **Style**       | 20%    | Indentation, formatting, conventions      |
| **Structure**   | 30%    | File organization, layering, architecture |

---

## Anti-Patterns Detected

**Penalize by -5 points each:**

General:

- Global state usage
- Many TODOs (>5)
- Long functions (>150 lines)
- Deep nesting (>6 levels)

Python: Bare except, bad comparisons  
JavaScript: var usage, == instead of ===  
React: Class state instead of hooks, array keys

---

## Best Practices Recognized

General: Comments, error handling, entry points  
Python: Context managers, decorators, comprehensions  
JavaScript: Arrow functions, async/await, const/let  
React: Hooks, performance optimization

---

## Final Score Formula

```
Final = 22% Stack + 26% Commits + 20% Code + 13% Depth + 9% Docs + 10% GraphCodeBERT_Quality
```

---

## Configuration

### Enable/Disable

```json
{
  "graphcodebert": {
    "quality_scoring": { "enabled": true }
  }
}
```

### Adjust Penalty

```json
{ "anti_pattern_penalty": 5 }
```

### Change Thresholds

```json
{
  "quality_thresholds": {
    "excellent": 80,
    "good": 70,
    "acceptable": 60,
    "needs_improvement": 50
  }
}
```

---

## Quick Test

```bash
python analyze_repo.py
# Enter: https://github.com/user/repo
# Enter: username
# Enter: JavaScript, React, Python
```

**Look for:** `GraphCodeBERT Quality Score: XX.X` in output

---

## Score Contribution Example

```
Code Quality Score: 75.3
Contribution: 75.3 × 0.10 = 7.53 points (out of 100)

Impact:
- Without quality: 67.0 / 100
- With good quality: 74.75 / 100
- Difference: +7.75 points
```

---

## Common Questions

**Q: How do I disable it?**  
A: Set `enabled: false` in scoring_policy.json

**Q: Does it slow things down?**  
A: No, <50ms overhead (negligible)

**Q: What if score is 0?**  
A: Check that code files are being sampled

**Q: Can I adjust weights?**  
A: Yes, all configurable in scoring_policy.json

**Q: Does it need external models?**  
A: No, pattern-based only

**Q: Is it deterministic?**  
A: Yes, 100% reproducible

---

## Files

- **Full Guide:** [GRAPHCODEBERT_GUIDE.md](GRAPHCODEBERT_GUIDE.md)
- **Scoring Logic:** [score_logic.md](score_logic.md#section-8)
- **Configuration:** [scoring_policy.json](scoring_policy.json)
- **Implementation:** [graphcodebert_quality_scorer.py](graphcodebert_quality_scorer.py)

---

## Summary

Semantic code analysis measuring 4 quality dimensions, detecting 8+ anti-patterns per language, recognizing 20+ best practices, and contributing 10% to final evaluation with minimal overhead.

See [GRAPHCODEBERT_GUIDE.md](GRAPHCODEBERT_GUIDE.md) for comprehensive documentation.
