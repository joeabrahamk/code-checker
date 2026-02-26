# Integration Guide: Skill Knowledge Assessment

## Quick Start

### Step 1: Already Done

- ✅ `scoring_policy.json` - Updated with skill assessment rules
- ✅ `skill_assessment_engine.py` - Pattern detection module created
- ✅ `audit_prompt.txt` - Updated for skill review
- ✅ Documentation files created

### Step 2: Integrate into `analyze_repo.py`

Find this section in `analyze_repo.py` (around line 1350):

```python
def main():
    # ... existing code ...

    # Compute all scores
    stack_accuracy_score = compute_stack_accuracy(stack_result, policy)
    commit_quality_score = compute_commit_quality(commits, policy)
    code_quality_score = compute_code_quality(repo_path, policy)
    project_depth_score = compute_project_depth(repo_path, lines_stats, policy)
    documentation_score = compute_documentation(repo_path, claimed_stacks_raw, policy)
    confidence = compute_confidence(stack_result, policy)

    # Build final payload
    evaluation = {
        "policy_version": policy["version"],
        # ... existing fields ...
    }
```

**Add this after `documentation_score`:**

```python
# NEW: Compute skill knowledge assessment
from skill_assessment_engine import compute_skill_assessments

skill_assessments = compute_skill_assessments(
    repo_path,
    claimed_stacks_raw,
    policy
)
```

**Then add to the `evaluation` dict:**

```python
    evaluation = {
        "policy_version": policy["version"],
        # ... existing fields ...
        "skill_assessment": skill_assessments,  # ADD THIS LINE
    }
```

### Step 3: Test

Run the analyzer:

```bash
py analyze_repo.py
```

Check `evaluation_result.json` for new `skill_assessment` array:

```json
{
  "skill_assessment": [
    {
      "stack": "React",
      "knowledge_score": 75,
      "level": "advanced",
      "indicators_detected": [...],
      "remark": "..."
    }
  ]
}
```

### Step 4: Run AI Audit (Optional)

```bash
py ai_audit.py
```

Should now include skill_knowledge_review in output.

---

## Code Integration Details

### Option A: Minimal Integration (5 minutes)

Just add skill_assessments to output:

```python
from skill_assessment_engine import compute_skill_assessments

# In main(), after other scores
skill_assessments = compute_skill_assessments(repo_path, claimed_stacks_raw, policy)

# In evaluation dict
"skill_assessment": skill_assessments
```

### Option B: Full Integration (15 minutes)

Add skill assessment to the final output format:

```python
# Print skill assessment
print("\n" + "="*50)
print("SKILL KNOWLEDGE ASSESSMENT")
print("="*50)

for skill in skill_assessments:
    print(f"\n{skill['stack']}:")
    print(f"  Score: {skill['knowledge_score']}")
    print(f"  Level: {skill['level']}")
    print(f"  Remark: {skill['remark']}")
    if skill['indicators_detected']:
        print(f"  Patterns: {', '.join(skill['indicators_detected'][:3])}")
```

---

## Customization

### Add New Language

Edit `scoring_policy.json`:

```json
"skill_knowledge_assessment": {
  "language_specific_signals": {
    "your_language": {
      "pattern_name_1": 20,
      "pattern_name_2": 15,
      "pattern_name_3": 10
    }
  }
}
```

Then update `skill_assessment_engine.py`, in `_detect_pattern()`:

```python
elif stack == 'your_language':
    patterns = {
        'pattern_name_1': r'regex_pattern_1',
        'pattern_name_2': r'regex_pattern_2',
        'pattern_name_3': r'regex_pattern_3',
    }
```

### Adjust Point Values

Change points in `scoring_policy.json`:

```json
"react": {
  "hooks_usage": 30,        // Was 20
  "state_management": 20,   // Was 15
  "custom_hooks": 15        // Was 5
}
```

### Change Knowledge Thresholds

Edit thresholds in `scoring_policy.json`:

```json
"knowledge_thresholds": {
  "expert": { "min": 90 },     // Was 85
  "advanced": { "min": 75 },   // Was 70
  "intermediate": { "min": 55 },
  "beginner": { "min": 30 },
  "novice": { "min": 0 }
}
```

