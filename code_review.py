"""
AI Code Review Auditor
(adversarial, non-authoritative, confidence-affecting only)

This is NOT the same as the AI audit system.
- The audit AI reviews your evaluator's output
- The code review AI reviews the actual code itself
They must never be merged.

What it CAN do:
- Read sampled code
- Comment on logic depth
- Flag potential manipulation
- Raise code-quality warnings
- Reduce confidence
- Add interpretation notes

What it CANNOT do:
- Change scores
- Add penalties
- Detect stacks
- Decide pass/fail
- Rewrite rules
- Judge intent or morality
"""

import os
import json
import ollama

# Load the system prompt (safety cage)
SYSTEM_PROMPT = open("code_review_prompt.txt").read()

# Folders to ignore when sampling
IGNORED_PATHS = [
    "node_modules", "vendor", "dist", "build", 
    "__pycache__", ".venv", ".git", "coverage",
    ".next", "out", ".cache"
]

# File extensions to consider for code review
CODE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".go", ".rb", ".php"}

# Config files to exclude (not interesting for logic review)
CONFIG_FILES = {
    "package.json", "package-lock.json", "tsconfig.json", 
    "webpack.config.js", "babel.config.js", ".eslintrc.js",
    "requirements.txt", "setup.py", "pyproject.toml"
}


def is_ignored(path):
    """Check if path should be ignored."""
    return any(ignored in path for ignored in IGNORED_PATHS)


def is_config_file(filename):
    """Check if file is a config file (not interesting for logic review)."""
    return filename.lower() in CONFIG_FILES


def get_file_info(filepath):
    """Get file size and line count."""
    try:
        with open(filepath, "r", errors="ignore") as f:
            content = f.read()
            return {
                "path": filepath,
                "size": len(content),
                "lines": content.count("\n") + 1,
                "content": content
            }
    except Exception:
        return None


def select_representative_files(repo_path, max_files=5):
    """
    Select 3-5 representative files for code review.
    
    Criteria:
    - Highest LOC (but not monster files)
    - Core logic files (entry points, services, components)
    - Exclude configs and generated code
    
    This is chosen by the system, NOT the AI.
    """
    all_files = []
    
    # Priority patterns (files likely to contain core logic)
    priority_patterns = [
        "app.", "main.", "index.", "server.", "client.",
        "/components/", "/services/", "/api/", "/utils/",
        "/pages/", "/routes/", "/controllers/", "/models/"
    ]
    
    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue
            
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            
            if ext not in CODE_EXTENSIONS:
                continue
            if is_config_file(filename):
                continue
                
            filepath = os.path.join(root, filename)
            file_info = get_file_info(filepath)
            
            if file_info and 10 < file_info["lines"] < 500:
                # Calculate priority score
                priority = 0
                rel_path = filepath.replace(repo_path, "").lower()
                
                for pattern in priority_patterns:
                    if pattern in rel_path:
                        priority += 10
                
                # Bonus for reasonable file sizes (sweet spot: 50-200 lines)
                if 50 <= file_info["lines"] <= 200:
                    priority += 5
                
                file_info["priority"] = priority
                file_info["rel_path"] = rel_path.lstrip("/\\")
                all_files.append(file_info)
    
    # Sort by priority (desc), then by lines (desc)
    all_files.sort(key=lambda x: (x["priority"], x["lines"]), reverse=True)
    
    # Take top N files
    selected = all_files[:max_files]
    
    return selected


def build_review_payload(repo_path, confirmed_stacks, lines_added, files_touched):
    """
    Build the input payload for the Code Review Auditor.
    
    Sends only what it needs - no GitHub links, no scores, no commits.
    """
    # Determine project type from stacks
    project_type = "unknown"
    stacks_lower = [s.lower() for s in confirmed_stacks]
    
    if any(s in stacks_lower for s in ["react", "vue", "angular", "svelte"]):
        project_type = "frontend"
    elif any(s in stacks_lower for s in ["django", "flask", "express", "fastapi"]):
        project_type = "backend"
    elif any(s in stacks_lower for s in ["next", "nuxt", "remix"]):
        project_type = "fullstack"
    
    # Select representative files
    selected_files = select_representative_files(repo_path)
    
    if not selected_files:
        return None, "No suitable code files found for review"
    
    # Build code samples (path + content only)
    code_samples = []
    for f in selected_files:
        code_samples.append({
            "path": f["rel_path"],
            "content": f["content"]
        })
    
    payload = {
        "project_context": {
            "confirmed_stacks": confirmed_stacks,
            "project_type": project_type,
            "lines_added": lines_added,
            "files_touched": files_touched
        },
        "code_samples": code_samples
    }
    
    return payload, None


