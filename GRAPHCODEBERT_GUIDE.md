# GraphCodeBERT Quality Scoring - Comprehensive Guide

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** February 2026

---

## Table of Contents

1. [Overview](#overview)
2. [What It Does](#what-it-does)
3. [How It Works](#how-it-works)
4. [Configuration](#configuration)
5. [Anti-Patterns & Best Practices](#anti-patterns--best-practices)
6. [Integration](#integration)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

---

## Overview

GraphCodeBERT Quality Scoring is a semantic code analysis layer that measures code merit through four quality dimensions:

- **Modularity** (25%) - Code organization and separation of concerns
- **Reusability** (25%) - Parameterized functions, DRY principle, composition patterns
- **Style Consistency** (20%) - Indentation, formatting, language conventions
- **Structure Management** (30%) - File organization, layering, clear architecture

**Contribution:** 10% of final evaluation score  
**Performance:** <50ms per repository  
**Model Required:** None (heuristic/pattern-based)

---

## What It Does

### Input

- Up to 10 representative code files from repository
- List of claimed technology stacks

### Processing

1. Analyzes 4 quality metrics (0-100 each)
2. Detects 8+ anti-patterns per language (-5 points each)
3. Recognizes 20+ best practices per language
4. Assesses overall code health

### Output

```json
{
  "overall_score": 74.3,
  "modularity": 72.0,
  "reusability": 68.5,
  "style_consistency": 81.2,
  "structure": 79.1,
  "anti_patterns": ["var usage", "deep nesting"],
  "best_practices": ["error handling", "async/await"],
  "code_health": "Good"
}
```

---

## How It Works

### Step 1: Code Sampling

- Samples up to 10 representative files
- Prioritizes entry points (app.js, main.py, index.html)
- Prioritizes organized structure (components/, services/, etc.)
- Prefers files with 50-200 lines (meaningful, not trivial)

### Step 2: Metric Scoring

**Modularity (25% weight)**

- Base: 50 points
- +20 for good function/class ratio
- +15 for proper imports/modules
- +10 for clear folder separation
- +10 for consistent naming
- Max: 100

**Reusability (25% weight)**

- Base: 50 points
- +25 for parameterized functions
- +15 for DRY principle (>90% unique lines)
- +10 for functional patterns (map, filter, pipe)
- +15 for abstractions (interfaces, base classes)
- Max: 100

**Style Consistency (20% weight)**

- Base: 50 points
- +20 for indentation consistency (80%+)
- +15 for good spacing/formatting
- +5-10 for language-specific conventions
- Max: 100

**Structure Management (30% weight)**

- Base: 50 points
- +25 for reasonable file sizes (30-200 lines)
- +10 for varied file purposes
- +5 for clear directory hierarchy
- Max: 100

### Step 3: Penalty & Bonus

- Each anti-pattern: -5 points (cumulative)
- Best practices: informational (no bonus)

### Step 4: Health Assessment

```
≥80 + no anti-patterns  → Excellent
≥70 + ≤1 anti-pattern   → Good
≥60                     → Acceptable
≥50                     → Needs Improvement
<50                     → Poor
```

---

## Configuration

### In scoring_policy.json

**Enable/Disable:**

```json
{
  "graphcodebert": {
    "quality_scoring": {
      "enabled": true // Set false to disable
    }
  }
}
```

**Metric Weights:**

```json
{
  "metrics": {
    "modularity": { "weight": 0.25 },
    "reusability": { "weight": 0.25 },
    "style_consistency": { "weight": 0.2 },
    "structure": { "weight": 0.3 }
  }
}
```

**Tuning Parameters:**

```json
{
  "max_files": 10, // Code files to sample
  "anti_pattern_penalty": 5, // Points per issue
  "quality_thresholds": {
    "excellent": 80,
    "good": 70,
    "acceptable": 60,
    "needs_improvement": 50
  }
}
```

**Final Score Weights:**

```json
{
  "final_score_weights": {
    "stack_accuracy": 0.22,
    "commit_quality": 0.26,
    "code_quality": 0.2,
    "project_depth": 0.13,
    "documentation": 0.09,
    "graphcodebert_quality": 0.1
  }
}
```

---

## Anti-Patterns & Best Practices

### Anti-Patterns Detected

**General (All Languages)**

- Global state usage (`global`, `window.*`, `$GLOBALS`)
- Many unresolved TODOs/FIXMEs (>5)
- Very long functions (>150 lines)
- Deep nesting (>6 levels)

**Python-Specific**

- Bare `except: pass`
- Improper boolean comparison (`== True`, `== False`, `== None`)

**JavaScript-Specific**

- Using `var` instead of `const`/`let`
- Using `==` instead of `===`

**React-Specific**

- Using class state instead of hooks
- Using array index as React key

### Best Practices Recognized

**All Languages**

- Good documentation/comments
- Error handling implemented
- Proper entry point handling

**Python**

- Context managers used (`with` statements)
- Decorators used (`@decorator`)
- Pythonic patterns (list comprehensions)

**JavaScript/TypeScript**

- Arrow functions used
- Modern async/await patterns
- Modern variable declarations (`const`/`let`)

**React**

- React Hooks used (useState, useEffect)
- Performance optimization (React.memo, useMemo)

---

## Integration

### In analyze_repo.py (lines 1225-1251)

```python
# Sample code files
code_samples = sample_code_files(local_path, max_files=10)

# Score quality
from graphcodebert_quality_scorer import score_code_quality
quality_result = score_code_quality(code_samples, claimed_stacks, policy)

# Add to scores
scores["graphcodebert_quality"] = quality_result.get("overall_score", 0)

# Compute final with new weight
final_score = compute_final_score(scores, policy["final_score_weights"])
```

### Output in evaluation_result.json

```json
{
  "graphcodebert": {
    "quality_analysis": {
      "overall_score": 74.3,
      "modularity": 72.0,
      "reusability": 68.5,
      "style_consistency": 81.2,
      "structure": 79.1,
      "anti_patterns": ["var usage"],
      "best_practices": ["error handling", "async/await"],
      "code_health": "Good"
    }
  }
}
```

---

## Examples

### Example 1: Good Quality Code

```
Repository: well-organized JavaScript/React project

Analysis:
- Modularity: 75 (good function organization)
- Reusability: 72 (mostly parameterized functions)
- Style Consistency: 82 (consistent indentation)
- Structure: 80 (clear layering)

Overall Score = (75×0.25) + (72×0.25) + (82×0.20) + (80×0.30) = 77.5

Anti-patterns detected: 0
Best practices: 4 (error handling, async/await, hooks, modern syntax)

Code Health: Good

Final Score Contribution: 77.5 × 0.10 = 7.75 points
```

### Example 2: Poor Quality Code

```
Repository: minimally organized code

Analysis:
- Modularity: 45 (poor organization)
- Reusability: 38 (hardcoded values)
- Style Consistency: 35 (inconsistent)
- Structure: 48 (large files)

Overall Score = (45×0.25) + (38×0.25) + (35×0.20) + (48×0.30) = 42.0

Anti-patterns detected: 4
- var usage
- == comparisons
- Very long functions
- Deep nesting

Penalty: 4 × 5 = -20 points

Final Quality Score: 42.0 - 20 = 22.0

Code Health: Poor

Final Score Contribution: 22.0 × 0.10 = 2.2 points
```

### Example 3: Average Code

```
Repository: typical project

Scores: Modularity 68, Reusability 65, Style 72, Structure 70

Overall Score = (68×0.25) + (65×0.25) + (72×0.20) + (70×0.30) = 68.8

Anti-patterns detected: 1 (minor issue)
Penalty: -5

Final Quality Score: 68.8 - 5 = 63.8

Code Health: Acceptable

Final Score Contribution: 63.8 × 0.10 = 6.38 points
```

---

## Troubleshooting

### Quality Score Always 0

**Cause:** Feature disabled  
**Solution:** Check `graphcodebert.quality_scoring.enabled` = true in policy

**Cause:** No code files sampled  
**Solution:** Verify repo has source files with supported extensions

**Cause:** Import error  
**Solution:** Ensure `graphcodebert_quality_scorer.py` exists in project root

### Quality Score Same for All Repos

**Cause:** Not analyzing actual code  
**Solution:** Add debug prints to verify sampling works

**Cause:** Threshold too narrow  
**Solution:** Verify metric weights and calculations

### Quality Score Seems Wrong

**Cause:** Anti-patterns not detected  
**Solution:** Review code vs. pattern regex in scorer

**Cause:** Weights misconfigured  
**Solution:** Verify all weights in final_score_weights sum to 1.0

**Cause:** Penalty too harsh  
**Solution:** Adjust `anti_pattern_penalty` (default 5)

### Debug Specific Repository

```python
from graphcodebert_quality_scorer import GraphCodeBERTScorer
from analyze_repo import sample_code_files
import json

# Load policy
with open('scoring_policy.json') as f:
    policy = json.load(f)

# Sample code
samples = sample_code_files("./temp_repo/project", max_files=10)
print(f"Sampled {len(samples)} files")

# Score
scorer = GraphCodeBERTScorer(policy)
result = scorer.score_samples(samples, ["JavaScript", "React"])
print(json.dumps(result, indent=2))
```

---

## Performance Characteristics

| Operation               | Time      |
| ----------------------- | --------- |
| Sample files            | <10ms     |
| Modularity analysis     | <5ms      |
| Reusability analysis    | <5ms      |
| Style analysis          | <5ms      |
| Structure analysis      | <5ms      |
| Anti-pattern detection  | <10ms     |
| Best practice detection | <10ms     |
| **Total**               | **<50ms** |

**Overhead:** <0.2% of total evaluation time

---

## Files Reference

- **Implementation:** [graphcodebert_quality_scorer.py](graphcodebert_quality_scorer.py)
- **Integration:** [analyze_repo.py](analyze_repo.py#L1225)
- **Configuration:** [scoring_policy.json](scoring_policy.json)
- **Scoring Logic:** [score_logic.md](score_logic.md#section-8)
- **AI Audit:** [audit_prompt.txt](audit_prompt.txt)

---

## FAQ

**Q: Can I disable GraphCodeBERT quality?**  
A: Yes, set `enabled: false` in `scoring_policy.json` under `graphcodebert.quality_scoring`

**Q: Will it slow down analysis?**  
A: No, only <50ms overhead per repository

**Q: What if a repo gets 0 quality score?**  
A: Check that code files were sampled; if none found, score is 0

**Q: Can I adjust the metrics?**  
A: Yes, all weights and thresholds are configurable in scoring_policy.json

**Q: Does it require external models?**  
A: No, it's entirely heuristic/pattern-based

**Q: How deterministic is it?**  
A: 100% deterministic - same code always gets same score

---

## Summary

GraphCodeBERT Quality Scoring provides semantic code analysis measuring modularity, reusability, style, and structure. It detects common anti-patterns and recognizes best practices across multiple languages, contributing 10% to the final evaluation score with negligible performance overhead.

For quick reference, see [QUICK_GUIDE.md](QUICK_GUIDE.md).
