import os
import re
import json
import requests
from git import Repo


# Folders that inflate numbers and destroy credibility
IGNORED_PATHS = [
    "node_modules",
    "vendor",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    ".git"
]

# Common module directories - signs of intentional structure
COMMON_MODULE_DIRS = {"src", "components", "utils", "services", "pages", "lib", "helpers", "hooks"}

# Config files - boring but they matter
CONFIG_FILES = {
    "package.json",
    "tsconfig.json",
    "pyproject.toml",
    "requirements.txt",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.json",
    ".prettierrc",
    ".prettierrc.js",
    ".prettierrc.json",
    "setup.py",
    "setup.cfg"
}

# Stack signatures - we only detect what we can prove
STACK_SIGNATURES = {
    "React": ["package.json", "react"],
    "Node.js": ["package.json"],
    "Python": [".py"],
    "Django": ["manage.py"],
    "Flask": ["flask"],
    "MongoDB": ["mongodb", "mongoose"],
    "PostgreSQL": ["psycopg2", "postgres"]
}

# =============================================================================
# STACK TAXONOMY - Not ML. This is ontology. Machines need categories.
# =============================================================================

STACK_CATEGORIES = {
    "languages": {
        "html": "HTML",
        "css": "CSS",
        "javascript": "JavaScript",
        "js": "JavaScript",
        "jsx": "JavaScript",
        "ts": "TypeScript",
        "tsx": "TypeScript",
        "java": "Java",
        "csharp": "C#",
        "c#": "C#",
        "go": "Go",
        "ruby": "Ruby",
        "php": "PHP",   
        "swift": "Swift",
        "kotlin": "Kotlin",
        "rust": "Rust",
        "python": "Python",
        "typescript": "TypeScript"
    },

    "frameworks": {
        "react": "React",
        "django": "Django",
        "flask": "Flask",
        "next": "Next.js",
        "next.js": "Next.js",
        "nextjs": "Next.js",
        "spring": "Spring",
        "laravel": "Laravel",
        "rails": "Ruby on Rails"
        
    },

    "runtimes": {
        "node": "Node.js",
        "node.js": "Node.js",
        "nodejs": "Node.js",
        
    },

    "databases": {
        "mongodb": "MongoDB",
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL"
    },

    "tooling": {
        "docker": "Docker",
        "git": "Git",
        "webpack": "Webpack",
        "babel": "Babel"
    }
}

# Database confirmation signatures
DATABASE_SIGNATURES = {
    "mongodb": ["mongoose", "mongodb"],
    "postgresql": ["psycopg2", "pg", "sequelize"]
}

# Tooling confirmation signatures
TOOLING_SIGNATURES = {
    "docker": ["dockerfile", "Dockerfile", "docker-compose.yml"],
    "git": [".git"],
    "webpack": ["webpack.config.js"]
}


# =============================================================================
# POLICY LOADER
# =============================================================================

def load_policy(path="scoring_policy.json"):
    """Load the scoring policy from JSON."""
    with open(path, "r") as f:
        return json.load(f)


# =============================================================================
# STACK CONFIRMATION FUNCTIONS
# =============================================================================

def normalize_claims(claimed_raw):
    """Free text is chaos. Normalize it."""
    return [c.strip().lower() for c in claimed_raw if c.strip()]


def confirm_languages(claimed, repo_languages):
    """Confirm languages using GitHub stats. If GitHub reports bytes, it's confirmed."""
    confirmed = set()
    languages_present = {k.lower() for k in repo_languages.keys()}

    for c in claimed:
        if c in languages_present:
            confirmed.add(c)

    return confirmed


def confirm_frameworks(claimed, detected_stacks):
    """Frameworks require stronger evidence - structural detection."""
    detected = {d.lower() for d in detected_stacks}
    return {c for c in claimed if c in detected}


def confirm_runtimes(claimed, detected_stacks):
    """Runtimes confirmed via project structure (e.g., package.json for Node.js)."""
    detected = {d.lower() for d in detected_stacks}
    return {c for c in claimed if c in detected}


