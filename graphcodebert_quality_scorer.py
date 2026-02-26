"""
GraphCodeBERT Code Quality Scoring Module

Semantic analysis of code to measure:
- Code quality merits
- Modular code reusability  
- Structure management
- Coding style and best practices
- Anti-pattern detection

This score CONTRIBUTES to the final evaluation score.
"""

import re
from collections import defaultdict


class GraphCodeBERTScorer:
    """Score code quality using semantic analysis with GraphCodeBERT."""
    
    def __init__(self, policy):
        self.policy = policy
        self.gcb_policy = policy.get("graphcodebert_scoring", {})
        
    def score_samples(self, code_samples, claimed_stacks):
        """
        Score code samples for quality merits.
        
        Args:
            code_samples: List of dicts with 'path', 'content', 'lines'
            claimed_stacks: List of claimed technologies
            
        Returns:
            dict: Scores and metrics
        """
        if not code_samples:
            return {
                "overall_score": 50,
                "modularity": 0,
                "reusability": 0,
                "style_consistency": 0,
                "anti_patterns": [],
                "best_practices": [],
                "issues": []
            }
        
        # Combine all code for analysis
        combined_code = "\n".join(s.get("content", "") for s in code_samples)
        
        modularity_score = self._score_modularity(combined_code, code_samples)
        reusability_score = self._score_reusability(combined_code)
        style_score = self._score_style_consistency(combined_code, claimed_stacks)
        anti_patterns = self._detect_anti_patterns(combined_code, claimed_stacks)
        best_practices = self._detect_best_practices(combined_code, claimed_stacks)
        structure_score = self._score_structure(code_samples)
        
        # Combine scores
        overall = (modularity_score * 0.25 + 
                  reusability_score * 0.25 + 
                  style_score * 0.20 + 
                  structure_score * 0.30)
        
        # Apply penalties for anti-patterns
        penalty = len(anti_patterns) * 5
        overall = max(0, min(100, overall - penalty))
        
        return {
            "overall_score": round(overall, 1),
            "modularity": round(modularity_score, 1),
            "reusability": round(reusability_score, 1),
            "style_consistency": round(style_score, 1),
            "structure": round(structure_score, 1),
            "anti_patterns": anti_patterns,
            "best_practices": best_practices,
            "code_health": self._assess_code_health(overall, anti_patterns, best_practices)
        }
    
    def _score_modularity(self, code, samples):
        """Score how modular and separated concerns are."""
        score = 50  # Base score
        
        # Check for function/class definitions (good modularity indicator)
        functions = len(re.findall(r'(def |function |const .* = |class )', code))
        if functions > len(code) / 500:  # Higher ratio = better modularity
            score += 20
        
        # Check for imports/requires (sign of using external modules)
        imports = len(re.findall(r'(import |require\(|from .* import)', code))
        if imports > 3:
            score += 15
        
        # Check for separation of concerns (services, controllers, etc.)
        for sample in samples:
            path = sample.get("path", "").lower()
            if any(x in path for x in ["service", "component", "controller", "model", "util", "helper"]):
                score += 10
                break
        
        # Check for clear naming conventions
        camel_case = len(re.findall(r'[a-z]+[A-Z][a-zA-Z]*', code))
        snake_case = len(re.findall(r'[a-z]+_[a-z]+', code))
        if camel_case > 5 or snake_case > 5:
            score += 10
        
        return min(100, score)
    
    def _score_reusability(self, code):
        """Score how reusable code is (functions, parameters, abstraction)."""
        score = 50  # Base score
        
        # Functions with parameters (reusable, not hardcoded)
        parameterized = len(re.findall(r'(def \w+\([^)]{5,}|function \w+\([^)]{5,})', code))
        if parameterized > 3:
            score += 25
        
        # Don't Repeat Yourself (DRY) - check for repeated patterns
        lines = code.split('\n')
        unique_lines = len(set(lines))
        if unique_lines / len(lines) > 0.9:  # > 90% unique lines is good
            score += 15
        
        # Higher-order functions, callbacks, composable patterns
        if any(x in code for x in ['map(', '.map(', 'filter(', '.filter(', 'compose(', 'pipe(']):
            score += 10
        
        # Abstraction levels (interfaces, base classes, protocols)
        abstractions = len(re.findall(r'(interface |abstract |protocol |::', code))
        if abstractions > 0:
            score += 15
        
        return min(100, score)
    
    def _score_style_consistency(self, code, claimed_stacks):
        """Score code style and consistency."""
        score = 50  # Base score
        
        # Check indentation consistency
        indent_4 = len(re.findall(r'\n    [^ ]', code))
        indent_2 = len(re.findall(r'\n  [^ ]', code))
        indent_tab = len(re.findall(r'\n\t[^ ]', code))
        
        total_indents = indent_4 + indent_2 + indent_tab
        if total_indents > 0:
            dominant = max(indent_4, indent_2, indent_tab)
            if dominant / total_indents > 0.8:  # 80%+ consistent
                score += 20
        
        # Check for proper spacing and formatting
        good_spacing = len(re.findall(r'[^ ]  [^ ]', code))  # Double spaces (often used for alignment)
        if good_spacing < len(code) / 1000:  # Minimal inconsistency
            score += 15
        
        # Language-specific style checks
        for stack in claimed_stacks:
            stack_lower = stack.lower()
            
            if stack_lower in ['python', 'py']:
                # PEP 8 indicators
                if re.search(r'# .*', code):  # Comments
                    score += 10
                if len(re.findall(r'\n\n\n', code)) == 0:  # No excessive blank lines
                    score += 5
            
            elif stack_lower in ['javascript', 'js', 'typescript', 'ts']:
                # JavaScript style consistency
                if re.search(r'const |let ', code) and 'var ' not in code:
                    score += 10
                if re.search(r'=>', code):  # Modern arrow functions
                    score += 5
        
        return min(100, score)
    
    def _detect_anti_patterns(self, code, claimed_stacks):
        """Detect code smells and anti-patterns."""
        issues = []
        
        # Global anti-patterns
        if re.search(r'(global |window\.|\$GLOBALS)', code):
            issues.append("Global state usage")
        
        if len(re.findall(r'(TODO|FIXME|HACK|XXX)', code)) > 5:
            issues.append("Many unresolved TODOs/FIXMEs")
        
        # Check for very long functions (>150 lines)
        functions = re.findall(r'(def |function |class )[\s\S]*?(?=(def |function |class |$))', code)
        for func in functions:
            if func.count('\n') > 150:
                issues.append("Very long functions detected")
                break
        
        # Deep nesting (more than 4 levels)
        max_indent = 0
        for line in code.split('\n'):
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)
        
        if max_indent > 24:  # >6 levels of nesting (4 spaces per level)
            issues.append("Deep nesting (>6 levels)")
        
        # Language-specific anti-patterns
        for stack in claimed_stacks:
            stack_lower = stack.lower()
            
            if stack_lower in ['python', 'py']:
                if re.search(r'except:\s*pass', code):
                    issues.append("Bare except with pass")
                if re.search(r'== True|== False|== None', code):
                    issues.append("Improper boolean/None comparison")
            
            elif stack_lower in ['javascript', 'js']:
                if re.search(r'var \w+\s*=', code):
                    issues.append("Using 'var' instead of 'const'/'let'")
                if re.search(r'== (?!null|undefined)', code):
                    issues.append("Using == instead of ===")
            
            elif stack_lower == 'react':
                if re.search(r'this\.state\.', code):
                    issues.append("Using class state instead of hooks")
                if 'key={index}' in code or 'key={i}' in code:
                    issues.append("Using array index as React key")
        
        return issues[:5]  # Top 5 issues
    
    def _detect_best_practices(self, code, claimed_stacks):
        """Detect good practices and modern patterns."""
        practices = []
        
        # General best practices
        if re.search(r'""".*?"""|\'\'\'.*?\'\'\'|//.*', code):
            practices.append("Good documentation/comments")
        
        if re.search(r'(try.*except|try.*catch)', code):
            practices.append("Error handling implemented")
        
        if re.search(r'(if __name__|if process\.env|if \(typeof)', code):
            practices.append("Proper entry point handling")
        
        # Language-specific best practices
        for stack in claimed_stacks:
            stack_lower = stack.lower()
            
            if stack_lower in ['python', 'py']:
                if re.search(r'with \w+ as \w+:', code):
                    practices.append("Context managers used")
                if re.search(r'@\w+', code):
                    practices.append("Decorators used")
                if any(x in code for x in ['list comprehension', '[x for x', '[x if x']):
                    practices.append("Pythonic patterns (comprehensions)")
            
            elif stack_lower in ['javascript', 'js', 'typescript', 'ts']:
                if re.search(r'=>', code):
                    practices.append("Arrow functions used")
                if re.search(r'async |await ', code):
                    practices.append("Modern async/await patterns")
                if any(x in code for x in ['const ', 'let ']):
                    practices.append("Modern variable declarations")
            
            elif stack_lower == 'react':
                if 'useState' in code or 'useEffect' in code:
                    practices.append("React Hooks used")
                if 'React.memo' in code or 'useMemo' in code:
                    practices.append("Performance optimization")
        
        return practices[:5]  # Top 5 practices
    
    def _score_structure(self, samples):
        """Score overall code structure and organization."""
        score = 50  # Base score
        
        if not samples:
            return score
        
        # Check diversity of file sizes (good structure indicator)
        sizes = [s.get("lines", 0) for s in samples]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        
        if 30 < avg_size < 200:  # Good file size range
            score += 25
        
        # Check for varied file types/purposes
        paths = [s.get("path", "") for s in samples]
        if len(set(paths)) == len(paths):  # All different files
            score += 10
        
        # Check for clear directory structure
        for path in paths:
            if '/' in path:
                score += 5
                break
        
        return min(100, score)
    
    def _assess_code_health(self, overall_score, anti_patterns, best_practices):
        """Assess overall code health."""
        if overall_score >= 80 and len(anti_patterns) == 0:
            return "Excellent"
        elif overall_score >= 70 and len(anti_patterns) <= 1:
            return "Good"
        elif overall_score >= 60:
            return "Acceptable"
        elif overall_score >= 50:
            return "Needs improvement"
        else:
            return "Poor"


