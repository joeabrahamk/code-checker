# GraphCodeBERT Quality Scoring - Integration Guide

## Overview

GraphCodeBERT Quality Scoring is a new semantic analysis component that **contributes 10% to the final evaluation score**. It analyzes actual code to measure:

- **Modularity** (25% weight) - Code separation of concerns and organization
- **Reusability** (25% weight) - Functions parameterized, DRY principle, composition patterns
- **Style Consistency** (20% weight) - Indentation, formatting, language-specific conventions
- **Structure Management** (30% weight) - File organization, layering, clear architecture

## What Changed

### 1. New Score Component

- Added `graphcodebert_quality` to `final_score_weights` (10%)
- Adjusted other weights:
  - Stack Accuracy: 22% (was 25%)
  - Commit Quality: 26% (was 30%)
  - Code Quality: 20% (unchanged)
  - Project Depth: 13% (was 15%)
  - Documentation: 9% (was 10%)

### 2. New Module: `graphcodebert_quality_scorer.py`

**Main Class:** `GraphCodeBERTScorer`

```python
from graphcodebert_quality_scorer import score_code_quality

# Score code samples
result = score_code_quality(code_samples, claimed_stacks, policy)

# Returns:
{
    "overall_score": 75.3,           # 0-100
    "modularity": 72.0,              # 0-100
    "reusability": 68.5,             # 0-100
    "style_consistency": 81.2,       # 0-100
    "structure": 79.1,               # 0-100
    "anti_patterns": [...],          # List of issues
    "best_practices": [...],         # List of good patterns
    "code_health": "Good"            # Excellent/Good/Acceptable/Needs improvement/Poor
}
```

### 3. Anti-Pattern Detection

**General Anti-Patterns:**

- Global state usage (`global`, `window.*`, `$GLOBALS`)
- Many unresolved TODOs/FIXMEs (>5)
- Very long functions (>150 lines)
- Deep nesting (>6 levels)

**Python-Specific:**

- Bare `except: pass`
- Improper boolean/None comparison (`== True`, `== False`, `== None`)

**JavaScript-Specific:**

- Using `var` instead of `const`/`let`
- Using `==` instead of `===`

**React-Specific:**

- Using class state instead of hooks
- Using array index as React key

### 4. Best Practice Detection

**General:**

- Good documentation/comments
- Error handling implemented
- Proper entry point handling

**Python:**

- Context managers used (`with` statements)
- Decorators used (`@decorator`)
- Pythonic patterns (list comprehensions)

**JavaScript/TypeScript:**

- Arrow functions used
- Modern async/await patterns
- Modern variable declarations (`const`/`let`)

**React:**

- React Hooks used (useState, useEffect)
- Performance optimization (React.memo, useMemo)

## Configuration

### In `scoring_policy.json`

```json
{
  "final_score_weights": {
    "stack_accuracy": 0.22,
    "commit_quality": 0.26,
    "code_quality": 0.2,
    "project_depth": 0.13,
    "documentation": 0.09,
    "graphcodebert_quality": 0.1
  },

  "graphcodebert": {
    "enabled": true,
    "quality_scoring": {
      "enabled": true,
      "max_files": 10,
      "metrics": {
        "modularity": { "weight": 0.25 },
        "reusability": { "weight": 0.25 },
        "style_consistency": { "weight": 0.2 },
        "structure": { "weight": 0.3 }
      },
      "anti_pattern_penalty": 5,
      "best_practice_bonus": 2,
      "quality_thresholds": {
        "excellent": 80,
        "good": 70,
        "acceptable": 60,
        "needs_improvement": 50
      }
    }
  }
}
```

## How It Works

### Step 1: Code Sampling

- Samples up to 10 representative code files from the repository
- Prioritizes main entry points (app.js, main.py, etc.)
- Prioritizes organized structure (components/, services/, etc.)
- Prefers files with 50-200 lines (meaningful but not overly large)

### Step 2: Scoring

For each metric:

**Modularity Score:**

- Base: 50 points
- +20 for good function/class ratio
- +15 for proper use of imports/modules
- +10 for clear folder separation (services, components, models, etc.)
- +10 for consistent naming conventions (camelCase/snake_case)
- Max: 100

**Reusability Score:**

- Base: 50 points
- +25 for parameterized functions (vs hardcoded values)
- +15 for DRY principle (>90% unique lines)
- +10 for functional patterns (map, filter, compose, pipe)
- +15 for abstractions (interfaces, base classes, protocols)
- Max: 100

