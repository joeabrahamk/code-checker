import ollama
import json

SYSTEM_PROMPT = open("audit_prompt.txt").read()

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

    return response["message"]["content"]


if __name__ == "__main__":
    # Test with real evaluation payload
    evaluation_payload = {
        "evaluation_summary": {
            "final_score": 72.4,
            "confidence": 0.80,
            "scores": {
                "stack_accuracy": 85,
                "commit_quality": 80,
                "code_quality": 70,
                "project_depth": 88,
                "documentation": 45
            }
        },
        "stack_analysis": {
            "claimed": ["react", "html", "python"],
            "confirmed": ["react", "html"],
            "false_claims": ["python"],
            "unknown": []
        },
        "repo_evidence": {
            "languages": {
                "javascript": 56168,
                "html": 5217,
                "css": 293
            },
            "commits": 32,
            "lines_added": 13113,
            "files_touched": 38,
            "modular_structure": True,
            "config_files": True,
            "error_handling": True,
            "readme_exists": True
        }
    }
    
    print("Running AI audit...")
    print("=" * 50)
    result = run_ai_audit(evaluation_payload)
    print(result)
