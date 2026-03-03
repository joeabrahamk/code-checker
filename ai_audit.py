import ollama
import json
import os
import re

SYSTEM_PROMPT = open("audit_prompt.txt").read()


def _extract_json_object(text):
    if not text:
        return None

    fenced_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    candidate = fenced_match.group(1) if fenced_match else text

    try:
        return json.loads(candidate)
    except Exception:
        pass

    raw_match = re.search(r"\{[\s\S]*\}", text)
    if not raw_match:
        return None

    try:
        return json.loads(raw_match.group())
    except Exception:
        return None


def _level_from_score(score):
    if score >= 85:
        return "Expert"
    if score >= 70:
        return "Advanced"
    if score >= 50:
        return "Intermediate"
    if score >= 30:
        return "Beginner"
    return "Novice"


def normalize_audit_output(raw_output, evaluation_payload):
    parsed = _extract_json_object(raw_output)
    if not isinstance(parsed, dict):
        parsed = {}

    score_summary = {
        "final_score": evaluation_payload.get("evaluation_summary", {}).get("final_score"),
        "confidence": evaluation_payload.get("evaluation_summary", {}).get("confidence"),
        "stack_independent_scores": evaluation_payload.get("graphcodebert", {}).get("stack_independent_scores", [])
    }
    parsed["score_summary"] = score_summary

    skill_assessment = evaluation_payload.get("skill_assessment", [])
    by_stack = {item.get("stack", "").strip().lower(): item for item in skill_assessment if item.get("stack")}

    skill_review = parsed.get("skill_knowledge_review")
    if not isinstance(skill_review, dict):
        skill_review = {}
        parsed["skill_knowledge_review"] = skill_review

    existing_rows = skill_review.get("stack_assessments")
    if not isinstance(existing_rows, list):
        existing_rows = []

    rows_by_stack = {}
    for row in existing_rows:
        if isinstance(row, dict) and row.get("stack"):
            rows_by_stack[row["stack"].strip().lower()] = row

    normalized_rows = []
    for stack_key, skill_item in by_stack.items():
        row = rows_by_stack.get(stack_key, {"stack": skill_item.get("stack")})
        if not isinstance(row, dict):
            row = {"stack": skill_item.get("stack")}

        score = skill_item.get("score", 0)
        independent_score = skill_item.get("evidence", {}).get("graphcodebert_independent_score", score)
        demonstrated_level = _level_from_score(score)

        row["score"] = score
        row["graphcodebert_independent_score"] = independent_score
        row.setdefault("claimed_level", "Not specified")
        row["demonstrated_level"] = demonstrated_level
        row.setdefault("alignment", demonstrated_level)

        gaps = row.get("gaps")
        if isinstance(gaps, str):
            gaps = [gaps]
        if not isinstance(gaps, list) or not gaps:
            if skill_item.get("knows"):
                gaps = ["No major skill gap detected from repository evidence."]
            else:
                gaps = ["Claimed skill lacks sufficient implementation evidence in repository."]
        row["gaps"] = gaps

        recs = row.get("recommendations")
        if isinstance(recs, str):
            recs = [recs]
        if not isinstance(recs, list) or not recs:
            if skill_item.get("knows"):
                recs = ["Sustain evidence with broader real-world implementations and tests."]
            else:
                recs = ["Add production-like features in this stack to demonstrate practical depth."]
        row["recommendations"] = recs

        normalized_rows.append(row)

    skill_review["stack_assessments"] = normalized_rows
    skill_review.setdefault("summary", "Overall assessment of claimed vs demonstrated expertise")
    skill_review.setdefault("overall_expertise_assessment", "Assessment generated from deterministic evidence")

    allowed_skill_review_keys = {
        "summary",
        "stack_assessments",
        "overall_expertise_assessment"
    }
    skill_review = {k: v for k, v in skill_review.items() if k in allowed_skill_review_keys}
    parsed["skill_knowledge_review"] = skill_review

    parsed.setdefault("audit_summary", "Audit generated with deterministic score enrichment")
    parsed.setdefault("flags", [])
    parsed.setdefault("warnings", [])
    parsed.setdefault("consistency_check", "Based on provided evidence")

    allowed_top_keys = {
        "score_summary",
        "audit_summary",
        "flags",
        "warnings",
        "consistency_check",
        "graphcodebert_quality_review",
        "code_quality_deep_dive",
        "skill_knowledge_review",
        "improvement_suggestions"
    }
    parsed = {k: v for k, v in parsed.items() if k in allowed_top_keys}

    parsed.setdefault("graphcodebert_quality_review", {})
    parsed.setdefault("code_quality_deep_dive", {})
    parsed.setdefault("improvement_suggestions", [])

    return parsed

def load_evaluation_payload(filepath="evaluation_result.json"):
    """Load evaluation payload from JSON file generated by analyze_repo.py"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"'{filepath}' not found. Run 'python analyze_repo.py' first."
        )
    
    with open(filepath, "r") as f:
        return json.load(f)


def run_ai_audit(evaluation_payload):
    """Run AI audit on evaluation results.
    
    This function:
    - Does not allow score manipulation
    - Forces structured JSON response
    - Keeps AI boxed in to audit role only
    """
    response = ollama.chat(
        model="qwen2.5-coder:7b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(evaluation_payload, indent=2)
            }
        ]
    )

    raw_output = response["message"]["content"]
    normalized = normalize_audit_output(raw_output, evaluation_payload)
    return json.dumps(normalized, indent=2)


if __name__ == "__main__":
    # Load evaluation payload from analyze_repo.py output
    try:
        evaluation_payload = load_evaluation_payload()
        
        print("Loaded evaluation from: evaluation_result.json")
        print(f"Final Score: {evaluation_payload['evaluation_summary']['final_score']}")
        print(f"Confidence: {evaluation_payload['evaluation_summary']['confidence']}")
        print("\nRunning AI audit...")
        print("=" * 50)
        
        result = run_ai_audit(evaluation_payload)
        print(result)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nUsage:")
        print("  1. First run: python analyze_repo.py")
        print("  2. Then run:  python ai_audit.py")
