# Skill Knowledge Assessment

## Overview

The **Skill Knowledge Assessment** measures **understanding depth** for each claimed technology stack. It's stored **separately** from Stack Accuracy and answers the question:

> "How well does the developer understand and use this technology?"

This is different from Stack Accuracy, which only confirms presence/absence.

---

## Key Difference: Accuracy vs. Knowledge

| Aspect                  | Stack Accuracy              | Skill Knowledge                           |
| ----------------------- | --------------------------- | ----------------------------------------- |
| **Question**            | Is this tech actually used? | Does developer understand it deeply?      |
| **Evidence**            | File presence, dependencies | Code patterns, best practices, complexity |
| **Score Range**         | 0-100 (penalty-based)       | 0-100 (indicator-based)                   |
| **Affects Final Score** | Yes (25% weight)            | No (informational only)                   |
| **Purpose**             | Prevent false claims        | Gauge expertise level                     |

---

## Knowledge Indicators (General)

Each indicator represents a depth signal and is worth points:

| Indicator                    | Points | What It Means                              |
| ---------------------------- | ------ | ------------------------------------------ |
| **Advanced Patterns**        | 20     | Uses sophisticated, non-obvious patterns   |
| **Error Handling**           | 15     | Robust try/catch or equivalent error paths |
| **State Management**         | 15     | Proper state flow, no prop drilling        |
| **API Integration**          | 15     | Proper async patterns, error handling      |
| **Testing Coverage**         | 10     | Tests exist, reasonable coverage           |
| **Performance Optimization** | 10     | Memoization, caching, lazy loading         |
| **Security Practices**       | 5      | Input validation, sanitization             |

---

## Knowledge Thresholds

Scores are bucketed by understanding level:

| Level            | Score Range | Description                               |
| ---------------- | ----------- | ----------------------------------------- |
| **Expert**       | 85-100      | Deep mastery with industry best practices |
| **Advanced**     | 70-84       | Strong understanding & proper usage       |
| **Intermediate** | 50-69       | Functional knowledge, basic patterns      |
| **Beginner**     | 30-49       | Basic usage, minimal patterns             |
| **Novice**       | 0-29        | Claimed but not evidenced                 |

---

## Language-Specific Signals

Knowledge is measured differently for each language/framework.

### JavaScript

```
- async/await patterns (15 pts)
- Modern ES6+ syntax (10 pts)
- Closures and scope understanding (10 pts)
- Event handling (5 pts)
- DOM manipulation (5 pts)
```

**Example:** A developer gets +15 for using async/await correctly, but 0 if code uses callbacks everywhere.

### Python

```
- List comprehensions (10 pts)
- Decorators (15 pts)
- Exception handling (10 pts)
- Context managers (10 pts)
- Generators (5 pts)
```

**Example:** A developer gets +15 for using decorators, +10 for context managers with proper cleanup.

### React

```
- Hooks usage (20 pts)
- State management strategy (15 pts)
- Component optimization (10 pts)
- Error boundaries (10 pts)
- Custom hooks (5 pts)
```

**Example:** Code using hooks correctly = +20, but class components everywhere = 0.

### Java

```
- OOP principles (15 pts)
- Generics (10 pts)
- Exception handling (10 pts)
- Design patterns (10 pts)
- Streams API (5 pts)
```

### SQL/Database

```
- Complex joins and aggregates (15 pts)
- Query optimization (15 pts)
- Transactions (10 pts)
- Indexing strategy (5 pts)
- Normalization (5 pts)
```

### Docker

```
- Multi-stage builds (15 pts)
- Volume management (10 pts)
- Networking (10 pts)
- Security best practices (5 pts)
```

---

## How Scores Are Calculated

### For Confirmed Stacks

1. **Start at 0**
2. **Scan codebase** for language-specific indicators
3. **Add points** for each detected pattern
4. **Cap at 100**

**Example (React):**

```
Hooks present? +20
State management visible? +15
Component optimization (React.memo, useCallback)? +10
Error boundaries implemented? +10
Custom hooks created? +5
---
Total: 60 points (Intermediate)
```

### For Unknown/False Stacks

1. **Start at 0**
2. **Attempt GraphCodeBERT semantic similarity** (if enabled)
3. **Show results with low confidence**

---

## Output Format

The skill assessment section in `evaluation_result.json` looks like:

```json
{
  "skill_assessment": [
    {
      "stack": "React",
      "confirmed": true,
      "knowledge_score": 78,
      "level": "advanced",
      "indicators_detected": [
        "hooks_usage (20 pts)",
        "state_management (15 pts)",
        "component_optimization (10 pts)",
        "error_boundaries (10 pts)"
      ],
      "remark": "Strong understanding of React hooks and state patterns. Shows solid grasp of optimization techniques."
    },
    {
      "stack": "Python",
      "confirmed": true,
      "knowledge_score": 62,
      "level": "intermediate",
      "indicators_detected": [
        "exception_handling (10 pts)",
        "list_comprehensions (10 pts)"
      ],
      "remark": "Functional knowledge with basic patterns. Could strengthen decorator usage and context managers."
    },
    {
      "stack": "Docker",
      "confirmed": false,
      "knowledge_score": 15,
      "level": "novice",
      "indicators_detected": [],
      "remark": "Claimed but not evidenced in codebase. No Docker-specific patterns detected."
    }
  ]
}
```

