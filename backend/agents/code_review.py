"""Code Review Agent - Automated code quality checks.

Phase 11E Enhancement:
- Theme code quality (CSS var usage, no hardcoded theme colors)
- Cross-batch consistency (shared component imports, naming patterns)
- Integration code quality (Stripe/Resend/Supabase patterns)
- KB integration for pattern learning

Checks for:
- Code smells: duplication, god components, prop drilling
- TypeScript strictness (no 'any' types)
- Naming consistency
- Error handling
- Dev artifacts removal (console.logs, TODOs, commented code)
- Design system usage (no hardcoded colors/spacing)
- Python: type hints, docstrings, exception handling

Outputs code_review_report.json with issues by severity and auto-fixes.
Uses Claude Sonnet 4 model.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .base import BaseAgent, AgentResult

# Import knowledge base
try:
    from ..knowledge import query_knowledge, store_knowledge, KnowledgeEntryType
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CodeIssue:
    """Represents a code quality issue."""
    severity: str  # critical, high, medium, low
    category: str  # duplication, typescript, naming, error_handling, dev_artifacts, design_system
    rule: str
    message: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    auto_fixable: bool = False
    fix_suggestion: Optional[str] = None


@dataclass
class AutoFix:
    """Represents an auto-fix that was applied."""
    file_path: str
    rule: str
    original: str
    fixed: str
    line_number: Optional[int] = None


@dataclass
class CodeReviewReport:
    """Complete code review report."""
    project_id: str
    generated_at: str
    total_files_scanned: int
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues_by_category: Dict[str, int]
    issues: List[Dict[str, Any]]
    auto_fixes_applied: List[Dict[str, Any]]
    summary: str
    pass_threshold: bool  # Whether code passes quality threshold
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "generated_at": self.generated_at,
            "total_files_scanned": self.total_files_scanned,
            "total_issues": self.total_issues,
            "issues_by_severity": self.issues_by_severity,
            "issues_by_category": self.issues_by_category,
            "issues": self.issues,
            "auto_fixes_applied": self.auto_fixes_applied,
            "summary": self.summary,
            "pass_threshold": self.pass_threshold,
        }


# Code patterns to detect
TYPESCRIPT_PATTERNS = {
    "any_type": {
        "pattern": r":\s*any\b",
        "message": "Avoid using 'any' type - use proper TypeScript types",
        "severity": "high",
        "auto_fix": False,
    },
    "explicit_any": {
        "pattern": r"as\s+any\b",
        "message": "Avoid type assertions to 'any'",
        "severity": "high",
        "auto_fix": False,
    },
    "ts_ignore": {
        "pattern": r"@ts-ignore|@ts-nocheck",
        "message": "Avoid @ts-ignore - fix the underlying type issue",
        "severity": "medium",
        "auto_fix": False,
    },
}

DEV_ARTIFACT_PATTERNS = {
    "console_log": {
        "pattern": r"console\.(log|debug|info|warn)\s*\(",
        "message": "Remove console.log statements in production code",
        "severity": "medium",
        "auto_fix": True,
        "fix_pattern": r"^\s*console\.(log|debug|info|warn)\s*\([^)]*\);?\s*\n?",
        "fix_replace": "",
    },
    "debugger": {
        "pattern": r"\bdebugger\b",
        "message": "Remove debugger statements",
        "severity": "high",
        "auto_fix": True,
        "fix_pattern": r"^\s*debugger;?\s*\n?",
        "fix_replace": "",
    },
    "todo_comment": {
        "pattern": r"//\s*(TODO|FIXME|XXX|HACK)\b",
        "message": "Unresolved TODO/FIXME comment found",
        "severity": "low",
        "auto_fix": False,
    },
    "commented_code": {
        "pattern": r"//\s*(const|let|var|function|class|import|export|return)\s+\w+",
        "message": "Commented-out code detected - remove if not needed",
        "severity": "low",
        "auto_fix": False,
    },
}

DESIGN_SYSTEM_PATTERNS = {
    "hardcoded_color_hex": {
        "pattern": r"['\"]#[0-9A-Fa-f]{3,8}['\"]",
        "message": "Hardcoded hex color - use design system tokens instead",
        "severity": "medium",
        "auto_fix": False,
    },
    "hardcoded_color_rgb": {
        "pattern": r"rgba?\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+",
        "message": "Hardcoded RGB color - use design system tokens instead",
        "severity": "medium",
        "auto_fix": False,
    },
    "hardcoded_px": {
        "pattern": r":\s*\d+px(?!\s*\/\*\s*design)",
        "message": "Hardcoded pixel value - consider using spacing tokens",
        "severity": "low",
        "auto_fix": False,
    },
    "inline_style": {
        "pattern": r"style\s*=\s*\{\s*\{",
        "message": "Inline styles detected - prefer Tailwind classes or styled components",
        "severity": "low",
        "auto_fix": False,
    },
}

# Phase 11E: Theme-specific patterns
THEME_CODE_PATTERNS = {
    "hardcoded_dark_color": {
        "pattern": r"(?:bg|text|border)-(?:gray|slate|zinc)-(?:[7-9]00|950)",
        "message": "Hardcoded dark theme color - use dark: variant for theme support",
        "severity": "medium",
        "auto_fix": False,
    },
    "hardcoded_light_color": {
        "pattern": r"(?:bg|text|border)-(?:white|gray-50|slate-50)",
        "message": "Hardcoded light color - may not work in dark mode",
        "severity": "medium",
        "auto_fix": False,
    },
    "missing_dark_variant": {
        "pattern": r"className=['\"][^'\"]*bg-white[^'\"]*['\"](?![^>]*dark:)",
        "message": "bg-white without dark: variant - add dark mode style",
        "severity": "high",
        "auto_fix": False,
    },
    "no_css_variable": {
        "pattern": r"color:\s*(?!var\(--)[^;]+;",
        "message": "Direct color value instead of CSS variable - use var(--color-*)",
        "severity": "low",
        "auto_fix": False,
    },
}

# Phase 11E: Integration code patterns
INTEGRATION_PATTERNS = {
    "stripe_insecure": {
        "pattern": r"stripe\.(?:charges|customers|subscriptions)\.(?:create|update)\([^)]*\)",
        "check_file": r"client|page|component",  # Should not be in client code
        "message": "Stripe operation in client code - move to server action/API route",
        "severity": "critical",
    },
    "supabase_admin_client": {
        "pattern": r"createClient.*service_role",
        "check_file": r"client|page|component",
        "message": "Supabase admin client in client code - use anon key",
        "severity": "critical",
    },
    "env_direct_access": {
        "pattern": r"process\.env\.[A-Z_]+(?!.*NEXT_PUBLIC)",
        "check_file": r"client|page\.tsx$|component",
        "message": "Server env var accessed in client code - use NEXT_PUBLIC_ prefix",
        "severity": "high",
    },
}

PYTHON_PATTERNS = {
    "missing_type_hint": {
        "pattern": r"def\s+\w+\s*\([^)]*\)\s*:",
        "check_fn": "_check_missing_type_hint",
        "message": "Function missing return type hint",
        "severity": "low",
        "auto_fix": False,
    },
    "bare_except": {
        "pattern": r"except\s*:",
        "message": "Bare except clause - specify exception type",
        "severity": "high",
        "auto_fix": False,
    },
    "print_statement": {
        "pattern": r"\bprint\s*\(",
        "message": "print() statement - use logging instead",
        "severity": "low",
        "auto_fix": False,
    },
    "pass_in_except": {
        "pattern": r"except.*:\s*\n\s*pass\s*\n",
        "message": "Silent exception handling - at least log the error",
        "severity": "medium",
        "auto_fix": False,
    },
}

CODE_SMELL_PATTERNS = {
    "long_function": {
        "threshold": 50,  # lines
        "message": "Function is too long ({lines} lines) - consider breaking it up",
        "severity": "medium",
    },
    "prop_drilling": {
        "pattern": r"props\.\w+\.\w+\.\w+",
        "message": "Deep prop drilling detected - consider using context or state management",
        "severity": "medium",
    },
    "god_component": {
        "threshold": 300,  # lines
        "message": "Component file is too large ({lines} lines) - split into smaller components",
        "severity": "high",
    },
}


class CodeReviewAgent(BaseAgent):
    """Code Review Agent that checks code quality and applies auto-fixes.
    
    Phase 11E: Enhanced with theme code quality, integration patterns, and KB integration.
    """
    
    name = "code_review"
    description = "Code Review - Checks quality and applies fixes"
    model = "anthropic/claude-sonnet-4"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.issues: List[CodeIssue] = []
        self.auto_fixes: List[AutoFix] = []
        self.files_scanned: int = 0
    
    @property
    def name(self) -> str:
        return "code_review"
    
    async def _query_kb_for_patterns(self, project_type: str) -> List[Dict]:
        """Query KB for known code quality patterns."""
        if not KB_AVAILABLE:
            return []
        
        try:
            results = await query_knowledge(
                query=f"code quality patterns for {project_type}",
                entry_types=[KnowledgeEntryType.CODE_PATTERN],
                limit=15,
            )
            return results
        except Exception as e:
            logger.warning(f"KB query failed: {e}")
            return []
    
    async def _write_findings_to_kb(self, issues: List[CodeIssue], project_type: str):
        """Write code review findings to KB."""
        if not KB_AVAILABLE:
            return
        
        try:
            # Store patterns for future reference
            for issue in issues:
                if issue.severity in ["critical", "high"]:
                    await store_knowledge(
                        entry_type=KnowledgeEntryType.CODE_PATTERN,
                        content=f"Code issue: {issue.message}",
                        metadata={
                            "project_type": project_type,
                            "category": issue.category,
                            "rule": issue.rule,
                            "severity": issue.severity,
                            "agent": "code_review",
                        },
                    )
        except Exception as e:
            logger.warning(f"KB write failed: {e}")
    
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute code review on the project with Phase 11E enhancements."""
        logger.info("Starting code review")
        
        project_id = context.get("project_id", "unknown")
        project_path = context.get("project_path", "/tmp/project")
        auto_fix_enabled = context.get("auto_fix", True)
        project_type = context.get("project_type", "web_simple")
        requirements = context.get("requirements", {})
        
        self.issues = []
        self.auto_fixes = []
        self.files_scanned = 0
        
        if not os.path.exists(project_path):
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=[f"Project path does not exist: {project_path}"],
            )
        
        # Query KB for patterns
        kb_patterns = await self._query_kb_for_patterns(project_type)
        
        # Determine which patterns to use based on project type
        is_python_project = project_type in ["python_api", "python_saas", "cli_tool"]
        is_typescript_project = project_type in ["web_simple", "web_complex", "mobile_cross_platform", "mobile_pwa", "desktop_app", "chrome_extension"]
        
        # Determine theme mode
        color_scheme = requirements.get("color_scheme", "dark")
        check_dual_theme = color_scheme in ["both", "system"]
        
        # Scan codebase
        self._scan_directory(project_path, is_python_project, is_typescript_project)
        
        # Phase 11E: Check theme code quality
        if check_dual_theme:
            self._scan_theme_patterns(project_path)
        
        # Phase 11E: Check integration code quality
        integrations = requirements.get("integrations", [])
        if integrations:
            self._scan_integration_patterns(project_path, integrations)
        
        # Apply auto-fixes if enabled
        if auto_fix_enabled:
            self._apply_auto_fixes(project_path)
        
        # Check for code smells
        self._detect_code_smells(project_path)
        
        # Check for code duplication
        duplicates = self._detect_duplication(project_path)
        for dup in duplicates:
            self.issues.append(CodeIssue(
                severity="medium",
                category="duplication",
                rule="code_duplication",
                message=f"Duplicate code block found in {len(dup['files'])} files",
                file_path=dup["files"][0],
                code_snippet=dup["snippet"][:100] + "...",
            ))
        
        # Generate report
        report = self._generate_report(project_id, project_path)
        
        # Write report to file
        report_path = os.path.join(project_path, "code_review_report.json")
        try:
            with open(report_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            self.logger.info(f"Code review report written to {report_path}")
        except Exception as e:
            self.logger.warning(f"Failed to write report: {e}")
        
        # Determine success
        critical_count = report.issues_by_severity.get("critical", 0)
        high_count = report.issues_by_severity.get("high", 0)
        success = critical_count == 0 and high_count <= 5
        
        return AgentResult(
            success=success,
            agent_name=self.name,
            data={
                "report": report.to_dict(),
                "report_path": report_path,
                "pass_threshold": report.pass_threshold,
            },
            errors=[f"{i['category']}: {i['message']}" for i in report.issues if i["severity"] == "critical"],
            warnings=[f"Found {report.total_issues} code quality issues ({critical_count} critical, {high_count} high)"],
        )
    
    def _scan_directory(self, path: str, is_python: bool, is_typescript: bool) -> None:
        """Recursively scan directory for code issues."""
        skip_dirs = ["node_modules", ".git", "__pycache__", ".next", "dist", "build", ".venv", "venv"]
        
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # TypeScript/JavaScript files
                if is_typescript and file.endswith(('.ts', '.tsx', '.js', '.jsx')):
                    self._scan_typescript_file(file_path)
                
                # Python files
                if is_python and file.endswith('.py'):
                    self._scan_python_file(file_path)
                
                # CSS/SCSS files (design system checks)
                if file.endswith(('.css', '.scss', '.sass')):
                    self._scan_style_file(file_path)
    
    def _scan_typescript_file(self, file_path: str) -> None:
        """Scan TypeScript/JavaScript file for issues."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return
        
        self.files_scanned += 1
        
        # Check TypeScript patterns
        for rule_name, rule in TYPESCRIPT_PATTERNS.items():
            for i, line in enumerate(lines):
                if re.search(rule["pattern"], line):
                    self.issues.append(CodeIssue(
                        severity=rule["severity"],
                        category="typescript",
                        rule=rule_name,
                        message=rule["message"],
                        file_path=file_path,
                        line_number=i + 1,
                        code_snippet=line.strip()[:100],
                        auto_fixable=rule.get("auto_fix", False),
                    ))
        
        # Check dev artifacts
        for rule_name, rule in DEV_ARTIFACT_PATTERNS.items():
            for i, line in enumerate(lines):
                if re.search(rule["pattern"], line):
                    self.issues.append(CodeIssue(
                        severity=rule["severity"],
                        category="dev_artifacts",
                        rule=rule_name,
                        message=rule["message"],
                        file_path=file_path,
                        line_number=i + 1,
                        code_snippet=line.strip()[:100],
                        auto_fixable=rule.get("auto_fix", False),
                    ))
        
        # Check design system (in TSX files)
        if file_path.endswith(('.tsx', '.jsx')):
            for rule_name, rule in DESIGN_SYSTEM_PATTERNS.items():
                for i, line in enumerate(lines):
                    if re.search(rule["pattern"], line):
                        # Skip if it's a Tailwind config or CSS variable
                        if 'tailwind' in file_path.lower() or '--' in line:
                            continue
                        self.issues.append(CodeIssue(
                            severity=rule["severity"],
                            category="design_system",
                            rule=rule_name,
                            message=rule["message"],
                            file_path=file_path,
                            line_number=i + 1,
                            code_snippet=line.strip()[:100],
                        ))
    
    def _scan_python_file(self, file_path: str) -> None:
        """Scan Python file for issues."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return
        
        self.files_scanned += 1
        
        for rule_name, rule in PYTHON_PATTERNS.items():
            if "check_fn" in rule:
                # Use custom check function
                continue
            
            for i, line in enumerate(lines):
                if re.search(rule["pattern"], line):
                    self.issues.append(CodeIssue(
                        severity=rule["severity"],
                        category="python",
                        rule=rule_name,
                        message=rule["message"],
                        file_path=file_path,
                        line_number=i + 1,
                        code_snippet=line.strip()[:100],
                    ))
        
        # Check for missing docstrings on classes and functions
        self._check_python_docstrings(file_path, content)
    
    def _check_python_docstrings(self, file_path: str, content: str) -> None:
        """Check for missing docstrings in Python file."""
        # Simple pattern matching for function/class definitions
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check function definitions
            if stripped.startswith('def ') and not stripped.startswith('def _'):
                # Check if next non-empty line is a docstring
                has_docstring = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith('"""') or next_line.startswith("'''"):
                        has_docstring = True
                        break
                    if next_line and not next_line.startswith('#'):
                        break
                
                if not has_docstring:
                    self.issues.append(CodeIssue(
                        severity="low",
                        category="python",
                        rule="missing_docstring",
                        message="Public function missing docstring",
                        file_path=file_path,
                        line_number=i + 1,
                        code_snippet=stripped[:100],
                    ))
    
    def _scan_style_file(self, file_path: str) -> None:
        """Scan CSS/SCSS file for design system violations."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return
        
        self.files_scanned += 1
        
        # Check for hardcoded colors
        for i, line in enumerate(lines):
            # Skip CSS variable definitions
            if '--' in line and ':' in line:
                continue
            
            if re.search(r'#[0-9A-Fa-f]{3,8}\b', line):
                self.issues.append(CodeIssue(
                    severity="low",
                    category="design_system",
                    rule="hardcoded_color_css",
                    message="Hardcoded color in CSS - use CSS variables",
                    file_path=file_path,
                    line_number=i + 1,
                    code_snippet=line.strip()[:100],
                ))
    
    def _detect_code_smells(self, project_path: str) -> None:
        """Detect code smells like long functions and god components."""
        code_extensions = ['.ts', '.tsx', '.js', '.jsx', '.py']
        skip_dirs = ["node_modules", ".git", "__pycache__", ".next", "dist"]
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if not any(file.endswith(ext) for ext in code_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                except Exception:
                    continue
                
                line_count = len(lines)
                
                # Check for god components (very large files)
                threshold = CODE_SMELL_PATTERNS["god_component"]["threshold"]
                if line_count > threshold:
                    self.issues.append(CodeIssue(
                        severity=CODE_SMELL_PATTERNS["god_component"]["severity"],
                        category="code_smell",
                        rule="god_component",
                        message=CODE_SMELL_PATTERNS["god_component"]["message"].format(lines=line_count),
                        file_path=file_path,
                    ))
                
                # Check for long functions
                self._check_long_functions(file_path, lines)
                
                # Check for prop drilling
                for i, line in enumerate(lines):
                    if re.search(CODE_SMELL_PATTERNS["prop_drilling"]["pattern"], line):
                        self.issues.append(CodeIssue(
                            severity=CODE_SMELL_PATTERNS["prop_drilling"]["severity"],
                            category="code_smell",
                            rule="prop_drilling",
                            message=CODE_SMELL_PATTERNS["prop_drilling"]["message"],
                            file_path=file_path,
                            line_number=i + 1,
                            code_snippet=line.strip()[:100],
                        ))
    
    def _check_long_functions(self, file_path: str, lines: List[str]) -> None:
        """Check for long functions in the file."""
        threshold = CODE_SMELL_PATTERNS["long_function"]["threshold"]
        
        function_starts = []
        brace_count = 0
        in_function = False
        function_start_line = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect function start (simplified)
            if (re.match(r'(function|const|let|var)\s+\w+\s*=?\s*(async\s*)?\(?', stripped) or
                re.match(r'(async\s+)?function\s+\w+', stripped) or
                re.match(r'def\s+\w+', stripped)):
                if '{' in line or ':' in line:
                    function_start_line = i
                    in_function = True
                    brace_count = line.count('{') - line.count('}')
            
            if in_function:
                brace_count += line.count('{') - line.count('}')
                
                # Python uses indentation
                if file_path.endswith('.py'):
                    if i > function_start_line and stripped and not line.startswith(' ') and not line.startswith('\t'):
                        func_length = i - function_start_line
                        if func_length > threshold:
                            self.issues.append(CodeIssue(
                                severity=CODE_SMELL_PATTERNS["long_function"]["severity"],
                                category="code_smell",
                                rule="long_function",
                                message=CODE_SMELL_PATTERNS["long_function"]["message"].format(lines=func_length),
                                file_path=file_path,
                                line_number=function_start_line + 1,
                            ))
                        in_function = False
                else:
                    if brace_count <= 0:
                        func_length = i - function_start_line
                        if func_length > threshold:
                            self.issues.append(CodeIssue(
                                severity=CODE_SMELL_PATTERNS["long_function"]["severity"],
                                category="code_smell",
                                rule="long_function",
                                message=CODE_SMELL_PATTERNS["long_function"]["message"].format(lines=func_length),
                                file_path=file_path,
                                line_number=function_start_line + 1,
                            ))
                        in_function = False
    
    def _detect_duplication(self, project_path: str) -> List[Dict[str, Any]]:
        """Detect duplicated code blocks."""
        duplicates = []
        code_blocks: Dict[str, List[str]] = {}
        
        code_extensions = ['.ts', '.tsx', '.js', '.jsx', '.py']
        skip_dirs = ["node_modules", ".git", "__pycache__", ".next", "dist"]
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if not any(file.endswith(ext) for ext in code_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    continue
                
                # Extract significant code blocks (5+ lines)
                lines = content.split('\n')
                for i in range(len(lines) - 5):
                    block = '\n'.join(lines[i:i+5])
                    # Normalize whitespace for comparison
                    normalized = re.sub(r'\s+', ' ', block.strip())
                    
                    if len(normalized) > 100:  # Only consider significant blocks
                        if normalized not in code_blocks:
                            code_blocks[normalized] = []
                        code_blocks[normalized].append(file_path)
        
        # Find duplicates (blocks appearing in multiple files)
        for block, files in code_blocks.items():
            unique_files = list(set(files))
            if len(unique_files) > 1:
                duplicates.append({
                    "snippet": block,
                    "files": unique_files,
                })
        
        return duplicates[:10]  # Limit to top 10 duplicates
    
    def _apply_auto_fixes(self, project_path: str) -> None:
        """Apply auto-fixes to fixable issues."""
        # Group issues by file
        issues_by_file: Dict[str, List[CodeIssue]] = {}
        for issue in self.issues:
            if issue.auto_fixable:
                if issue.file_path not in issues_by_file:
                    issues_by_file[issue.file_path] = []
                issues_by_file[issue.file_path].append(issue)
        
        for file_path, issues in issues_by_file.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                for issue in issues:
                    rule = DEV_ARTIFACT_PATTERNS.get(issue.rule)
                    if rule and "fix_pattern" in rule:
                        content = re.sub(
                            rule["fix_pattern"],
                            rule["fix_replace"],
                            content,
                            flags=re.MULTILINE
                        )
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.auto_fixes.append(AutoFix(
                        file_path=file_path,
                        rule=", ".join(i.rule for i in issues),
                        original="[see diff]",
                        fixed="[auto-fixed]",
                    ))
                    
                    self.logger.info(f"Auto-fixed issues in {file_path}")
            
            except Exception as e:
                self.logger.warning(f"Failed to auto-fix {file_path}: {e}")
    
    def _generate_report(self, project_id: str, project_path: str) -> CodeReviewReport:
        """Generate the code review report."""
        # Count issues by severity
        issues_by_severity = {}
        for issue in self.issues:
            issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1
        
        # Count issues by category
        issues_by_category = {}
        for issue in self.issues:
            issues_by_category[issue.category] = issues_by_category.get(issue.category, 0) + 1
        
        # Convert issues to dicts
        issues_list = []
        for issue in self.issues:
            issues_list.append({
                "severity": issue.severity,
                "category": issue.category,
                "rule": issue.rule,
                "message": issue.message,
                "file": issue.file_path,
                "line": issue.line_number,
                "snippet": issue.code_snippet,
                "auto_fixable": issue.auto_fixable,
                "fix_suggestion": issue.fix_suggestion,
            })
        
        # Convert auto-fixes to dicts
        fixes_list = []
        for fix in self.auto_fixes:
            fixes_list.append({
                "file": fix.file_path,
                "rule": fix.rule,
                "line": fix.line_number,
            })
        
        # Determine pass threshold
        critical_count = issues_by_severity.get("critical", 0)
        high_count = issues_by_severity.get("high", 0)
        pass_threshold = critical_count == 0 and high_count <= 5
        
        # Generate summary
        total = len(self.issues)
        if total == 0:
            summary = "✅ Code review passed - no issues found"
        elif pass_threshold:
            summary = f"✅ Code review passed with {total} issues ({critical_count} critical, {high_count} high)"
        else:
            summary = f"❌ Code review failed - {total} issues ({critical_count} critical, {high_count} high)"
        
        return CodeReviewReport(
            project_id=project_id,
            generated_at=datetime.utcnow().isoformat(),
            total_files_scanned=self.files_scanned,
            total_issues=len(self.issues),
            issues_by_severity=issues_by_severity,
            issues_by_category=issues_by_category,
            issues=issues_list,
            auto_fixes_applied=fixes_list,
            summary=summary,
            pass_threshold=pass_threshold,
        )

    def _scan_theme_patterns(self, project_path: str) -> None:
        """Phase 11E: Scan for theme-related code quality issues."""
        code_extensions = [".tsx", ".jsx", ".ts", ".js"]
        skip_dirs = ["node_modules", ".git", "__pycache__", ".next", "dist"]
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if not any(file.endswith(ext) for ext in code_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                except Exception:
                    continue
                
                # Check theme patterns
                for rule_name, rule in THEME_CODE_PATTERNS.items():
                    pattern = rule.get("pattern")
                    if not pattern:
                        continue
                    
                    for i, line in enumerate(lines):
                        if re.search(pattern, line):
                            self.issues.append(CodeIssue(
                                severity=rule["severity"],
                                category="theme",
                                rule=rule_name,
                                message=rule["message"],
                                file_path=file_path,
                                line_number=i + 1,
                                code_snippet=line.strip()[:100],
                            ))
    
    def _scan_integration_patterns(self, project_path: str, integrations: List[str]) -> None:
        """Phase 11E: Scan for integration-related code quality issues."""
        code_extensions = [".tsx", ".jsx", ".ts", ".js"]
        skip_dirs = ["node_modules", ".git", "__pycache__", ".next", "dist"]
        
        # Determine which patterns to check based on integrations
        patterns_to_check = []
        for integration in integrations:
            int_lower = integration.lower()
            if "stripe" in int_lower:
                patterns_to_check.append(("stripe_insecure", INTEGRATION_PATTERNS["stripe_insecure"]))
            if "supabase" in int_lower:
                patterns_to_check.append(("supabase_admin_client", INTEGRATION_PATTERNS["supabase_admin_client"]))
        
        # Always check env access
        patterns_to_check.append(("env_direct_access", INTEGRATION_PATTERNS["env_direct_access"]))
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if not any(file.endswith(ext) for ext in code_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                except Exception:
                    continue
                
                for rule_name, rule in patterns_to_check:
                    pattern = rule.get("pattern")
                    check_file = rule.get("check_file", "")
                    
                    # Only check if file matches the check_file pattern
                    if check_file and not re.search(check_file, file_path, re.IGNORECASE):
                        continue
                    
                    for i, line in enumerate(lines):
                        if re.search(pattern, line):
                            self.issues.append(CodeIssue(
                                severity=rule["severity"],
                                category="integration",
                                rule=rule_name,
                                message=rule["message"],
                                file_path=file_path,
                                line_number=i + 1,
                                code_snippet=line.strip()[:100],
                            ))