def run_code_review(repo_path, confirmed_stacks, lines_added, files_touched):
    """
    Run the AI Code Review Auditor.
    
    Returns the review result or error message.
    """
    # Build payload
    payload, error = build_review_payload(
        repo_path, confirmed_stacks, lines_added, files_touched
    )
    
    if error:
        return {"error": error}
    
    # Print which files are being reviewed
    print("\nFiles selected for code review:")
    for sample in payload["code_samples"]:
        print(f"  - {sample['path']}")
    
    # Call the AI
    try:
        response = ollama.chat(
            model="qwen2.5-coder:7b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, indent=2)}
            ]
        )
        
        return response["message"]["content"]
        
    except Exception as e:
        return {"error": f"AI review failed: {e}"}


def apply_confidence_impact(base_confidence, review_result):
    """
    Adjust confidence based on code review findings.
    
    This is how it influences trust WITHOUT touching scores.
    """
    impact_map = {
        "none": 0.0,
        "low": -0.05,
        "medium": -0.12,
        "high": -0.20
    }
    
    try:
        # Parse the review result if it's a string
        if isinstance(review_result, str):
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', review_result)
            if json_match:
                review_data = json.loads(json_match.group())
            else:
                return base_confidence, "Could not parse review"
        else:
            review_data = review_result
        
        impact = review_data.get("confidence_impact", "none").lower()
        adjustment = impact_map.get(impact, 0.0)
        
        adjusted = max(0.30, min(0.95, base_confidence + adjustment))
        
        return round(adjusted, 2), None
        
    except Exception as e:
        return base_confidence, f"Could not apply impact: {e}"


def load_evaluation_result(filepath="evaluation_result.json"):
    """Load the evaluation result from analyze_repo.py"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"'{filepath}' not found. Run 'python analyze_repo.py' first."
        )
    
    with open(filepath, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    # Load evaluation result
    try:
        eval_result = load_evaluation_result()
        
        # Extract what we need
        confirmed_stacks = eval_result["stack_analysis"]["confirmed"]
        lines_added = eval_result["repo_evidence"]["lines_added"]
        files_touched = eval_result["repo_evidence"]["files_touched"]
        base_confidence = eval_result["evaluation_summary"]["confidence"]
        final_score = eval_result["evaluation_summary"]["final_score"]
        
        print("=" * 60)
        print("AI CODE REVIEW AUDITOR")
        print("(adversarial, non-authoritative, confidence-affecting only)")
        print("=" * 60)
        
        print(f"\nBase Score: {final_score}")
        print(f"Base Confidence: {base_confidence}")
        
        # Run code review
        repo_path = "./temp_repo"
        review_result = run_code_review(
            repo_path, confirmed_stacks, lines_added, files_touched
        )
        
        print("\n" + "-" * 60)
        print("CODE REVIEW RESULT")
        print("-" * 60)
        print(review_result)
        
        # Apply confidence impact
        adjusted_confidence, error = apply_confidence_impact(
            base_confidence, review_result
        )
        
        if error:
            print(f"\nNote: {error}")
        else:
            print("\n" + "=" * 60)
            print("FINAL ASSESSMENT")
            print("=" * 60)
            print(f"Final Score: {final_score} (unchanged)")
            print(f"Base Confidence: {base_confidence}")
            print(f"Adjusted Confidence: {adjusted_confidence}")
            
            if adjusted_confidence < base_confidence:
                print(f"\n⚠️  Confidence reduced by {base_confidence - adjusted_confidence:.2f}")
                print("   Reason: Code review flagged potential concerns")
            else:
                print("\n✓ No significant concerns detected")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nUsage:")
        print("  1. First run: python analyze_repo.py")
        print("  2. Then run:  python code_review.py")
