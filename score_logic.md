# Score Logic

This document explains how the evaluator converts repo evidence into scores. All scoring rules live in [scoring_policy.json](scoring_policy.json). The Python code reads that policy and applies it deterministically.

---

## 1) Inputs Used for Scoring

The scorer uses three sources of evidence:

1. **Git history** (commit counts, commit messages, code churn)
2. **Repo structure and file contents** (folder layout, configs, file sizes)
3. **GitHub language stats** (bytes per language)

These are collected in [analyze_repo.py](analyze_repo.py) and summarized into a single evaluation payload stored as `evaluation_result.json`.

---

## 2) Final Score Formula

The final score is a weighted sum of six sub-scores:

$$\text{Final Score} = (S_a \cdot w_a) + (S_c \cdot w_c) + (S_q \cdot w_q) + (S_p \cdot w_p) + (S_d \cdot w_d) + (S_g \cdot w_g)$$

Where:

- $S_a$ = Stack Accuracy
- $S_c$ = Commit Quality
- $S_q$ = Code Quality
- $S_p$ = Project Depth
- $S_d$ = Documentation
- $S_g$ = GraphCodeBERT Quality (NEW)

Weights are configured in [scoring_policy.json](scoring_policy.json):

```json
"final_score_weights": {
  "stack_accuracy": 0.22,
  "commit_quality": 0.26,
  "code_quality": 0.20,
  "project_depth": 0.13,
  "documentation": 0.09,
  "graphcodebert_quality": 0.10
}
```

**Total = 1.00** (all weights sum to 100%)

---

## 3) Stack Accuracy (25%)

**Purpose:** Penalize false claims. Reward verifiable tech.

### Evidence Rules

- **Languages** are confirmed by GitHub language bytes.
- **Frameworks** are confirmed by structural detection (e.g., React in `package.json`).
- **Runtimes** are confirmed via config files (e.g., Node.js via `package.json`).
- **Databases** are confirmed via dependency hints (e.g., `mongoose`, `psycopg2`).
- **Tooling** is confirmed via config files (`Dockerfile`, `webpack.config.js`, etc.).

### Score Calculation

Start at 100, subtract penalties for false claims:

$$S_a = 100 - \min(\text{false\_claims} \cdot 15, 60)$$

Configured in [scoring_policy.json](scoring_policy.json):

```json
"stack_accuracy": {
  "false_claim_penalty_per_stack": 15,
  "max_penalty": 60
}
```

---

## 4) Commit Quality (30%)

**Purpose:** Reward consistent, meaningful commit history.

### Base Score by Commit Count

| Commits | Score |
| ------- | ----- |
| 1–5     | 40    |
| 6–15    | 60    |
| 16–50   | 80    |
| 51–200  | 100   |
| 201+    | 90    |

### Quality Multipliers

Multipliers are applied based on commit message quality, spacing over time, or dump commits:

```json
"quality_multipliers": {
  "descriptive_messages": 1.1,
  "spread_over_time": 1.15,
  "single_massive_commit": 0.5
}
```

Final commit quality:

$$S_c = \text{base\_score} \times \text{applicable\_multipliers}$$

---

## 5) Code Quality (20%)

**Purpose:** Evaluate engineering hygiene signals.

### Signals (25 points each)

- **Modular folders** (`src`, `components`, `utils`, `services`, `pages`, `lib`)
- **Config files present** (`package.json`, `tsconfig.json`, `requirements.txt`, etc.)
- **Reasonable file sizes** (less than 20% of code files exceed 800 lines)
- **Consistent naming** (less than 20% of files with messy names)

Configured in [scoring_policy.json](scoring_policy.json):

```json
"code_quality": {
  "structure_signals": {
    "modular_folders": 25,
    "config_files_present": 25,
    "reasonable_file_sizes": 25,
    "consistent_naming": 25
  },
  "lines_per_commit_ideal_range": [20, 150],
  "test_file_bonus": 10,
  "linting_config_bonus": 5
}
```

**Score:** Sum of detected signals (plus optional bonuses).

---

## 6) Project Depth (15%)

**Purpose:** Distinguish real projects from tutorials/boilerplate.

### Base Score from LOC

| Lines of Code | Score |
| ------------- | ----- |
| 0             | 0     |
| 100           | 20    |
| 500           | 40    |
| 1000          | 55    |
| 2500          | 70    |
| 5000+         | 80    |

### Feature Indicators (+10 each)

- Error handling (`try/catch`, `except`)
- Multiple modules (3+ code folders)
- Data layers (`services`, `api`, `controllers`)
- Edge case handling (guard logic like `if (!x)`)

**Score:** Base LOC score + feature indicator bonuses (capped at 100).

---

## 7) Documentation (10%)

**Purpose:** Measure communication intent.

### Signals

- README exists → +30
- Setup instructions → +20
- Tech stack documented → +15
- Usage examples → +20
- Screenshots/diagrams → +15

No README = 0, regardless of other signals.

---

## 8) Confidence Score (Not in Final Score)

Confidence is reported separately and reflects evidence strength. It does **not** affect the final score.

$$\text{Confidence} = 0.70 + (\text{confirmed} \cdot 0.10) - (\text{unknown} \cdot 0.05) - (\text{false} \cdot 0.10)$$

Clamped to $[0.30, 0.95]$.

Configured in [scoring_policy.json](scoring_policy.json):

```json
"confidence": {
  "base": 0.70,
  "confirmed_stack_bonus": 0.10,
  "unknown_stack_penalty": 0.05,
  "false_claim_penalty": 0.10,
  "min": 0.30,
  "max": 0.95
}
```

---

## 9) Skill Knowledge Assessment (Separate, Non-Final-Score)

**Purpose:** Measure **understanding depth** for each claimed stack independently from Stack Accuracy.