def confirm_databases(claimed, repo_path):
    """Databases confirmed by dependency names or connection libraries."""
    confirmed = set()

    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue

        for file in files:
            file_lower = file.lower()
            full_path = os.path.join(root, file)
            
            for db, sigs in DATABASE_SIGNATURES.items():
                for sig in sigs:
                    # Check filename
                    if sig in file_lower:
                        confirmed.add(db)
                    # Check file contents for package.json or requirements.txt
                    if file in ["package.json", "requirements.txt"]:
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                content = f.read().lower()
                                if sig.lower() in content:
                                    confirmed.add(db)
                        except:
                            pass

    return {c for c in claimed if c in confirmed}


def confirm_tooling(claimed, repo_path):
    """Tooling confirmed by presence of known config files."""
    confirmed = set()

    for tool, sigs in TOOLING_SIGNATURES.items():
        for sig in sigs:
            if os.path.exists(os.path.join(repo_path, sig)):
                confirmed.add(tool)

    return {c for c in claimed if c in confirmed}


def confirm_stacks(claimed, detected_stacks, repo_languages, repo_path):
    """Unified stack confirmation - the heart of evaluator's honesty."""
    confirmed = set()

    confirmed |= confirm_languages(claimed, repo_languages)
    confirmed |= confirm_frameworks(claimed, detected_stacks)
    confirmed |= confirm_runtimes(claimed, detected_stacks)
    confirmed |= confirm_databases(claimed, repo_path)
    confirmed |= confirm_tooling(claimed, repo_path)

    return confirmed


def get_stack_category(stack_name):
    """Determine which category a stack belongs to."""
    stack_lower = stack_name.lower()
    for category, stacks in STACK_CATEGORIES.items():
        if stack_lower in stacks:
            return category
    return None


# 
# SCORING FUNCTIONS - No AI. No interpretation. Just math.
# 

def compute_stack_accuracy(claimed, detected, policy):
    """DEPRECATED: Use compute_stack_accuracy_v2 instead."""
    claimed = set(map(str.lower, claimed))
    detected = set(map(str.lower, detected))

    false_claims = claimed - detected
    confirmed = claimed & detected
    unknown = claimed - detected

    base_score = 100
    penalty = len(false_claims) * policy["stack_accuracy"]["false_claim_penalty_per_stack"]
    penalty = min(penalty, policy["stack_accuracy"]["max_penalty"])

    score = max(0, base_score - penalty)

    return {
        "score": score,
        "false_claims": list(false_claims),
        "confirmed": list(confirmed),
        "unknown": list(unknown)
    }


def compute_stack_accuracy_v2(claimed_raw, detected_stacks, repo_languages, repo_path, policy):
    """Stack accuracy with proper taxonomy. Languages, frameworks, etc. judged differently."""
    claimed = normalize_claims(claimed_raw)
    
    # Get all confirmed stacks
    confirmed = confirm_stacks(claimed, detected_stacks, repo_languages, repo_path)
    
    false_claims = set()
    unknown = set()

    for c in claimed:
        if c in confirmed:
            continue
        
        category = get_stack_category(c)
        
        if category == "languages":
            # Languages must be confirmed by GitHub stats - false if not
            false_claims.add(c)
        elif category is not None:
            # Known stack type but not confirmed - mark as unknown
            unknown.add(c)
        else:
            # Completely unknown stack - also unknown
            unknown.add(c)

    penalty = len(false_claims) * policy["stack_accuracy"]["false_claim_penalty_per_stack"]
    penalty = min(penalty, policy["stack_accuracy"]["max_penalty"])

    score = max(0, 100 - penalty)

    return {
        "score": score,
        "confirmed": list(confirmed),
        "false_claims": list(false_claims),
        "unknown": list(unknown)
    }


def base_commit_score(commit_count, thresholds):
    """Get base score from commit count thresholds."""
    for t in thresholds:
        if t["min"] <= commit_count <= t["max"]:
            return t["score"]
    return 0


def compute_commit_quality(commit_data, policy):
    """Commit quality score - enforces quality over quantity."""
    thresholds = policy["commit_quality"]["commit_count_thresholds"]
    multipliers = policy["commit_quality"]["quality_multipliers"]
    
    base = base_commit_score(commit_data["commit_count"], thresholds)
    score = base

    if commit_data.get("descriptive_messages"):
        score *= multipliers["descriptive_messages"]

    if commit_data.get("spread_over_time"):
        score *= multipliers["spread_over_time"]

    if commit_data.get("single_massive_commit"):
        score *= multipliers["single_massive_commit"]

    return min(100, int(score))