---

## Integration Points

### 1. in `analyze_repo.py`

The analyzer scans code files and detects language-specific patterns:

```python
def compute_skill_knowledge_per_stack(repo_path, claimed_stacks, policy):
    """Compute knowledge score for each claimed stack."""
    skill_policy = policy["skill_knowledge_assessment"]
    results = []

    for stack in claimed_stacks:
        score = 0
        indicators = []

        # Language-specific scanning
        if stack.lower() in skill_policy["language_specific_signals"]:
            signals = skill_policy["language_specific_signals"][stack.lower()]
            for pattern, points in signals.items():
                if pattern_found_in_codebase(repo_path, pattern, stack):
                    score += points
                    indicators.append(f"{pattern} ({points} pts)")

        results.append({
            "stack": stack,
            "knowledge_score": min(100, score),
            "indicators": indicators,
            "level": get_knowledge_level(score)
        })

    return results
```

### 2. in `ai_audit.py`

The AI auditor reviews skill scores and provides qualitative feedback:

```
Skill Assessment Review:

React (Score: 78 - Advanced):
✅ Strong indicators: hooks, state management, optimization
⚠️ Could improve: Error boundaries, custom hooks

Python (Score: 62 - Intermediate):
✅ Good: Exception handling, comprehensions
⚠️ Weak: No decorator usage, no context managers

Docker (Score: 15 - Novice):
❌ No evidence of Docker knowledge despite claim
→ Recommendation: Remove from resume or add Docker projects
```

---

## Customization

Edit `scoring_policy.json` under `skill_knowledge_assessment` to:

1. **Adjust indicator point values** (change `20` to `25` for more weight)
2. **Add new language-specific signals**
3. **Change knowledge thresholds**

Example: Make React hooks worth more:

```json
"react": {
  "hooks_usage": 30,  // Changed from 20
  "state_management": 15
}
```

---

## Sample Output Interpretation

### Score: 85+ (Expert)

```
"Advanced React patterns with hooks, context, and custom hooks.
Demonstrates understanding of performance optimization, memoization,
and error handling. Production-ready code quality."
```

### Score: 70-84 (Advanced)

```
"Solid React knowledge. Good state management and component patterns.
Shows understanding of common best practices."
```

### Score: 50-69 (Intermediate)

```
"Functional React implementation. Basic patterns present but missing
advanced optimizations and error handling strategies."
```

### Score: 30-49 (Beginner)

```
"Basic React usage. Limited patterns detected. Would benefit from
deeper study of hooks, state management, and optimization."
```

### Score: 0-29 (Novice)

```
"Claimed but not evidenced. No React-specific patterns detected in codebase."
```

---

## Non-Invasive Design

- **Separate from final score** — Skill assessment is informational
- **Complements Stack Accuracy** — Answers different questions
- **No score manipulation** — Only adds context
- **Actionable feedback** — Shows what to improve

---

## FAQ

**Q: How does this affect my final score?**  
A: It doesn't. It's separate. Final score is still based on Stack Accuracy, Commit Quality, Code Quality, Project Depth, and Documentation.

**Q: What if I'm intermediate but claimed expert?**  
A: Your Stack Accuracy won't be penalized (you do use React). But your Skill Knowledge will show 60, revealing the gap.

**Q: Can I improve my skill score?**  
A: Yes. Add patterns like hooks, error boundaries, testing, or documentation that showcase deeper understanding.

**Q: Why not use AI to rate knowledge?**  
A: Pattern detection is deterministic and reproducible. AI could hallucinate.

---

## Example: From Evidence to Knowledge

**Codebase shows:**

```javascript
// Pattern 1: Hooks usage
const [count, setCount] = useState(0);
useEffect(() => {
  /* ... */
}, [count]);
const MyContext = createContext();

// Pattern 2: Error boundaries
class ErrorBoundary extends React.Component {
  componentDidCatch(error, errorInfo) {
    /* ... */
  }
}

// Pattern 3: Optimization
const MemoComponent = React.memo(({ item }) => <div>{item}</div>);

// Pattern 4: Custom hooks
function useApi(url) {
  /* ... */
}
```

**Scoring:**

- Hooks usage → +20
- Error boundaries → +10
- Component optimization → +10
- Custom hooks → +5
- **Total: 45 → Intermediate**

---

**This framework ensures that claimed skills are backed by evidence of actual implementation depth.**