---

## Understanding the Output

### skill_assessment Array

Each entry:

```json
{
  "stack": "React", // Technology name
  "knowledge_score": 78, // 0-100
  "level": "advanced", // expert/advanced/intermediate/beginner/novice
  "indicators_detected": [
    // Patterns found
    "hooks_usage (20 pts)",
    "state_management (15 pts)",
    "component_optimization (10 pts)",
    "error_boundaries (10 pts)"
  ],
  "remark": "Strong understanding with proper usage patterns..."
}
```

### Interpretation Guide

| Score  | Level        | Meaning                    |
| ------ | ------------ | -------------------------- |
| 85-100 | Expert       | Production-ready mastery   |
| 70-84  | Advanced     | Professional understanding |
| 50-69  | Intermediate | Functional knowledge       |
| 30-49  | Beginner     | Basic usage                |
| 0-29   | Novice       | Claimed but not evidenced  |

---

## AI Audit Integration

The updated `audit_prompt.txt` now instructs the AI to:

1. Review each `skill_assessment` entry
2. Check if level matches claim
3. Identify gaps
4. Suggest improvements
5. Flag inconsistencies

Example AI audit output:

```json
{
  "skill_knowledge_review": {
    "summary": "Developer has beginner-to-intermediate skills...",
    "stack_assessments": [
      {
        "stack": "React",
        "claimed_level": "expert",
        "demonstrated_level": "intermediate",
        "alignment": "Mismatch - claiming expert but showing intermediate",
        "gaps": "Missing error boundaries, custom hooks, advanced optimizations",
        "recommendations": "Add error boundary components, create custom hooks for API calls"
      }
    ]
  }
}
```

---

## File Structure After Integration

```
├── analyze_repo.py              # Main analyzer (modify to add skill_assessments)
├── skill_assessment_engine.py   # NEW: Pattern detection engine
├── scoring_policy.json          # UPDATED: Added skill_knowledge_assessment
├── audit_prompt.txt             # UPDATED: Added skill review instructions
├── score_logic.md               # UPDATED: Added skill knowledge section
├── skill_assessment.md          # NEW: Full skill assessment documentation
├── SKILL_ASSESSMENT_IMPLEMENTATION.md  # NEW: Implementation guide
├── ai_audit.py                  # Reviews skill assessments
└── evaluation_result.json       # Output (now includes skill_assessment)
```

---

## Testing Checklist

- [ ] Can run `py analyze_repo.py` without errors
- [ ] `evaluation_result.json` contains `skill_assessment` array
- [ ] Each skill has score, level, and indicators
- [ ] `py ai_audit.py` runs successfully
- [ ] Audit output includes skill_knowledge_review section
- [ ] Skill scores reflect actual code patterns
- [ ] Can customize patterns in `scoring_policy.json`
- [ ] New languages can be added to detection

---

## Troubleshooting

**Q: `skill_assessment` is empty**
A: Check `claimed_stacks_raw` is being passed. Verify patterns in policy.

**Q: Scores seem wrong**
A: Check patterns are matching. Enable debug logging in `skill_assessment_engine.py`:

```python
def _detect_pattern(self, pattern_name, stack, code_content):
    content_lower = code_content.lower()
    # Add this line:
    print(f"[DEBUG] Checking {stack}.{pattern_name}")
```

**Q: AI audit doesn't review skills**
A: Ensure `audit_prompt.txt` has been updated with skill review instructions.

**Q: Module not found error**
A: Ensure `skill_assessment_engine.py` is in same directory as `analyze_repo.py`.

---

## Next Steps

1. Integrate into `analyze_repo.py` (see Step 2 above)
2. Test with sample repo
3. Customize patterns for your use case
4. Run AI audit to validate results
5. Iterate on thresholds if needed

---

## Support

See:

- [skill_assessment.md](skill_assessment.md) - Full documentation
- [score_logic.md](score_logic.md) - Score calculation details
- [SKILL_ASSESSMENT_IMPLEMENTATION.md](SKILL_ASSESSMENT_IMPLEMENTATION.md) - Implementation overview
- [scoring_policy.json](scoring_policy.json) - All configurable rules