This is stored separately and does **not** affect the final score. It answers:

> "How well does the developer understand this technology?"

### Knowledge Levels

- **Expert (85+):** Deep mastery with best practices
- **Advanced (70-84):** Strong understanding with proper usage
- **Intermediate (50-69):** Functional knowledge with basic patterns
- **Beginner (30-49):** Basic usage with minimal patterns
- **Novice (0-29):** Claimed but not evidenced

### Language-Specific Indicators

The system detects patterns specific to each language:

**JavaScript/TypeScript:**

- Async/await usage
- Modern ES6 syntax
- Closures and scope understanding
- Event handling
- DOM manipulation

**Python:**

- List comprehensions
- Decorators
- Exception handling
- Context managers
- Generators

**React:**

- Hooks usage (useState, useEffect, useContext)
- State management strategy
- Component optimization (React.memo)
- Error boundaries
- Custom hooks

**Java:**

- OOP principles
- Generics
- Exception handling
- Design patterns
- Streams API

**SQL:**

- Complex joins and aggregates
- Query optimization
- Transactions
- Indexing strategy
- Normalization

**Docker:**

- Multi-stage builds
- Volume management
- Networking
- Security practices

### Score Calculation

Each detected pattern adds points. For example, React:

$$
\text{React Score} = \begin{cases}
+20 & \text{if hooks usage detected} \\
+15 & \text{if state management detected} \\
+10 & \text{if component optimization detected} \\
+10 & \text{if error boundaries detected} \\
+5 & \text{if custom hooks detected}
\end{cases}
$$

Capped at 100.

### Output Example

```json
{
  "skill_assessment": [
    {
      "stack": "React",
      "knowledge_score": 78,
      "level": "advanced",
      "indicators_detected": [
        "hooks_usage (20 pts)",
        "state_management (15 pts)",
        "component_optimization (10 pts)",
        "error_boundaries (10 pts)"
      ],
      "remark": "Strong understanding with proper usage patterns. Detected: hooks_usage, state_management, component_optimization and 1 more."
    },
    {
      "stack": "Docker",
      "knowledge_score": 15,
      "level": "novice",
      "indicators_detected": [],
      "remark": "Claimed but not evidenced. No Docker-specific patterns detected."
    }
  ]
}
```

---

## 8) GraphCodeBERT Quality (10%)

**Purpose:** Measure code quality merits through semantic analysis. Scores style, modularity, reusability, and structure that can't be captured by rule-based metrics.

**Method:**

1. Sample up to 10 representative code files
2. Analyze semantic properties (without ML model)
3. Detect anti-patterns and best practices
4. Combine metrics into overall quality score

**Four Quality Metrics:**

### Modularity (25% weight)

Measures separation of concerns and code organization.

- Base: 50 points
- +20 for good function/class definition density
- +15 for proper module imports/requires
- +10 for architectural separation (services, components, models)
- +10 for consistent naming conventions (camelCase/snake_case)
- Max: 100 points

**Indicators:** Presence of service/component/controller folders, clear function boundaries, organized structure.

### Reusability (25% weight)

Measures how composable and reusable code is.

- Base: 50 points
- +25 for parameterized functions (vs hardcoded)
- +15 for DRY principle (>90% unique lines)
- +10 for functional/composition patterns (map, filter, pipe)
- +15 for abstractions (interfaces, base classes, protocols)
- Max: 100 points

**Indicators:** Functions accept parameters, no code duplication, higher-order functions, clear abstraction levels.

### Style Consistency (20% weight)

Measures formatting consistency and language conventions.

- Base: 50 points
- +20 for indentation consistency (80%+ same style)
- +15 for proper spacing/formatting
- +5-10 for language-specific conventions (PEP 8, ES6, etc.)
- Max: 100 points

**Indicators:** Consistent indentation, proper spacing, language-specific best practices.

### Structure Management (30% weight)

Measures overall code architecture and organization.

- Base: 50 points
- +25 for reasonable file sizes (30-200 lines average)
- +10 for diverse file purposes
- +5 for clear directory structure with meaningful separations
- Max: 100 points

**Indicators:** Well-sized files, layered architecture, separation of concerns.

**Anti-Pattern Penalties:**

Each anti-pattern detected reduces the score by 5 points:

**General:**

- Global state usage (window.\*, global, $GLOBALS)
- Many unresolved TODOs/FIXMEs (>5)
- Very long functions (>150 lines)
- Deep nesting (>6 levels)

**Python:**

- Bare `except: pass`
- Improper boolean comparison (`== True`, `== False`, `== None`)

**JavaScript:**

- Using `var` instead of `const`/`let`
- Using `==` instead of `===`

**React:**

- Using class state instead of hooks
- Using array index as React key

**Code Health Assessment:**

- Excellent: ≥80 + no anti-patterns
- Good: ≥70 + ≤1 anti-pattern
- Acceptable: ≥60
- Needs Improvement: ≥50
- Poor: <50

**Example Calculation:**

```
Code sample analysis:
- Modularity: 72 (good function organization)
- Reusability: 68 (some DRY violations)
- Style Consistency: 81 (consistent formatting)
- Structure: 79 (clear layering)

Overall Score = (72×0.25) + (68×0.25) + (81×0.20) + (79×0.30)
              = 18 + 17 + 16.2 + 23.7
              = 74.9

Anti-patterns detected: 1 (var usage)
Penalty: -5
Final GraphCodeBERT Quality = 69.9
```

---

## 9) Determinism Guarantees

- All scores are **rule-based** and **policy-driven**.
- No model can change scores.
- The policy file is the single source of truth.

If you want different scoring behavior, edit [scoring_policy.json](scoring_policy.json). The code remains unchanged.