# =============================================================================
# CODE QUALITY HELPER FUNCTIONS - Engineering hygiene signals
# =============================================================================

def has_modular_structure(repo_path):
    """Check for intentional structure: src, components, utils, services, etc."""
    for root, dirs, _ in os.walk(repo_path):
        if is_ignored(root):
            continue
        if COMMON_MODULE_DIRS.intersection(set(dirs)):
            return True
    return False


def has_config_files(repo_path):
    """Check for config files. Boring, but they matter."""
    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue
        if CONFIG_FILES.intersection(set(files)):
            return True
    return False


def has_reasonable_file_sizes(repo_path, max_lines=800):
    """Check that files aren't monster files. >800 lines is suspicious."""
    large_files = 0
    total_files = 0

    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue
        for f in files:
            if f.endswith((".js", ".ts", ".py", ".jsx", ".tsx")):
                total_files += 1
                try:
                    with open(os.path.join(root, f), "r", errors="ignore") as file:
                        if sum(1 for _ in file) > max_lines:
                            large_files += 1
                except Exception:
                    pass

    if total_files == 0:
        return True  # No code files, pass by default

    # Less than 20% oversized files is acceptable
    return (large_files / total_files) < 0.2


def has_consistent_naming(repo_path):
    """Check for consistent naming. No FinalVersion2.js chaos."""
    bad_names = 0
    checked = 0
    # Allow lowercase, numbers, underscores, hyphens, dots
    pattern = re.compile(r"^[a-z0-9_\-\.]+$")

    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue
        for f in files:
            if f.endswith((".js", ".ts", ".py", ".jsx", ".tsx")):
                checked += 1
                if not pattern.match(f.lower()):
                    bad_names += 1

    if checked == 0:
        return True  # No code files, pass by default

    # Less than 20% bad names is acceptable
    return (bad_names / checked) < 0.2


def compute_code_quality(repo_path, policy):
    """Compute code quality score based on structural signals.
    
    What it is: Structural, deterministic, evidence-based
    What it is not: Style nitpicking, algorithm judging
    """
    if repo_path is None:
        return 0
        
    score = 0
    signals = policy["code_quality"]["structure_signals"]

    if has_modular_structure(repo_path):
        score += signals["modular_folders"]

    if has_config_files(repo_path):
        score += signals["config_files_present"]

    if has_reasonable_file_sizes(repo_path):
        score += signals["reasonable_file_sizes"]

    if has_consistent_naming(repo_path):
        score += signals["consistent_naming"]

    return min(policy["code_quality"]["max_score"], score)


# =============================================================================
# PROJECT DEPTH HELPER FUNCTIONS - Non-trivial effort signals
# =============================================================================

# Keywords indicating error handling
ERROR_KEYWORDS = ["try", "catch", "except", "throw", "raise"]

# Directories indicating data flow architecture
DATA_LAYER_DIRS = {"services", "api", "controllers", "hooks", "utils", "models", "stores"}

# Keywords indicating edge case handling
EDGE_CASE_KEYWORDS = ["if (!", "if not", "return null", "return None", "?? ", "|| null", "|| undefined"]


def loc_depth_score(lines_added, thresholds):
    """Get base depth score from lines of code thresholds."""
    score = 0
    for t in thresholds:
        if lines_added >= t["min"]:
            score = t["score"]
    return score


def has_error_handling(repo_path):
    """Check for error handling: try, catch, except, throw."""
    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue
        for f in files:
            if f.endswith((".js", ".ts", ".py", ".jsx", ".tsx")):
                try:
                    with open(os.path.join(root, f), "r", errors="ignore") as file:
                        content = file.read()
                        if any(k in content for k in ERROR_KEYWORDS):
                            return True
                except Exception:
                    pass
    return False


def has_multiple_modules(repo_path):
    """Check for multiple meaningful folders with code."""
    module_dirs = set()

    for root, dirs, files in os.walk(repo_path):
        if is_ignored(root):
            continue
        if any(f.endswith((".js", ".ts", ".py", ".jsx", ".tsx")) for f in files):
            module_dirs.add(root)

    return len(module_dirs) >= 3