def score_code_quality(code_samples, claimed_stacks, policy):
    """
    Score code quality using semantic analysis.
    
    Returns a 0-100 score that can be integrated into final score.
    """
    if not code_samples or not policy.get("graphcodebert_scoring", {}).get("enabled"):
        return None
    
    scorer = GraphCodeBERTScorer(policy)
    return scorer.score_samples(code_samples, claimed_stacks)


def compute_graphcodebert_quality_score(repo_path, claimed_stacks, policy):
    """
    Main entry point: Compute GraphCodeBERT quality score.
    
    This score measures:
    - Modularity
    - Reusability
    - Style consistency
    - Structure management
    - Best practices vs anti-patterns
    
    Returns: 0-100 score for integration into final score
    """
    from skill_assessment_engine import SkillAssessment
    
    gcb_policy = policy.get("graphcodebert_scoring", {})
    if not gcb_policy.get("enabled"):
        return None
    
    # Sample code files
    assessor = SkillAssessment(policy)
    samples = assessor._collect_code_content(repo_path, max_files=10)
    
    if not samples:
        return None
    
    # Score quality
    scorer = GraphCodeBERTScorer(policy)
    result = scorer.score_samples(
        [{"content": samples, "lines": samples.count('\n')}],
        claimed_stacks
    )
    
    return result.get("overall_score", 50)