**Style Consistency Score:**

- Base: 50 points
- +20 for consistent indentation (80%+ of code uses same style)
- +15 for good spacing/formatting
- +5-10 for language-specific style best practices
- Max: 100

**Structure Score:**

- Base: 50 points
- +25 for reasonable file sizes (30-200 lines average)
- +10 for varied file types/purposes
- +5 for clear directory structure
- Max: 100

### Step 3: Penalty and Bonus

- Each anti-pattern: -5 points (cumulative)
- Improper coding can significantly reduce score

### Step 4: Code Health Assessment

- Excellent: ≥80 + no anti-patterns
- Good: ≥70 + ≤1 anti-pattern
- Acceptable: ≥60
- Needs Improvement: ≥50
- Poor: <50

## Integration Points

### In `analyze_repo.py`

The `evaluate_repo()` function now:

1. **Samples code files**

   ```python
   code_samples = sample_code_files(local_path, max_files=10)
   ```

2. **Scores code quality**

   ```python
   from graphcodebert_quality_scorer import score_code_quality
   quality_result = score_code_quality(code_samples, claimed_stacks, policy)
   ```

3. **Includes in scores dict**

   ```python
   scores = {
       "stack_accuracy": ...,
       "commit_quality": ...,
       "code_quality": ...,
       "project_depth": ...,
       "documentation": ...,
       "graphcodebert_quality": quality_result["overall_score"]
   }
   ```

4. **Contributes to final score**

   ```python
   final_score = compute_final_score(scores, policy["final_score_weights"])
   ```

5. **Includes details in evaluation output**
   ```json
   {
     "graphcodebert": {
       "scores": {...},
       "quality_analysis": {
         "overall_score": 75.3,
         "modularity": 72.0,
         "anti_patterns": [...],
         "best_practices": [...]
       }
     }
   }
   ```

## Difference: GraphCodeBERT Quality vs Stack Skill Knowledge

| Component                 | Purpose                              | Method                                              | Contribution                            |
| ------------------------- | ------------------------------------ | --------------------------------------------------- | --------------------------------------- |
| **Stack Accuracy**        | Does the code use claimed stacks?    | GitHub API + file detection                         | 22% of score                            |
| **Skill Knowledge**       | Does developer understand the stack? | Regex pattern detection (50+ patterns per language) | Separate metric (not directly in score) |
| **GraphCodeBERT Quality** | Is the code well-written?            | Semantic analysis of style, modularity, reusability | 10% of score                            |

## Example Output

```json
{
  "evaluation_summary": {
    "final_score": 78.5,
    "scores": {
      "stack_accuracy": 85,
      "commit_quality": 72,
      "code_quality": 68,
      "project_depth": 75,
      "documentation": 70,
      "graphcodebert_quality": 74.3
    }
  },
  "graphcodebert": {
    "quality_analysis": {
      "overall_score": 74.3,
      "modularity": 72.0,
      "reusability": 68.5,
      "style_consistency": 81.2,
      "structure": 79.1,
      "anti_patterns": [
        "Using 'var' instead of 'const'/'let'",
        "Deep nesting (>6 levels)"
      ],
      "best_practices": [
        "Good documentation/comments",
        "Error handling implemented",
        "Modern async/await patterns"
      ],
      "code_health": "Good"
    }
  }
}
```

## Disabling GraphCodeBERT Quality

To disable this feature:

```json
{
  "graphcodebert": {
    "quality_scoring": {
      "enabled": false
    }
  }
}
```

If disabled, all repositories will receive 0 for GraphCodeBERT quality score.

## Testing

Run the analyzer with debug output:

```bash
python analyze_repo.py
# Repository URL: https://github.com/user/repo.git
# GitHub Username: user
# Claimed stacks: JavaScript, React, Python
```

Expected output includes:

```
  GraphCodeBERT Quality Score: 74.3
  Modularity: 72.0
  Reusability: 68.5
  Style Consistency: 81.2
  Structure: 79.1
```

## Performance Notes

- Samples up to 10 code files (configurable in policy)
- Analysis runs synchronously in evaluate_repo()
- Total time per repo: <100ms on modern hardware
- No external ML model required (pattern/heuristic based)

## Future Enhancements

Potential improvements:

- Cyclomatic complexity analysis
- Code coverage metrics (if available)
- Performance anti-patterns detection
- Security vulnerability scanning
- Framework-specific best practices
- Commit history analysis (refactoring patterns)