def has_data_layers(repo_path):
    """Check for data flow layer patterns: services, api, controllers, hooks, utils."""
    for root, dirs, _ in os.walk(repo_path):
        if is_ignored(root):
            continue
        if DATA_LAYER_DIRS.intersection(set(dirs)):
            return True
    return False


def has_edge_case_handling(repo_path):
    """Check for guard logic and edge case handling."""
    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue
        for f in files:
            if f.endswith((".js", ".ts", ".py", ".jsx", ".tsx")):
                try:
                    with open(os.path.join(root, f), "r", errors="ignore") as file:
                        content = file.read()
                        if any(k in content for k in EDGE_CASE_KEYWORDS):
                            return True
                except Exception:
                    pass
    return False


def compute_project_depth(repo_path, contribution, policy):
    """Compute project depth score based on sustained effort and architecture.
    
    Measures: Sustained effort, architectural intent, feature breadth
    Does not measure: Code beauty, clever algorithms, LOC vanity
    """
    if repo_path is None or contribution is None:
        return 0
    
    depth_policy = policy["project_depth"]
    
    # Base score from LOC
    score = loc_depth_score(
        contribution["lines_added"],
        depth_policy["loc_thresholds"]
    )

    features = depth_policy["feature_indicators"]

    if has_error_handling(repo_path):
        score += features["error_handling"]

    if has_multiple_modules(repo_path):
        score += features["multiple_modules"]

    if has_data_layers(repo_path):
        score += features["data_flow_layers"]

    if has_edge_case_handling(repo_path):
        score += features["edge_case_handling"]

    return min(depth_policy["max_score"], score)


# =============================================================================
# DOCUMENTATION HELPER FUNCTIONS - Communication intent signals
# =============================================================================

# Keywords indicating setup instructions
SETUP_KEYWORDS = ["install", "setup", "npm", "pip", "yarn", "run", "getting started", "quick start"]

# Keywords indicating usage examples
USAGE_KEYWORDS = ["usage", "example", "demo", "how to", "tutorial", "guide"]


def readme_exists(repo_path):
    """Check if README exists."""
    try:
        return any(
            f.lower().startswith("readme")
            for f in os.listdir(repo_path)
        )
    except Exception:
        return False


def load_readme(repo_path):
    """Read README content once for reuse."""
    try:
        for f in os.listdir(repo_path):
            if f.lower().startswith("readme"):
                try:
                    with open(os.path.join(repo_path, f), "r", errors="ignore") as file:
                        return file.read().lower()
                except Exception:
                    pass
    except Exception:
        pass
    return ""


def has_setup_instructions(readme):
    """Check for setup/install instructions."""
    return any(k in readme for k in SETUP_KEYWORDS)


def has_tech_stack_section(readme, claimed_stacks):
    """Check if claimed stacks are mentioned in README."""
    for stack in claimed_stacks:
        if stack.lower() in readme:
            return True
    return False


def has_usage_examples(readme):
    """Check for usage examples or demos."""
    return any(k in readme for k in USAGE_KEYWORDS)


def has_visuals(readme):
    """Check for screenshots or diagrams (markdown images)."""
    return (
        "![" in readme or 
        ".png" in readme or 
        ".jpg" in readme or 
        ".gif" in readme or
        ".svg" in readme or
        "screenshot" in readme or
        "diagram" in readme
    )


def compute_documentation(repo_path, claimed_stacks, policy):
    """Compute documentation score based on communication intent.
    
    Measures: Did they explain? Can someone else run this? Is intent visible?
    Does not measure: Writing style, length, marketing polish
    """
    if repo_path is None:
        return 0
    
    doc_policy = policy["documentation"]
    signals = doc_policy["signals"]
    score = 0

    if not readme_exists(repo_path):
        return 0

    readme = load_readme(repo_path)

    # README exists
    score += signals["readme_exists"]

    # Setup instructions present
    if has_setup_instructions(readme):
        score += signals["setup_instructions"]

    # Tech stack documented
    if has_tech_stack_section(readme, claimed_stacks):
        score += signals["tech_stack_documented"]

    # Usage examples present
    if has_usage_examples(readme):
        score += signals["usage_examples"]

    # Screenshots or diagrams
    if has_visuals(readme):
        score += signals["screenshots_or_diagrams"]

    return min(doc_policy["max_score"], score)


