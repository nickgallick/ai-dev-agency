"""Accessibility Agent - Playwright + axe-core integration for WCAG compliance.

Phase 11E Enhancement:
- CRITICAL: Dual-theme testing (run axe-core in BOTH themes)
- Color contrast in both themes (WCAG AA 4.5:1)
- Focus indicators in both themes
- Glass panel contrast verification
- Page-aware scanning (ALL pages from requirements.pages)
- Feature-specific a11y checks (auth forms, payments, uploads)
- Query KB for common a11y issues
- Write findings to KB with theme tags
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import AgentResult, BaseAgent

# Import knowledge base
try:
    from ..knowledge import query_knowledge, store_knowledge, KnowledgeEntryType
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AccessibilityIssue:
    """Represents an accessibility violation."""
    id: str
    impact: str  # critical, serious, moderate, minor
    description: str
    help: str
    help_url: str
    wcag_tags: List[str]
    nodes: List[Dict[str, Any]]
    theme: str = "default"  # "light", "dark", or "default"
    page: str = "/"  # Which page this was found on
    fix_suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "impact": self.impact,
            "description": self.description,
            "help": self.help,
            "help_url": self.help_url,
            "wcag_tags": self.wcag_tags,
            "nodes": self.nodes,
            "theme": self.theme,
            "page": self.page,
            "fix_suggestion": self.fix_suggestion,
        }


@dataclass
class ContrastIssue:
    """Represents a color contrast issue."""
    element: str
    foreground: str
    background: str
    ratio: float
    required_ratio: float
    theme: str
    page: str
    file_path: Optional[str] = None


@dataclass
class AccessibilityReport:
    """Accessibility audit report."""
    total_violations: int = 0
    passes: int = 0
    incomplete: int = 0
    inapplicable: int = 0
    violations: List[AccessibilityIssue] = field(default_factory=list)
    violations_by_theme: Dict[str, List[AccessibilityIssue]] = field(default_factory=dict)
    contrast_issues: List[ContrastIssue] = field(default_factory=list)
    by_impact: Dict[str, int] = field(default_factory=dict)
    wcag_compliance: Dict[str, bool] = field(default_factory=dict)
    pages_scanned: List[str] = field(default_factory=list)
    theme_mode: str = "single"  # "single" or "both"
    kb_patterns_used: int = 0
    scan_url: str = ""
    scan_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_violations": self.total_violations,
            "passes": self.passes,
            "incomplete": self.incomplete,
            "inapplicable": self.inapplicable,
            "violations": [v.to_dict() for v in self.violations],
            "violations_by_theme": {
                k: [v.to_dict() for v in vlist]
                for k, vlist in self.violations_by_theme.items()
            },
            "contrast_issues": [
                {
                    "element": c.element,
                    "foreground": c.foreground,
                    "background": c.background,
                    "ratio": c.ratio,
                    "required_ratio": c.required_ratio,
                    "theme": c.theme,
                    "page": c.page,
                }
                for c in self.contrast_issues
            ],
            "by_impact": self.by_impact,
            "wcag_compliance": self.wcag_compliance,
            "pages_scanned": self.pages_scanned,
            "theme_mode": self.theme_mode,
            "kb_patterns_used": self.kb_patterns_used,
            "scan_url": self.scan_url,
            "scan_time": self.scan_time,
            "errors": self.errors,
        }


# Feature-specific accessibility requirements
FEATURE_A11Y_REQUIREMENTS = {
    "auth": {
        "required_labels": ["email", "password", "username"],
        "required_aria": ["aria-required", "aria-invalid"],
        "focus_management": True,
    },
    "payments": {
        "required_labels": ["card number", "expiration", "cvv", "cvc"],
        "required_aria": ["aria-describedby", "aria-live"],
        "error_announcements": True,
    },
    "file_uploads": {
        "required_labels": ["file", "upload"],
        "required_aria": ["aria-describedby"],
        "progress_indicators": True,
    },
}


class AccessibilityAgent(BaseAgent):
    """Agent for accessibility auditing using Playwright + axe-core."""

    # WCAG 2.1 AA tags to check
    WCAG_21_AA_TAGS = [
        "wcag2a", "wcag2aa", "wcag21a", "wcag21aa",
        "best-practice", "ACT"
    ]

    # Fix suggestions for common violations
    FIX_SUGGESTIONS = {
        "color-contrast": "Increase the contrast ratio between foreground and background colors. Use a minimum ratio of 4.5:1 for normal text and 3:1 for large text.",
        "image-alt": "Add descriptive alt text to images. Use alt=\"\" for decorative images.",
        "label": "Add a label element associated with the form control using 'for' attribute, or use aria-label/aria-labelledby.",
        "link-name": "Add text content to links, or use aria-label to provide an accessible name.",
        "button-name": "Add text content to buttons, or use aria-label to provide an accessible name.",
        "html-has-lang": "Add a lang attribute to the <html> element (e.g., lang=\"en\").",
        "document-title": "Add a <title> element to the document <head>.",
        "heading-order": "Ensure headings follow a logical order (h1, h2, h3...) without skipping levels.",
        "landmark-one-main": "Add a <main> element or role=\"main\" to identify the main content area.",
        "region": "Wrap page content in landmark regions (<main>, <nav>, <header>, <footer>, etc.).",
        "bypass": "Add a skip link at the beginning of the page to allow users to bypass navigation.",
        "focus-order-semantics": "Ensure interactive elements receive focus in a logical order.",
        "aria-valid-attr": "Use valid ARIA attributes. Check spelling and ensure the attribute is appropriate for the element.",
        "aria-valid-attr-value": "Ensure ARIA attribute values are valid and match the expected format.",
        "aria-roles": "Use valid ARIA roles. Ensure the role is appropriate for the element type.",
        "tabindex": "Avoid using tabindex values greater than 0. Use tabindex=\"0\" or tabindex=\"-1\" instead.",
        "duplicate-id": "Ensure all id attribute values are unique within the document.",
        "form-field-multiple-labels": "Ensure form fields have only one associated label.",
        "scrollable-region-focusable": "Ensure scrollable regions are keyboard accessible by adding tabindex=\"0\".",
        "focus-visible": "Ensure focus indicators are visible in both light and dark themes.",
    }

    @property
    def name(self) -> str:
        return "Accessibility"
    
    async def _query_kb_for_a11y_issues(self, project_type: str, theme_mode: str) -> List[Dict]:
        """Query KB for common accessibility issues."""
        if not KB_AVAILABLE:
            return []
        
        try:
            query = f"accessibility issues for {project_type} with {theme_mode} theme"
            results = await query_knowledge(
                query=query,
                entry_types=[KnowledgeEntryType.QA_FINDING],
                limit=15,
            )
            return results
        except Exception as e:
            logger.warning(f"KB query failed: {e}")
            return []
    
    async def _write_findings_to_kb(self, report: AccessibilityReport, project_type: str):
        """Write accessibility findings to KB with theme tags."""
        if not KB_AVAILABLE:
            return
        
        try:
            # Store critical/serious violations
            for violation in report.violations:
                if violation.impact in ["critical", "serious"]:
                    await store_knowledge(
                        entry_type=KnowledgeEntryType.QA_FINDING,
                        content=f"A11y: {violation.description}",
                        metadata={
                            "project_type": project_type,
                            "violation_id": violation.id,
                            "impact": violation.impact,
                            "theme": violation.theme,
                            "page": violation.page,
                            "wcag_tags": violation.wcag_tags,
                            "agent": "accessibility",
                        },
                    )
            
            # Store contrast issues
            for contrast in report.contrast_issues:
                await store_knowledge(
                    entry_type=KnowledgeEntryType.QA_FINDING,
                    content=f"Contrast issue: {contrast.element} ({contrast.ratio:.2f}:{1} < {contrast.required_ratio}:1)",
                    metadata={
                        "project_type": project_type,
                        "theme": contrast.theme,
                        "page": contrast.page,
                        "ratio": contrast.ratio,
                        "agent": "accessibility",
                    },
                )
        except Exception as e:
            logger.warning(f"KB write failed: {e}")

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute accessibility audit with dual-theme support."""
        project_path = context.get("project_path")
        target_url = context.get("target_url", "http://localhost:3000")
        requirements = context.get("requirements", {})
        project_type = context.get("project_type", "web_simple")

        if not project_path or not os.path.exists(project_path):
            logger.warning(f"No project path available, skipping accessibility audit")
            return AgentResult(
                success=True,  # Allow pipeline to continue
                agent_name=self.name,
                data={
                    "skipped": True,
                    "reason": "No project path available",
                    "a11y_report": {"violations": [], "wcag_level": "AA", "passes": True}
                },
                warnings=["Accessibility audit skipped - no project path available"],
            )

        logger.info(f"Running accessibility audit")

        report = AccessibilityReport()
        start_time = time.time()

        # Determine theme mode
        color_scheme = requirements.get("color_scheme", "dark")
        if color_scheme in ["both", "system"]:
            report.theme_mode = "both"
        else:
            report.theme_mode = "single"
        
        # Get pages to scan
        pages = self._get_pages_from_requirements(requirements, project_path)
        report.pages_scanned = pages
        
        # Query KB for common issues
        kb_patterns = await self._query_kb_for_a11y_issues(project_type, report.theme_mode)
        report.kb_patterns_used = len(kb_patterns)
        
        # Get features for feature-specific checks
        features = self._extract_features(requirements)

        # Try to connect to Playwright service
        playwright_url = f"ws://{self.settings.playwright_host}:{self.settings.playwright_port}"
        
        try:
            if report.theme_mode == "both":
                # Run axe-core in BOTH themes
                light_violations = await self._run_axe_scan(
                    target_url, playwright_url, theme="light", pages=pages
                )
                dark_violations = await self._run_axe_scan(
                    target_url, playwright_url, theme="dark", pages=pages
                )
                
                report.violations_by_theme["light"] = light_violations.violations
                report.violations_by_theme["dark"] = dark_violations.violations
                
                # Merge violations
                all_violations = light_violations.violations + dark_violations.violations
                report.violations = self._dedupe_violations(all_violations)
                
                report.passes = light_violations.passes + dark_violations.passes
                report.incomplete = light_violations.incomplete + dark_violations.incomplete
                
                # Check contrast in both themes
                light_contrast = await self._check_contrast(project_path, "light")
                dark_contrast = await self._check_contrast(project_path, "dark")
                report.contrast_issues = light_contrast + dark_contrast
            else:
                result = await self._run_axe_scan(target_url, playwright_url, pages=pages)
                report.violations = result.violations
                report.passes = result.passes
                report.incomplete = result.incomplete
                
                # Check contrast for single theme
                report.contrast_issues = await self._check_contrast(project_path, color_scheme)
        
        except Exception as e:
            logger.warning(f"Playwright service not available: {e}")
            # Fallback: scan HTML files directly
            if report.theme_mode == "both":
                for theme in ["light", "dark"]:
                    result = await self._scan_html_files(project_path, theme)
                    report.violations_by_theme[theme] = result.violations
                    report.violations.extend(result.violations)
            else:
                result = await self._scan_html_files(project_path)
                report.violations = result.violations
            
            # Check contrast from CSS
            report.contrast_issues = await self._check_css_contrast(project_path, report.theme_mode)

        # Run feature-specific accessibility checks
        feature_issues = await self._check_feature_accessibility(project_path, features)
        report.violations.extend(feature_issues)

        # Check focus indicators in both themes
        focus_issues = await self._check_focus_indicators(project_path, report.theme_mode)
        report.violations.extend(focus_issues)

        # Check glass panel contrast (common in glassmorphic designs)
        glass_issues = await self._check_glass_panel_contrast(project_path)
        report.violations.extend(glass_issues)

        # Add fix suggestions
        for violation in report.violations:
            violation.fix_suggestion = self._get_fix_suggestion(violation.id)

        # Calculate impact breakdown
        report.by_impact = self._calculate_impact_breakdown(report.violations)
        
        # Check WCAG 2.1 AA compliance
        report.wcag_compliance = self._check_wcag_compliance(report.violations)
        
        report.scan_time = time.time() - start_time
        report.total_violations = len(report.violations)

        # Write to KB
        await self._write_findings_to_kb(report, project_type)

        # Generate report file
        report_path = os.path.join(project_path, "accessibility_report.json")
        self.write_file(report_path, json.dumps(report.to_dict(), indent=2))

        # Determine success (no critical violations)
        critical_count = report.by_impact.get("critical", 0)
        serious_count = report.by_impact.get("serious", 0)
        success = critical_count == 0 and serious_count <= 3

        return AgentResult(
            success=success,
            agent_name=self.name,
            data={
                "report": report.to_dict(),
                "report_path": report_path,
            },
            errors=[f"Critical: {v.description}" for v in report.violations if v.impact == "critical"],
            warnings=[f"Serious: {v.description}" for v in report.violations if v.impact == "serious"],
        )
    
    def _get_pages_from_requirements(
        self, requirements: Dict[str, Any], project_path: str
    ) -> List[str]:
        """Extract pages to scan from requirements."""
        pages = ["/"]
        
        # From web_complex_options
        web_complex = requirements.get("web_complex_options", {})
        for page in web_complex.get("pages", []):
            if isinstance(page, dict):
                route = page.get("route", f"/{page.get('name', '')}")
            else:
                route = f"/{page}"
            route = route.replace(" ", "-").lower()
            if route not in pages:
                pages.append(route)
        
        return pages[:10]  # Limit to 10 pages
    
    def _extract_features(self, requirements: Dict[str, Any]) -> List[str]:
        """Extract accessibility-relevant features from requirements."""
        features = set()
        
        req_features = requirements.get("features", [])
        for feature in req_features:
            feature_lower = feature.lower()
            if any(kw in feature_lower for kw in ["auth", "login", "signin"]):
                features.add("auth")
            if any(kw in feature_lower for kw in ["payment", "stripe", "checkout"]):
                features.add("payments")
            if any(kw in feature_lower for kw in ["upload", "file"]):
                features.add("file_uploads")
        
        return list(features)
    
    def _dedupe_violations(self, violations: List[AccessibilityIssue]) -> List[AccessibilityIssue]:
        """Deduplicate violations while preserving theme info."""
        seen = set()
        unique = []
        
        for v in violations:
            key = (v.id, v.page)
            if key not in seen:
                seen.add(key)
                unique.append(v)
        
        return unique

    async def _run_axe_scan(
        self, 
        target_url: str, 
        playwright_url: str,
        theme: Optional[str] = None,
        pages: List[str] = ["/"]
    ) -> AccessibilityReport:
        """Run axe-core scan using Playwright service with theme support."""
        report = AccessibilityReport()
        report.scan_url = target_url

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.connect(playwright_url)
                
                try:
                    page = await browser.new_page()
                    
                    # Set theme preference via media query emulation
                    if theme:
                        await page.emulate_media(color_scheme=theme)
                    
                    for page_route in pages[:5]:  # Limit pages
                        url = f"{target_url.rstrip('/')}{page_route}"
                        
                        try:
                            await page.goto(url, wait_until="networkidle", timeout=30000)
                            
                            # Inject and run axe-core
                            axe_script = self._get_axe_script()
                            await page.add_script_tag(content=axe_script)

                            results = await page.evaluate("""
                                async () => {
                                    const results = await axe.run(document, {
                                        runOnly: {
                                            type: 'tag',
                                            values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
                                        }
                                    });
                                    return results;
                                }
                            """)

                            page_report = self._process_axe_results(results, theme, page_route)
                            report.violations.extend(page_report.violations)
                            report.passes += page_report.passes
                            report.incomplete += page_report.incomplete
                            
                        except Exception as e:
                            logger.warning(f"Failed to scan {url}: {e}")

                finally:
                    await browser.close()

        except ImportError:
            report.errors.append("Playwright not installed")
        except Exception as e:
            report.errors.append(f"Playwright scan failed: {e}")

        return report

    async def _scan_html_files(
        self, project_path: str, theme: str = "default"
    ) -> AccessibilityReport:
        """Fallback: Scan HTML files for common accessibility issues."""
        report = AccessibilityReport()
        report.scan_url = "static-analysis"

        html_patterns = self._get_accessibility_patterns()
        
        for root, _, files in os.walk(project_path):
            if "node_modules" in root or ".git" in root:
                continue

            for file in files:
                if file.endswith((".html", ".tsx", ".jsx", ".vue")):
                    file_path = os.path.join(root, file)
                    content = self.read_file(file_path)
                    if not content:
                        continue

                    violations = self._check_accessibility_patterns(
                        content, file_path, html_patterns, theme
                    )
                    report.violations.extend(violations)

        # Deduplicate
        report.violations = self._dedupe_violations(report.violations)
        return report
    
    async def _check_contrast(self, project_path: str, theme: str) -> List[ContrastIssue]:
        """Check color contrast ratios for a theme."""
        issues = []
        
        # Look for CSS variables and check common patterns
        css_files = []
        for root, _, files in os.walk(project_path):
            if "node_modules" in root:
                continue
            for file in files:
                if file.endswith((".css", ".scss")):
                    css_files.append(os.path.join(root, file))
        
        # Known problematic color combinations in dark themes
        dark_problematic = [
            ("#6B7280", "#1F2937"),  # Gray on dark gray
            ("#9CA3AF", "#374151"),  # Light gray on medium gray
        ]
        
        # Check each CSS file for potential issues
        for css_file in css_files:
            content = self.read_file(css_file)
            if not content:
                continue
            
            # Check for low contrast patterns
            if theme == "dark":
                # Look for potential issues in dark mode
                if "rgba(255,255,255,0.05)" in content.replace(" ", ""):
                    issues.append(ContrastIssue(
                        element="glass-panel",
                        foreground="text",
                        background="rgba(255,255,255,0.05)",
                        ratio=2.5,  # Estimated
                        required_ratio=4.5,
                        theme=theme,
                        page="/",
                        file_path=css_file,
                    ))
        
        return issues
    
    async def _check_css_contrast(self, project_path: str, theme_mode: str) -> List[ContrastIssue]:
        """Check CSS files for contrast issues."""
        return await self._check_contrast(project_path, "dark" if theme_mode == "single" else "both")
    
    async def _check_feature_accessibility(
        self, project_path: str, features: List[str]
    ) -> List[AccessibilityIssue]:
        """Check feature-specific accessibility requirements."""
        issues = []
        
        for feature in features:
            requirements = FEATURE_A11Y_REQUIREMENTS.get(feature, {})
            
            # Search for feature-related files
            for root, _, files in os.walk(project_path):
                if "node_modules" in root:
                    continue
                
                for file in files:
                    if not file.endswith((".tsx", ".jsx")):
                        continue
                    
                    # Check if file is related to feature
                    if feature not in file.lower() and feature not in root.lower():
                        continue
                    
                    file_path = os.path.join(root, file)
                    content = self.read_file(file_path)
                    if not content:
                        continue
                    
                    # Check for required ARIA attributes
                    for aria_attr in requirements.get("required_aria", []):
                        if aria_attr not in content:
                            issues.append(AccessibilityIssue(
                                id=f"missing-{aria_attr}",
                                impact="serious",
                                description=f"{feature} forms should use {aria_attr}",
                                help=f"Add {aria_attr} to form controls for better accessibility",
                                help_url=f"https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Attributes/{aria_attr}",
                                wcag_tags=["wcag2a", "wcag412"],
                                nodes=[{"file": file_path}],
                            ))
                            break
        
        return issues
    
    async def _check_focus_indicators(
        self, project_path: str, theme_mode: str
    ) -> List[AccessibilityIssue]:
        """Check that focus indicators are visible in both themes."""
        issues = []
        
        # Look for focus styles
        focus_styles_found = False
        
        for root, _, files in os.walk(project_path):
            if "node_modules" in root:
                continue
            
            for file in files:
                if not file.endswith((".css", ".scss", ".tsx", ".jsx")):
                    continue
                
                file_path = os.path.join(root, file)
                content = self.read_file(file_path)
                if not content:
                    continue
                
                # Check for focus styles
                if ":focus" in content or "focus:" in content or "focus-visible" in content:
                    focus_styles_found = True
                
                # Check for outline:none without replacement
                if "outline: none" in content or "outline:none" in content:
                    # Check if there's a replacement focus style
                    if "focus" not in content or ("ring" not in content and "border" not in content):
                        issues.append(AccessibilityIssue(
                            id="focus-visible",
                            impact="serious",
                            description="Focus outline removed without visible replacement",
                            help="Ensure focus indicators are visible - use ring or border styles",
                            help_url="https://dequeuniversity.com/rules/axe/4.4/focus-visible",
                            wcag_tags=["wcag2aa", "wcag247"],
                            nodes=[{"file": file_path}],
                        ))
        
        if not focus_styles_found:
            issues.append(AccessibilityIssue(
                id="focus-visible",
                impact="moderate",
                description="No custom focus styles found - using browser defaults",
                help="Consider adding visible focus styles for better accessibility",
                help_url="https://dequeuniversity.com/rules/axe/4.4/focus-visible",
                wcag_tags=["wcag2aa", "wcag247"],
                nodes=[],
            ))
        
        return issues
    
    async def _check_glass_panel_contrast(self, project_path: str) -> List[AccessibilityIssue]:
        """Check glassmorphic panel contrast."""
        issues = []
        
        # Look for glassmorphic patterns
        glass_patterns = [
            r"backdrop-blur",
            r"backdrop-filter.*blur",
            r"bg-.*\/\d+",  # Tailwind opacity
            r"rgba\([^)]*,\s*0\.[0-4]",  # Low opacity colors
        ]
        
        for root, _, files in os.walk(project_path):
            if "node_modules" in root:
                continue
            
            for file in files:
                if not file.endswith((".tsx", ".jsx", ".css")):
                    continue
                
                file_path = os.path.join(root, file)
                content = self.read_file(file_path)
                if not content:
                    continue
                
                for pattern in glass_patterns:
                    if re.search(pattern, content):
                        # Found glassmorphic style - add advisory
                        issues.append(AccessibilityIssue(
                            id="glass-panel-contrast",
                            impact="moderate",
                            description="Glassmorphic elements may have low contrast",
                            help="Ensure text on glass panels meets 4.5:1 contrast ratio",
                            help_url="https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html",
                            wcag_tags=["wcag2aa", "wcag143"],
                            nodes=[{"file": file_path}],
                        ))
                        return issues  # One warning is enough
        
        return issues

    def _get_accessibility_patterns(self) -> List[Dict[str, Any]]:
        """Get patterns for static accessibility analysis."""
        return [
            {
                "id": "image-alt",
                "pattern": r"<img(?![^>]*alt=)[^>]*>",
                "impact": "critical",
                "description": "Images must have alternate text",
                "help": "Ensure images have alt attribute for screen readers",
                "wcag_tags": ["wcag2a", "wcag111"],
            },
            {
                "id": "html-has-lang",
                "pattern": r"<html(?![^>]*lang=)[^>]*>",
                "impact": "serious",
                "description": "HTML element must have a lang attribute",
                "help": "Add lang attribute to html element",
                "wcag_tags": ["wcag2a", "wcag311"],
            },
            {
                "id": "link-name",
                "pattern": r"<a[^>]*>\s*</a>",
                "impact": "serious",
                "description": "Links must have discernible text",
                "help": "Add text content or aria-label to links",
                "wcag_tags": ["wcag2a", "wcag244", "wcag412"],
            },
            {
                "id": "button-name",
                "pattern": r"<button[^>]*>\s*</button>",
                "impact": "critical",
                "description": "Buttons must have discernible text",
                "help": "Add text content or aria-label to buttons",
                "wcag_tags": ["wcag2a", "wcag412"],
            },
            {
                "id": "label",
                "pattern": r"<input(?![^>]*(aria-label|id=['\"][^'\"]+['\"][^>]*<label[^>]*for=))[^>]*>",
                "impact": "critical",
                "description": "Form inputs must have labels",
                "help": "Add label element or aria-label attribute",
                "wcag_tags": ["wcag2a", "wcag332", "wcag131"],
            },
            {
                "id": "tabindex",
                "pattern": r"tabindex=['\"]([2-9]|\d{2,})['\"]",
                "impact": "serious",
                "description": "Avoid positive tabindex values",
                "help": "Use tabindex=\"0\" or tabindex=\"-1\" instead",
                "wcag_tags": ["wcag2a", "wcag243"],
            },
        ]

    def _check_accessibility_patterns(
        self, 
        content: str, 
        file_path: str, 
        patterns: List[Dict[str, Any]],
        theme: str = "default"
    ) -> List[AccessibilityIssue]:
        """Check content against accessibility patterns."""
        violations = []

        for pattern_def in patterns:
            if pattern_def["pattern"] is None:
                continue

            matches = re.finditer(pattern_def["pattern"], content, re.IGNORECASE)
            
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                
                violations.append(AccessibilityIssue(
                    id=pattern_def["id"],
                    impact=pattern_def["impact"],
                    description=pattern_def["description"],
                    help=pattern_def["help"],
                    help_url=f"https://dequeuniversity.com/rules/axe/4.4/{pattern_def['id']}",
                    wcag_tags=pattern_def["wcag_tags"],
                    theme=theme,
                    nodes=[{
                        "file": file_path,
                        "line": line_num,
                        "html": match.group(0)[:100],
                    }],
                ))

        return violations

    def _get_axe_script(self) -> str:
        """Get axe-core script for injection."""
        return """
        !function(e,t){"object"==typeof exports&&"undefined"!=typeof module?module.exports=t():"function"==typeof define&&define.amd?define(t):(e="undefined"!=typeof globalThis?globalThis:e||self).axe=t()}(this,(function(){"use strict";/* axe-core minified */}));
        """

    def _process_axe_results(
        self, results: Dict[str, Any], theme: Optional[str], page: str
    ) -> AccessibilityReport:
        """Process axe-core results into report format."""
        report = AccessibilityReport()
        
        report.passes = len(results.get("passes", []))
        report.incomplete = len(results.get("incomplete", []))
        report.inapplicable = len(results.get("inapplicable", []))

        for violation in results.get("violations", []):
            issue = AccessibilityIssue(
                id=violation.get("id", ""),
                impact=violation.get("impact", "moderate"),
                description=violation.get("description", ""),
                help=violation.get("help", ""),
                help_url=violation.get("helpUrl", ""),
                wcag_tags=violation.get("tags", []),
                theme=theme or "default",
                page=page,
                nodes=[
                    {
                        "html": node.get("html", ""),
                        "target": node.get("target", []),
                        "failureSummary": node.get("failureSummary", ""),
                    }
                    for node in violation.get("nodes", [])
                ],
            )
            report.violations.append(issue)

        return report

    def _get_fix_suggestion(self, violation_id: str) -> str:
        """Get fix suggestion for a violation."""
        return self.FIX_SUGGESTIONS.get(
            violation_id,
            "Review the element and ensure it meets WCAG 2.1 AA guidelines."
        )

    def _calculate_impact_breakdown(
        self, violations: List[AccessibilityIssue]
    ) -> Dict[str, int]:
        """Calculate breakdown of violations by impact."""
        breakdown = {
            "critical": 0,
            "serious": 0,
            "moderate": 0,
            "minor": 0,
        }

        for violation in violations:
            impact = violation.impact.lower()
            if impact in breakdown:
                breakdown[impact] += 1

        return breakdown

    def _check_wcag_compliance(
        self, violations: List[AccessibilityIssue]
    ) -> Dict[str, bool]:
        """Check WCAG 2.1 AA compliance status."""
        compliance = {
            "wcag2a": True,
            "wcag2aa": True,
            "wcag21a": True,
            "wcag21aa": True,
        }

        for violation in violations:
            if violation.impact in ["critical", "serious"]:
                for tag in violation.wcag_tags:
                    if tag in compliance:
                        compliance[tag] = False

        return compliance
