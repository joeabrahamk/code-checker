"""
Skill Knowledge Assessment Module

Detects language-specific patterns in code to assess depth of understanding
for each claimed technology stack. Stored separately from Stack Accuracy.
"""

import os
import re
from collections import defaultdict


class SkillAssessment:
    """Assess skill knowledge for each claimed stack based on code patterns."""
    
    def __init__(self, policy):
        self.policy = policy
        self.skill_policy = policy.get("skill_knowledge_assessment", {})
        self.patterns = self.skill_policy.get("language_specific_signals", {})
        self.thresholds = self.skill_policy.get("knowledge_thresholds", {})
        
    def scan_codebase(self, repo_path, claimed_stacks):
        """
        Scan codebase for language-specific patterns and generate skill scores.
        
        Returns:
            list: Skill assessment for each claimed stack
        """
        if not claimed_stacks or repo_path is None:
            return []
        
        results = []
        code_content = self._collect_code_content(repo_path)
        
        for stack in claimed_stacks:
            stack_lower = stack.lower()
            
            # Get language-specific patterns
            if stack_lower in self.patterns:
                score, indicators = self._score_stack(stack_lower, code_content)
            else:
                # Unknown stack type - try general indicators
                score, indicators = self._score_general(stack_lower, code_content)
            
            level = self._get_knowledge_level(score)
            remark = self._generate_remark(stack, level, score, indicators)
            
            results.append({
                "stack": stack,
                "knowledge_score": min(100, score),
                "level": level,
                "indicators_detected": indicators,
                "remark": remark
            })
        
        return results
    
    def _collect_code_content(self, repo_path, max_files=50):
        """Collect code content from repo for pattern matching."""
        content = ""
        file_count = 0
        
        ignored = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}
        
        for root, dirs, files in os.walk(repo_path):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if d not in ignored]
            
            for file in files:
                if file_count >= max_files:
                    return content
                
                if not self._is_code_file(file):
                    continue
                
                try:
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content += f.read() + "\n"
                        file_count += 1
                except Exception:
                    continue
        
        return content
    
    def _is_code_file(self, filename):
        """Check if file is a code file."""
        code_extensions = {
            '.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.cs', '.go',
            '.rb', '.php', '.rs', '.swift', '.kt', '.sql', '.dockerfile'
        }
        return any(filename.endswith(ext) for ext in code_extensions)
    
    def _score_stack(self, stack_lower, code_content):
        """Score a known stack based on pattern detection."""
        score = 0
        indicators = []
        patterns = self.patterns.get(stack_lower, {})
        
        for pattern_name, points in patterns.items():
            if self._detect_pattern(pattern_name, stack_lower, code_content):
                score += points
                indicators.append(f"{pattern_name} ({points} pts)")
        
        return score, indicators
    
    def _score_general(self, stack_lower, code_content):
        """Score unknown stacks using general indicators."""
        score = 0
        indicators = []
        general_indicators = self.skill_policy.get("knowledge_indicators", {})
        
        # Check general indicators
        for indicator, points in general_indicators.items():
            if self._detect_general_indicator(indicator, code_content):
                score += points
                indicators.append(f"{indicator} ({points} pts)")
        
        return score, indicators
    
    def _detect_pattern(self, pattern_name, stack, code_content):
        """Detect if a specific pattern exists in code."""
        content_lower = code_content.lower()
        
        # JavaScript/TypeScript patterns
        if stack in ['javascript', 'js', 'typescript', 'ts', 'jsx', 'tsx']:
            patterns = {
                'async_await': r'\basync\s+\w+\s*\(|await\s+\w+',
                'modern_es6_syntax': r'=>|const\s+\w+\s*=|let\s+\w+\s*=|class\s+\w+',
                'closures_and_scope': r'function\s*\w*\s*\([^)]*\)\s*{.*return\s+function',
                'event_handling': r'addEventListener|\.on\(|\.off\(',
                'dom_manipulation': r'document\.|querySelector|getElementById',
            }
        # Python patterns
        elif stack == 'python':
            patterns = {
                'list_comprehensions': r'\[.+\s+for\s+\w+\s+in\s+',
                'decorators': r'@\w+|@property|@staticmethod|@classmethod',
                'exception_handling': r'try:|except\s+\w+:|finally:',
                'context_managers': r'with\s+\w+\s+as\s+\w+:',
                'generators': r'yield\s+|def\s+\w+\s*\([^)]*\):.*yield',
            }
        # React patterns
        elif stack == 'react':
            patterns = {
                'hooks_usage': r'useState|useEffect|useContext|useReducer|useCallback|useMemo',
                'state_management': r'useState|useReducer|useContext|Redux|Zustand',
                'component_optimization': r'React\.memo|useMemo|useCallback',
                'error_boundaries': r'ErrorBoundary|componentDidCatch',
                'custom_hooks': r'function\s+use[A-Z]\w+|const\s+use[A-Z]\w+\s*=',
            }
        # Java patterns
        elif stack == 'java':
            patterns = {
                'oop_principles': r'public\s+class|interface\s+\w+|abstract\s+class',
                'generics': r'<[A-Z]\w+>|<\?|extends|super',
                'exception_handling': r'throws\s+\w+|catch\s*\(|try\s*{',
                'design_patterns': r'Singleton|Factory|Observer|Strategy|Adapter',
                'streams_api': r'\.stream\(|\.map\(|\.filter\(|\.reduce\(',
            }
        # SQL patterns
        elif stack == 'sql':
            patterns = {
                'joins_and_aggregates': r'JOIN|LEFT JOIN|INNER JOIN|GROUP BY|COUNT|SUM|AVG',
                'query_optimization': r'INDEX|EXPLAIN|ANALYZE|VACUUM|DISTINCT',
                'transactions': r'BEGIN|COMMIT|ROLLBACK|SAVEPOINT',
                'indexing': r'CREATE\s+INDEX|PRIMARY\s+KEY|UNIQUE',
                'normalization': r'FOREIGN\s+KEY|REFERENCES|ON\s+DELETE',
            }
        # Docker patterns
        elif stack == 'docker':
            patterns = {
                'multi_stage_builds': r'FROM.*AS|--from=',
                'volume_management': r'VOLUME|volumes:|-v\s+',
                'networking': r'EXPOSE|--network|links:',
                'security': r'USER\s+\w+|--read-only|--cap-drop',
            }
        else:
            return False
        
        pattern_regex = patterns.get(pattern_name)
        if not pattern_regex:
            return False
        
        try:
            return bool(re.search(pattern_regex, code_content, re.IGNORECASE | re.DOTALL))
        except Exception:
            return False
    
    def _detect_general_indicator(self, indicator, code_content):
        """Detect general engineering indicators."""
        content_lower = code_content.lower()
        
        indicators = {
            'advanced_patterns': r'abstract|interface|strategy|factory|observer|singleton',
            'error_handling_patterns': r'try|catch|except|finally|error|exception',
            'state_management': r'state|store|reducer|context|props',
            'api_integration': r'fetch|axios|http|request|api|endpoint',
            'testing_coverage': r'test|describe|it\(|assert|expect|mock',
            'performance_optimization': r'memo|cache|lazy|debounce|throttle|memoize',
            'security_practices': r'sanitize|validate|escape|hash|encrypt|auth|csrf|xss',
        }
        
        pattern = indicators.get(indicator)
        if not pattern:
            return False
        
        try:
            return bool(re.search(pattern, code_content, re.IGNORECASE))
        except Exception:
            return False
    
    def _get_knowledge_level(self, score):
        """Determine knowledge level from score."""
        for level_name, threshold_info in self.thresholds.items():
            min_score = threshold_info.get("min", 0)
            if score >= min_score:
                return level_name
        
        return "novice"
    
    def _generate_remark(self, stack, level, score, indicators):
        """Generate a descriptive remark based on skill assessment."""
        if not indicators:
            return f"Claimed but not evidenced. No {stack}-specific patterns detected."
        
        level_descriptions = {
            "expert": "Deep mastery with industry best practices.",
            "advanced": "Strong understanding with proper usage patterns.",
            "intermediate": "Functional knowledge with basic patterns.",
            "beginner": "Basic usage with minimal patterns.",
            "novice": "Claimed but lacks evidence of implementation.",
        }
        
        desc = level_descriptions.get(level, "")
        patterns_str = ", ".join([ind.split(' (')[0] for ind in indicators[:3]])
        
        if len(indicators) > 3:
            patterns_str += f" and {len(indicators) - 3} more"
        
        if desc:
            return f"{desc} Detected: {patterns_str}."
        
        return f"Score: {score}. Detected patterns: {patterns_str}."


def compute_skill_assessments(repo_path, claimed_stacks, policy):
    """
    Compute skill knowledge assessments for claimed stacks.
    
    Args:
        repo_path: Path to repository
        claimed_stacks: List of claimed technology stacks
        policy: Scoring policy dict
    
    Returns:
        list: Skill assessment results
    """
    assessor = SkillAssessment(policy)
    return assessor.scan_codebase(repo_path, claimed_stacks)