def compute_confidence(stack_result, policy):
    """Compute confidence based on evidence completeness.
    
    Confidence is not a feeling. It is math.
    - Confirmed stacks increase confidence
    - Unknown stacks reduce confidence
    - False claims reduce confidence more
    - Never hits 0 or 1
    """
    conf_policy = policy["confidence"]
    confidence = conf_policy["base"]

    confidence += len(stack_result["confirmed"]) * conf_policy["confirmed_stack_bonus"]
    confidence -= len(stack_result["unknown"]) * conf_policy["unknown_stack_penalty"]
    confidence -= len(stack_result["false_claims"]) * conf_policy["false_claim_penalty"]

    confidence = max(conf_policy["min"], min(conf_policy["max"], confidence))
    return round(confidence, 2)


def compute_final_score(scores, weights):
    """Compute final weighted score - the heart of the system."""
    total = 0
    for key, weight in weights.items():
        total += scores[key] * weight
    return round(total, 2)


# =============================================================================
# REPO ANALYSIS FUNCTIONS
# =============================================================================

def is_ignored(file_path):
    """Check if a file path should be ignored."""
    return any(ignored in file_path for ignored in IGNORED_PATHS)


def clone_repo(repo_url, local_path):
    """Clone a repo locally to get full commit history."""
    if not os.path.exists(local_path):
        Repo.clone_from(repo_url, local_path)
    return Repo(local_path)


def get_user_commits(repo, github_username, known_emails=None):
    """Filter commits by username - tightened identity matching.
    
    A commit belongs to the user only if:
    - commit.author.name matches github_username
    - OR commit.author.email matches one of the user's known emails
    """
    user_commits = []

    for commit in repo.iter_commits():
        author_name = commit.author.name.lower()
        author_email = commit.author.email.lower()

        if github_username.lower() in author_name:
            user_commits.append(commit)
        elif known_emails and author_email in known_emails:
            user_commits.append(commit)

    return user_commits


def analyze_user_contributions(commits):
    """Count files and lines written by the user - raw evidence.
    Excludes generated and dependency code."""
    files_touched = set()
    lines_added = 0
    lines_deleted = 0

    for commit in commits:
        for file in commit.stats.files:
            if is_ignored(file):
                continue
            files_touched.add(file)
            lines_added += commit.stats.files[file]["insertions"]
            lines_deleted += commit.stats.files[file]["deletions"]

    return {
        "files_touched": list(files_touched),
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "commit_count": len(commits)
    }


def normalize_contribution(stats):
    """Normalize stats - raw numbers lie, normalized numbers explain."""
    commits = stats["commit_count"] or 1

    return {
        "avg_lines_per_commit": round(stats["lines_added"] / commits, 1),
        "avg_files_per_commit": round(len(stats["files_touched"]) / commits, 1)
    }


def detect_stacks(repo_path):
    """Detect stacks honestly - not perfect, but honest."""
    detected = set()

    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue

        for file in files:
            file_lower = file.lower()
            full_path = os.path.join(root, file)
            
            for stack, signatures in STACK_SIGNATURES.items():
                for sig in signatures:
                    if sig.lower() in file_lower:
                        detected.add(stack)
                    # Also check file contents for package.json
                    elif file == "package.json" and sig != "package.json":
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                content = f.read().lower()
                                if sig.lower() in content:
                                    detected.add(stack)
                        except:
                            pass

    return list(detected)


def get_repo_languages(repo_owner, repo_name):
    """Detect languages at repo level - honest detection."""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/languages"
    response = requests.get(url)
    return response.json()


def parse_repo_url(repo_url):
    """Extract owner and repo name from GitHub URL."""
    # Handle both https://github.com/owner/repo and https://github.com/owner/repo.git
    parts = repo_url.rstrip('/').rstrip('.git').split('/')
    repo_name = parts[-1]
    repo_owner = parts[-2]
    return repo_owner, repo_name


