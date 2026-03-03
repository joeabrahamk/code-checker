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

# Code file extensions for sampling
CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go",
    ".rb", ".php", ".rs", ".swift", ".kt", ".html", ".css"
}

# Resume parsing aliases (normalization)
RESUME_ALIASES = {
    "node js": "node.js",
    "nodejs": "node.js",
    "reactjs": "react",
    "nextjs": "next.js",
    "postgres": "postgresql",
    "js": "javascript",
    "ts": "typescript",
    "c sharp": "c#",
    "csharp": "c#",
    "golang": "go"
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


def canonical_stack_name(stack_name):
    """Map stack aliases to canonical display names."""
    if not stack_name:
        return stack_name
    lower = stack_name.strip().lower()
    lower = RESUME_ALIASES.get(lower, lower)
    for category, stacks in STACK_CATEGORIES.items():
        if lower in stacks:
            return stacks[lower]
    return stack_name.strip()


def extract_resume_text(resume_path):
    """Extract text from a resume file (PDF or text)."""
    if not resume_path:
        return ""
    if not os.path.exists(resume_path):
        print(f"Warning: resume not found at {resume_path}")
        return ""

    ext = os.path.splitext(resume_path)[1].lower()
    if ext == ".pdf":
        try:
            from pdfminer.high_level import extract_text  # type: ignore
            return extract_text(resume_path) or ""
        except Exception as exc:
            print(f"Warning: PDF parse failed ({exc}). Falling back to manual input.")
            return ""

    try:
        with open(resume_path, "r", encoding="utf-8", errors="ignore") as file:
            return file.read()
    except Exception as exc:
        print(f"Warning: resume read failed ({exc}).")
        return ""


def extract_claimed_stacks_from_resume(resume_text):
    """Extract claimed stacks from resume text via keyword matching."""
    if not resume_text:
        return []

    text = resume_text.lower()
    found = set()

    for category, stacks in STACK_CATEGORIES.items():
        for key, display in stacks.items():
            if key in text or display.lower() in text:
                found.add(display)

    for alias, target in RESUME_ALIASES.items():
        if alias in text:
            found.add(canonical_stack_name(target))

    return sorted(found)


def extract_github_urls_from_text(text):
    """Extract GitHub repository URLs from text."""
    if not text:
        return []
    urls = re.findall(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", text)
    return sorted(set(urls))


def build_stack_queries(claimed_stacks):
    """Build natural language queries for GraphCodeBERT similarity scoring."""
    queries = {}
    for raw in claimed_stacks:
        lower = raw.strip().lower()
        lower = RESUME_ALIASES.get(lower, lower)

        if lower in ["react", "next.js", "next", "vue", "angular", "svelte"]:
            queries[lower] = f"{canonical_stack_name(lower)} component using UI framework patterns and components"
        elif lower in ["node.js", "node", "express", "nestjs"]:
            queries[lower] = "Node.js server code using modules, APIs, and backend routing"
        elif lower in ["python", "java", "javascript", "typescript", "go", "rust", "php", "ruby", "c#", "swift", "kotlin"]:
            queries[lower] = f"{canonical_stack_name(lower)} source code with functions, classes, and program logic"
        elif lower in ["postgresql", "mongodb", "mysql"]:
            queries[lower] = f"{canonical_stack_name(lower)} database integration or query code"
        else:
            queries[lower] = f"{canonical_stack_name(lower)} related code implementation"

    return queries


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


def compute_skill_assessment(claimed_stacks, stack_result, graphcodebert_scores, policy):
    """Assess claimed stacks with a score and short remark."""
    if not claimed_stacks:
        return []

    gcb_policy = policy.get("graphcodebert", {})
    score_policy = gcb_policy.get("skill_score", {})
    independent_only = score_policy.get("independent_only", True)
    confirmed_weight = score_policy.get("confirmed_weight", 0.6)
    similarity_weight = score_policy.get("similarity_weight", 0.4)
    knows_threshold = score_policy.get("knows_threshold", 55)

    remark_thresholds = score_policy.get("remarks", {})
    strong = remark_thresholds.get("strong", 80)
    moderate = remark_thresholds.get("moderate", 60)
    weak = remark_thresholds.get("weak", 40)

    confirmed_set = {c.lower() for c in stack_result.get("confirmed", [])}
    results = []

    for raw in claimed_stacks:
        lower = RESUME_ALIASES.get(raw.lower(), raw.lower())
        display = canonical_stack_name(lower)
        confirmed = lower in confirmed_set
        gcb = graphcodebert_scores.get(lower, {}) if graphcodebert_scores else {}
        similarity = gcb.get("similarity", 0.0)
        independent_score = gcb.get("independent_score")

        if independent_only:
            score = independent_score if independent_score is not None else round(similarity * 100, 1)
        else:
            score = (confirmed_weight * (100 if confirmed else 0)) + (similarity_weight * similarity * 100)
        score = max(0, min(100, round(score, 1)))

        if score >= strong:
            remark = "Strong evidence in code"
        elif score >= moderate:
            remark = "Moderate evidence; likely proficient"
        elif score >= weak:
            remark = "Some evidence, but limited depth"
        else:
            remark = "Weak evidence for this claim"

        knows = score >= knows_threshold

        results.append({
            "stack": display,
            "knows": knows,
            "score": score,
            "remark": remark,
            "evidence": {
                "confirmed": confirmed,
                "graphcodebert_similarity": similarity,
                "graphcodebert_independent_score": independent_score,
                "best_file": gcb.get("best_file")
            }
        })

    return results


def build_graphcodebert_stack_scores(claimed_stacks, gcb_scores):
    """Build normalized per-stack independent GraphCodeBERT scores for reporting."""
    if not claimed_stacks:
        return []

    rows = []
    for raw in claimed_stacks:
        lower = RESUME_ALIASES.get(raw.lower(), raw.lower())
        display = canonical_stack_name(lower)
        gcb = gcb_scores.get(lower, {}) if gcb_scores else {}
        similarity = gcb.get("similarity", 0.0)
        independent_score = gcb.get("independent_score")
        if independent_score is None:
            independent_score = round(similarity * 100, 1)

        rows.append({
            "stack": display,
            "independent_score": round(float(independent_score), 1),
            "similarity": round(float(similarity), 4),
            "evidence_strength": gcb.get("evidence_strength", "none"),
            "best_file": gcb.get("best_file"),
            "matched_files": gcb.get("matched_files", [])
        })

    rows.sort(key=lambda x: x["independent_score"], reverse=True)
    return rows


# =============================================================================
# REPO ANALYSIS FUNCTIONS
# =============================================================================

def is_ignored(file_path):
    """Check if a file path should be ignored."""
    return any(ignored in file_path for ignored in IGNORED_PATHS)


def clone_repo(repo_url, local_path, max_retries=3):
    """Clone a repo locally with retry logic for network failures."""
    if os.path.exists(local_path):
        try:
            return Repo(local_path)
        except Exception as exc:
            print(f"  Warning: Existing repo at {local_path} is corrupted ({exc}). Retrying clone...")
            import shutil
            shutil.rmtree(local_path, ignore_errors=True)

    for attempt in range(max_retries):
        try:
            print(f"  Cloning {repo_url}... (attempt {attempt + 1}/{max_retries})")
            Repo.clone_from(repo_url, local_path)
            return Repo(local_path)
        except Exception as exc:
            if "Connection was reset" in str(exc) or "RPC failed" in str(exc):
                if attempt < max_retries - 1:
                    print(f"  ⚠️  Network error. Retrying in 3 seconds...")
                    import time
                    time.sleep(3)
                    continue
                else:
                    raise RuntimeError(
                        f"Failed to clone {repo_url} after {max_retries} attempts (network issue). "
                        f"Try again later or clone manually to {local_path}."
                    )
            else:
                raise RuntimeError(f"Failed to clone {repo_url}: {exc}")

    raise RuntimeError(f"Unexpected: Failed to clone {repo_url}")


def open_local_repo(local_path):
    """Open an existing local repository if possible."""
    try:
        return Repo(local_path)
    except Exception:
        return None


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


def sample_code_files(repo_path, max_files=5, max_chars=2000):
    """Select representative code files for GraphCodeBERT scoring."""
    candidates = []

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
            if filename.lower() in CONFIG_FILES:
                continue

            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            lines = content.count("\n") + 1
            if lines < 10:
                continue

            rel_path = filepath.replace(repo_path, "").lower()
            priority = 0
            for pattern in priority_patterns:
                if pattern in rel_path:
                    priority += 10

            if 50 <= lines <= 200:
                priority += 5

            candidates.append({
                "path": rel_path.lstrip("/\\"),
                "content": content[:max_chars],
                "lines": lines,
                "priority": priority
            })

    candidates.sort(key=lambda x: (x["priority"], x["lines"]), reverse=True)
    return candidates[:max_files]


def _stack_file_hints(stack_name):
    """Return file extension and path hints for stack-specific sampling."""
    stack = RESUME_ALIASES.get(stack_name.lower(), stack_name.lower())

    hints = {
        "python": {
            "extensions": {".py"},
            "path_keywords": ["python", "backend", "api", "service", "model"]
        },
        "javascript": {
            "extensions": {".js", ".jsx", ".mjs", ".cjs"},
            "path_keywords": ["frontend", "client", "component", "ui", "web"]
        },
        "typescript": {
            "extensions": {".ts", ".tsx"},
            "path_keywords": ["frontend", "client", "component", "ui", "web"]
        },
        "react": {
            "extensions": {".jsx", ".tsx", ".js", ".ts"},
            "path_keywords": ["component", "components", "hooks", "pages", "react"]
        },
        "go": {
            "extensions": {".go"},
            "path_keywords": ["go", "golang"]
        },
        "java": {
            "extensions": {".java"},
            "path_keywords": ["java", "spring", "src/main"]
        },
        "sql": {
            "extensions": {".sql"},
            "path_keywords": ["sql", "migration", "query", "db", "database"]
        },
        "docker": {
            "extensions": {".dockerfile"},
            "path_keywords": ["docker", "container"]
        },
        "node.js": {
            "extensions": {".js", ".ts", ".mjs", ".cjs"},
            "path_keywords": ["server", "backend", "api", "routes", "express", "node"]
        }
    }

    return hints.get(stack, {
        "extensions": set(),
        "path_keywords": [stack]
    })


def _filter_samples_for_stack(code_samples, stack_name):
    """Filter representative samples to files likely belonging to a specific stack."""
    hints = _stack_file_hints(stack_name)
    extensions = hints.get("extensions", set())
    keywords = hints.get("path_keywords", [])

    selected = []
    for sample in code_samples:
        path = sample.get("path", "").lower()
        ext = os.path.splitext(path)[1].lower()
        path_hit = any(keyword in path for keyword in keywords)
        ext_hit = ext in extensions if extensions else False

        if ext_hit or path_hit:
            selected.append(sample)

    return selected


def compute_graphcodebert_scores(repo_path, claimed_stacks, policy):
    """Compute GraphCodeBERT similarity scores for claimed stacks."""
    gcb_policy = policy.get("graphcodebert", {})
    if not gcb_policy.get("enabled", True):
        return {}, "GraphCodeBERT disabled by policy"

    max_files = gcb_policy.get("max_files", 5)
    max_chars = gcb_policy.get("max_chars_per_file", 2000)

    # Build a broader candidate pool first, then filter per stack.
    candidate_pool_size = max(max_files * 8, 40)
    samples = sample_code_files(repo_path, max_files=candidate_pool_size, max_chars=max_chars)
    if not samples:
        return {}, "No suitable code samples for GraphCodeBERT"

    query_map = build_stack_queries(claimed_stacks)
    if not query_map:
        return {}, "No stack queries for GraphCodeBERT"

    try:
        from graphcodebert_scoring import score_stacks_with_graphcodebert
        scores = {}

        for raw in claimed_stacks:
            stack_key = RESUME_ALIASES.get(raw.lower(), raw.lower())
            query = query_map.get(stack_key)
            if not query:
                continue

            filtered_samples = _filter_samples_for_stack(samples, stack_key)
            if not filtered_samples:
                scores[stack_key] = {
                    "similarity": 0.0,
                    "best_file": None,
                    "independent_score": 0.0,
                    "evidence_strength": "none",
                    "matched_files": [],
                    "matched_similarities": []
                }
                continue

            stack_scores, error = score_stacks_with_graphcodebert(filtered_samples, {stack_key: query})
            if error:
                return {}, error

            scores[stack_key] = stack_scores.get(stack_key, {
                "similarity": 0.0,
                "best_file": None,
                "independent_score": 0.0,
                "evidence_strength": "none",
                "matched_files": [],
                "matched_similarities": []
            })

        return scores, None
    except Exception as exc:
        return {}, f"GraphCodeBERT import failed: {exc}"


def get_repo_languages(repo_owner, repo_name, max_retries=3):
    """Detect languages at repo level - honest detection.
    
    Includes retry logic for network issues.
    Falls back to empty dict if API fails.
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/languages"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print("  Warning: GitHub API rate limit reached. Using local detection only.")
                return {}
            elif response.status_code == 404:
                print(f"  Warning: Repository not found on GitHub API.")
                return {}
            else:
                print(f"  Warning: GitHub API returned status {response.status_code}")
                return {}
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                print(f"  Connection error, retrying ({attempt + 1}/{max_retries})...")
                import time
                time.sleep(2)  # Wait before retry
            else:
                print("  Warning: Could not connect to GitHub API. Using local detection only.")
                return {}
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"  Timeout, retrying ({attempt + 1}/{max_retries})...")
            else:
                print("  Warning: GitHub API timeout. Using local detection only.")
                return {}
        except Exception as e:
            print(f"  Warning: GitHub API error: {e}")
            return {}
    
    return {}


def detect_languages_locally(repo_path):
    """Fallback: Detect languages from file extensions when API fails."""
    extension_to_language = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".html": "HTML",
        ".htm": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".sass": "SASS",
        ".json": "JSON",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C",
        ".cs": "C#",
        ".go": "Go",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".rs": "Rust",
        ".md": "Markdown"
    }
    
    language_bytes = {}
    
    for root, _, files in os.walk(repo_path):
        if is_ignored(root):
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in extension_to_language:
                lang = extension_to_language[ext]
                try:
                    file_size = os.path.getsize(os.path.join(root, f))
                    language_bytes[lang] = language_bytes.get(lang, 0) + file_size
                except:
                    pass
    
    return language_bytes


def parse_repo_url(repo_url):
    """Extract owner and repo name from GitHub URL."""
    # Handle both https://github.com/owner/repo and https://github.com/owner/repo.git
    parts = repo_url.rstrip('/').rstrip('.git').split('/')
    repo_name = parts[-1]
    repo_owner = parts[-2]
    return repo_owner, repo_name


def evaluate_repo(repo_url, local_path, github_username, claimed_stacks, policy):
    """Evaluate a repo and return evaluation payload + skill assessment."""
    repo = None
    try:
        if repo_url:
            repo = clone_repo(repo_url, local_path)
        else:
            repo = open_local_repo(local_path)
    except RuntimeError as exc:
        print(f"\n❌ Clone failed: {exc}")
        print(f"   Would you like to:")
        print(f"   1. Try again manually: git clone {repo_url} {local_path}")
        print(f"   2. Use an existing local repo at {local_path}")
        skip = input("\nSkip this repo and continue? (y/n): ").lower() == "y"
        if not skip:
            raise
        repo = open_local_repo(local_path)
        if repo is None:
            print(f"   No local repo found at {local_path}. Skipping...")
            return None

    if repo is None:
        contribution = {
            "files_touched": [],
            "lines_added": 0,
            "lines_deleted": 0,
            "commit_count": 0
        }
        normalized = {
            "avg_lines_per_commit": 0,
            "avg_files_per_commit": 0
        }
    else:
        commits = get_user_commits(repo, github_username)
        contribution = analyze_user_contributions(commits)
        normalized = normalize_contribution(contribution)

    # Language detection
    languages = {}
    if repo_url:
        try:
            repo_owner, repo_name = parse_repo_url(repo_url)
            print("\nFetching language stats...")
            languages = get_repo_languages(repo_owner, repo_name)
        except Exception:
            pass

    if not languages:
        print("  Using local file extension detection...")
        languages = detect_languages_locally(local_path)

    # Detect stacks
    stacks = detect_stacks(local_path)

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
        "descriptive_messages": False,
        "spread_over_time": False,
        "single_massive_commit": False
    }
    commit_quality_score = compute_commit_quality(commit_data, policy)

    # Code Quality Score - structural hygiene
    code_quality_score = compute_code_quality(local_path, policy)

    # Project Depth Score - non-trivial effort
    project_depth_score = compute_project_depth(local_path, contribution, policy)

    # Documentation Score - communication intent
    documentation_score = compute_documentation(local_path, claimed_stacks, policy)

    # GraphCodeBERT quality scoring
    graphcodebert_quality_score = 0
    graphcodebert_quality_details = {}
    gcb_quality_error = None
    
    gcb_quality_policy = policy.get("graphcodebert", {}).get("quality_scoring", {})
    if gcb_quality_policy.get("enabled"):
        try:
            from graphcodebert_quality_scorer import score_code_quality
            code_samples = sample_code_files(local_path, max_files=gcb_quality_policy.get("max_files", 10))
            if code_samples:
                quality_result = score_code_quality(code_samples, claimed_stacks, policy)
                if quality_result:
                    graphcodebert_quality_score = quality_result.get("overall_score", 0)
                    graphcodebert_quality_details = quality_result
                    print(f"  GraphCodeBERT Quality Score: {graphcodebert_quality_score}")
        except Exception as e:
            gcb_quality_error = str(e)
            print(f"  GraphCodeBERT quality scoring disabled: {e}")

    scores = {
        "stack_accuracy": stack_result["score"],
        "commit_quality": commit_quality_score,
        "code_quality": code_quality_score,
        "project_depth": project_depth_score,
        "documentation": documentation_score,
        "graphcodebert_quality": graphcodebert_quality_score
    }

    final_score = compute_final_score(scores, policy["final_score_weights"])

    # GraphCodeBERT scoring + skill assessment
    gcb_scores, gcb_error = compute_graphcodebert_scores(local_path, claimed_stacks, policy)
    skill_assessment = compute_skill_assessment(claimed_stacks, stack_result, gcb_scores, policy)
    graphcodebert_stack_scores = build_graphcodebert_stack_scores(claimed_stacks, gcb_scores)

    evaluation_payload = {
        "evaluation_summary": {
            "final_score": final_score,
            "confidence": confidence,
            "scores": scores
        },
        "stack_analysis": {
            "claimed": claimed_stacks,
            "confirmed": stack_result["confirmed"],
            "false_claims": stack_result["false_claims"],
            "unknown": stack_result["unknown"]
        },
        "repo_evidence": {
            "languages": languages,
            "commits": contribution["commit_count"],
            "lines_added": contribution["lines_added"],
            "lines_deleted": contribution["lines_deleted"],
            "files_touched": len(contribution["files_touched"]),
            "avg_lines_per_commit": normalized["avg_lines_per_commit"],
            "avg_files_per_commit": normalized["avg_files_per_commit"],
            "modular_structure": has_modular_structure(local_path),
            "config_files": has_config_files(local_path),
            "error_handling": has_error_handling(local_path),
            "readme_exists": readme_exists(local_path)
        },
        "detected_stacks": stacks,
        "graphcodebert": {
            "scores": gcb_scores,
            "stack_independent_scores": graphcodebert_stack_scores,
            "error": gcb_error,
            "quality_analysis": graphcodebert_quality_details,
            "quality_error": gcb_quality_error
        },
        "skill_assessment": skill_assessment
    }

    return {
        "repo_url": repo_url,
        "local_path": local_path,
        "evaluation": evaluation_payload,
        "graphcodebert": {
            "scores": gcb_scores,
            "stack_independent_scores": graphcodebert_stack_scores,
            "error": gcb_error
        },
        "skill_assessment": skill_assessment
    }


if __name__ == "__main__":
    resume_path = input("Resume path (optional, pdf/txt): ").strip()
    resume_text = extract_resume_text(resume_path)
    resume_claimed = extract_claimed_stacks_from_resume(resume_text)
    resume_repo_urls = extract_github_urls_from_text(resume_text)

    repo_urls_input = input("Repo URL(s) (comma-separated, optional): ").strip()
    if repo_urls_input:
        repo_urls = [r.strip() for r in repo_urls_input.split(",") if r.strip()]
    elif resume_repo_urls:
        repo_urls = resume_repo_urls
    else:
        repo_urls = []

    github_username = input("GitHub Username: ")
    claimed_stacks_input = input("Claimed stacks (comma-separated, or leave empty to use resume): ")
    claimed_stacks = [s.strip() for s in claimed_stacks_input.split(",") if s.strip()]

    if resume_claimed:
        if claimed_stacks:
            claimed_stacks = sorted(set(claimed_stacks + resume_claimed))
        else:
            claimed_stacks = resume_claimed

    claimed_stacks = [canonical_stack_name(s) for s in claimed_stacks]

    # Load policy
    policy = load_policy()
    print(f"\nPolicy version: {policy['version']}")

    if not repo_urls:
        print("No repo URLs provided; using local ./temp_repo")
        repo_urls = [""]

    repo_results = []
    combined_confirmed = set()
    combined_gcb_scores = {}

    for repo_url in repo_urls:
        if repo_url:
            _, repo_name = parse_repo_url(repo_url)
            local_path = os.path.join("./temp_repo", repo_name)
            print(f"\nAnalyzing repo: {repo_url}")
        else:
            local_path = "./temp_repo"
            print("\nAnalyzing local repo: ./temp_repo")

        try:
            result = evaluate_repo(repo_url or None, local_path, github_username, claimed_stacks, policy)
        except RuntimeError as exc:
            print(f"❌ Skipped repo due to error: {exc}")
            continue

        if result is None:
            print("⏭️  Skipped (no local repo and clone failed)")
            continue

        repo_results.append(result)

        confirmed = {c.lower() for c in result["evaluation"]["stack_analysis"]["confirmed"]}
        combined_confirmed |= confirmed

        for stack, gcb in result["graphcodebert"]["scores"].items():
            if stack not in combined_gcb_scores or gcb["similarity"] > combined_gcb_scores[stack]["similarity"]:
                combined_gcb_scores[stack] = gcb

        # Print summary per repo
        scores = result["evaluation"]["evaluation_summary"]["scores"]
        print("\n" + "=" * 40)
        print("Score Breakdown")
        print("-" * 40)
        print(f"Stack Accuracy: {scores['stack_accuracy']}")
        if result["evaluation"]["stack_analysis"]["confirmed"]:
            print(f"  ✓ Confirmed: {', '.join(result['evaluation']['stack_analysis']['confirmed'])}")
        if result["evaluation"]["stack_analysis"]["false_claims"]:
            print(f"  ✗ False claims: {', '.join(result['evaluation']['stack_analysis']['false_claims'])}")
        if result["evaluation"]["stack_analysis"]["unknown"]:
            print(f"  ? Unknown: {', '.join(result['evaluation']['stack_analysis']['unknown'])}")
        print(f"Commit Quality: {scores['commit_quality']}")
        print(f"Code Quality: {scores['code_quality']}")
        print(f"Project Depth: {scores['project_depth']}")
        print(f"Documentation: {scores['documentation']}")
        if result["evaluation"]["graphcodebert"].get("stack_independent_scores"):
            print("GraphCodeBERT Stack Scores:")
            for row in result["evaluation"]["graphcodebert"]["stack_independent_scores"]:
                print(f"  - {row['stack']}: {row['independent_score']} ({row['evidence_strength']})")
        print("-" * 40)
        print(f"Final Score: {result['evaluation']['evaluation_summary']['final_score']}")
        print(f"Confidence: {result['evaluation']['evaluation_summary']['confidence']}")
        print("=" * 40)

    if not repo_results:
        print("\n❌ No repos were successfully evaluated. Exiting.")
        import sys
        sys.exit(1)

    combined_stack_result = {
        "confirmed": list(combined_confirmed)
    }
    combined_skill_assessment = compute_skill_assessment(
        claimed_stacks, combined_stack_result, combined_gcb_scores, policy
    )

    if combined_skill_assessment:
        print("\nSkill Assessment")
        print("-" * 40)
        for item in combined_skill_assessment:
            status = "Yes" if item["knows"] else "No"
            print(f"{item['stack']}: {status} | Score: {item['score']} | {item['remark']}")

    primary_evaluation = repo_results[0]["evaluation"]
    
    # Flatten multi-repo results to avoid circular references
    multi_repo_summary = []
    for result in repo_results:
        multi_repo_summary.append({
            "repo_url": result["repo_url"],
            "local_path": result["local_path"],
            "final_score": result["evaluation"]["evaluation_summary"]["final_score"],
            "confidence": result["evaluation"]["evaluation_summary"]["confidence"],
            "scores": result["evaluation"]["evaluation_summary"]["scores"],
            "confirmed_stacks": result["evaluation"]["stack_analysis"]["confirmed"],
            "false_claims": result["evaluation"]["stack_analysis"]["false_claims"]
        })
    
    primary_evaluation["multi_repo_summary"] = multi_repo_summary
    primary_evaluation["combined_skill_assessment"] = combined_skill_assessment
    primary_evaluation["resume_evidence"] = {
        "path": resume_path,
        "extracted_claims": resume_claimed,
        "extracted_repos": resume_repo_urls
    }

    # Save evaluation payload to JSON file for AI audit
    import json
    with open("evaluation_result.json", "w") as f:
        json.dump(primary_evaluation, f, indent=2)

    print("\n✓ Evaluation saved to evaluation_result.json")
    print("  Run 'python ai_audit.py' for AI analysis")