if __name__ == "__main__":
    repo_url = input("Repo URL: ")
    github_username = input("GitHub Username: ")
    claimed_stacks_input = input("Claimed stacks (comma-separated, or leave empty): ")
    claimed_stacks = [s.strip() for s in claimed_stacks_input.split(",") if s.strip()]

    # Load policy
    policy = load_policy()
    print(f"\nPolicy version: {policy['version']}")

    local_path = "./temp_repo"
    repo = clone_repo(repo_url, local_path)

    commits = get_user_commits(repo, github_username)
    contribution = analyze_user_contributions(commits)
    normalized = normalize_contribution(contribution)

    # Get languages
    repo_owner, repo_name = parse_repo_url(repo_url)
    languages = get_repo_languages(repo_owner, repo_name)

    # Detect stacks
    stacks = detect_stacks(local_path)

    print("\nUser Contribution Summary")
    print("-------------------------")
    print("Commits:", contribution["commit_count"])
    print("Files touched:", len(contribution["files_touched"]))
    print("Lines added:", contribution["lines_added"])
    print("Lines deleted:", contribution["lines_deleted"])
    print("Avg lines/commit:", normalized["avg_lines_per_commit"])
    print("Avg files/commit:", normalized["avg_files_per_commit"])
    
    print("\nDetected stacks:")
    for stack in sorted(stacks):
        print(f"- {stack}")
    
    print("\nRepo Languages:")
    for lang, bytes_count in languages.items():
        print(f"- {lang}: {bytes_count} bytes")

    # ==========================================================================
    # SCORING
    # ==========================================================================
    
    # Stack Accuracy Score (v2 - with proper taxonomy)
    stack_result = compute_stack_accuracy_v2(
        claimed_stacks, stacks, languages, local_path, policy
    )
    
    # Compute confidence based on stack evidence
    confidence = compute_confidence(stack_result, policy)
    
    # Commit Quality Score
    commit_data = {
        "commit_count": contribution["commit_count"],
        "avg_lines_per_commit": normalized["avg_lines_per_commit"],
        "descriptive_messages": False,  # TODO: analyze later
        "spread_over_time": False,       # TODO: analyze later
        "single_massive_commit": False   # TODO: analyze later
    }
    commit_quality_score = compute_commit_quality(commit_data, policy)
    
    # Code Quality Score - structural hygiene
    code_quality_score = compute_code_quality(local_path, policy)
    
    # Project Depth Score - non-trivial effort
    project_depth_score = compute_project_depth(local_path, contribution, policy)
    
    # Documentation Score - communication intent
    documentation_score = compute_documentation(local_path, claimed_stacks, policy)
    
    # Collect all scores
    scores = {
        "stack_accuracy": stack_result["score"],
        "commit_quality": commit_quality_score,
        "code_quality": code_quality_score,
        "project_depth": project_depth_score,
        "documentation": documentation_score
    }
    
    # Compute final score
    final_score = compute_final_score(scores, policy["final_score_weights"])
    
    # Print score breakdown
    print("\n" + "=" * 40)
    print("Score Breakdown")
    print("-" * 40)
    print(f"Stack Accuracy: {scores['stack_accuracy']}")
    if stack_result["confirmed"]:
        print(f"  ✓ Confirmed: {', '.join(stack_result['confirmed'])}")
    if stack_result["false_claims"]:
        print(f"  ✗ False claims: {', '.join(stack_result['false_claims'])}")
    if stack_result["unknown"]:
        print(f"  ? Unknown: {', '.join(stack_result['unknown'])}")
    print(f"Commit Quality: {scores['commit_quality']}")
    print(f"Code Quality: {scores['code_quality']}")
    print(f"Project Depth: {scores['project_depth']}")
    print(f"Documentation: {scores['documentation']}")
    print("-" * 40)
    print(f"Final Score: {final_score}")
    print(f"Confidence: {confidence}")
    
    # Human-readable confidence interpretation
    if confidence >= 0.80:
        conf_text = "High - Strong evidence for claimed technologies"
    elif confidence >= 0.60:
        conf_text = "Medium - Some claims could not be conclusively verified"
    else:
        conf_text = "Low - Limited evidence or false claims detected"
    print(f"  ({conf_text})")
    print("=" * 40)
