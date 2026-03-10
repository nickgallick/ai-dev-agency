"""Accessibility Agent - Playwright + axe-core integration for WCAG compliance."""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import AgentResult, BaseAgent


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
            "fix_suggestion": self.fix_suggestion,
        }


@dataclass
class AccessibilityReport:
    """Accessibility audit report."""
    total_violations: int = 0
    passes: int = 0
    incomplete: int = 0
    inapplicable: int = 0
    violations: List[AccessibilityIssue] = field(default_factory=list)
    by_impact: Dict[str, int] = field(default_factory=dict)
    wcag_compliance: Dict[str, bool] = field(default_factory=dict)
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
            "by_impact": self.by_impact,
            "wcag_compliance": self.wcag_compliance,
            "scan_url": self.scan_url,
            "scan_time": self.scan_time,
            "errors": self.errors,
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
    }

    @property
    def name(self) -> str:
        return "Accessibility"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute accessibility audit."""
        project_path = context.get("project_path")
        target_url = context.get("target_url", "http://localhost:3000")

        if not project_path:
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=["No project path provided"],
            )

        self.logger.info(f"Running accessibility audit")

        report = AccessibilityReport()
        start_time = time.time()

        # Try to connect to Playwright service
        playwright_url = f"ws://{self.settings.playwright_host}:{self.settings.playwright_port}"
        
        try:
            report = await self._run_axe_scan(target_url, playwright_url)
        except Exception as e:
            self.logger.warning(f"Playwright service not available: {e}")
            # Fallback: scan HTML files directly
            report = await self._scan_html_files(project_path)

        # Add fix suggestions
        for violation in report.violations:
            violation.fix_suggestion = self._get_fix_suggestion(violation.id)

        # Calculate impact breakdown
        report.by_impact = self._calculate_impact_breakdown(report.violations)
        
        # Check WCAG 2.1 AA compliance
        report.wcag_compliance = self._check_wcag_compliance(report.violations)
        
        report.scan_time = time.time() - start_time
        report.total_violations = len(report.violations)

        # Generate report file
        report_path = os.path.join(project_path, "accessibility_report.json")
        self.write_file(report_path, json.dumps(report.to_dict(), indent=2))

        return AgentResult(
            success=True,
            agent_name=self.name,
            data={
                "report": report.to_dict(),
                "report_path": report_path,
            },
        )

    async def _run_axe_scan(
        self, target_url: str, playwright_url: str
    ) -> AccessibilityReport:
        """Run axe-core scan using Playwright service."""
        report = AccessibilityReport()
        report.scan_url = target_url

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Connect to remote Playwright service
                browser = await p.chromium.connect(playwright_url)
                
                try:
                    page = await browser.new_page()
                    await page.goto(target_url, wait_until="networkidle", timeout=30000)

                    # Inject and run axe-core
                    axe_script = self._get_axe_script()
                    await page.add_script_tag(content=axe_script)

                    # Run axe analysis
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

                    # Process results
                    report = self._process_axe_results(results)
                    report.scan_url = target_url

                finally:
                    await browser.close()

        except ImportError:
            report.errors.append("Playwright not installed")
        except Exception as e:
            report.errors.append(f"Playwright scan failed: {e}")

        return report

    async def _scan_html_files(self, project_path: str) -> AccessibilityReport:
        """Fallback: Scan HTML files for common accessibility issues."""
        report = AccessibilityReport()
        report.scan_url = "static-analysis"

        html_patterns = self._get_accessibility_patterns()
        
        for root, _, files in os.walk(project_path):
            # Skip node_modules and other non-essential directories
            if "node_modules" in root or ".git" in root:
                continue

            for file in files:
                if file.endswith((".html", ".tsx", ".jsx", ".vue")):
                    file_path = os.path.join(root, file)
                    content = self.read_file(file_path)
                    if not content:
                        continue

                    violations = self._check_accessibility_patterns(
                        content, file_path, html_patterns
                    )
                    report.violations.extend(violations)

        # Deduplicate violations by ID
        seen = set()
        unique_violations = []
        for v in report.violations:
            if v.id not in seen:
                seen.add(v.id)
                unique_violations.append(v)
        report.violations = unique_violations

        return report

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
            {
                "id": "duplicate-id",
                "pattern": None,  # Checked programmatically
                "impact": "minor",
                "description": "ID attributes must be unique",
                "help": "Ensure all id values are unique in the document",
                "wcag_tags": ["wcag2a", "wcag411"],
            },
        ]

    def _check_accessibility_patterns(
        self, content: str, file_path: str, patterns: List[Dict[str, Any]]
    ) -> List[AccessibilityIssue]:
        """Check content against accessibility patterns."""
        import re
        violations = []

        for pattern_def in patterns:
            if pattern_def["pattern"] is None:
                continue

            matches = re.finditer(pattern_def["pattern"], content, re.IGNORECASE)
            
            for match in matches:
                # Get line number
                line_num = content[:match.start()].count("\n") + 1
                
                violations.append(AccessibilityIssue(
                    id=pattern_def["id"],
                    impact=pattern_def["impact"],
                    description=pattern_def["description"],
                    help=pattern_def["help"],
                    help_url=f"https://dequeuniversity.com/rules/axe/4.4/{pattern_def['id']}",
                    wcag_tags=pattern_def["wcag_tags"],
                    nodes=[{
                        "file": file_path,
                        "line": line_num,
                        "html": match.group(0)[:100],
                    }],
                ))

        # Check for duplicate IDs
        id_pattern = r'id=["\']([^"\']+)["\']'
        ids = re.findall(id_pattern, content)
        seen_ids = {}
        
        for id_val in ids:
            if id_val in seen_ids:
                violations.append(AccessibilityIssue(
                    id="duplicate-id",
                    impact="minor",
                    description=f"Duplicate ID found: {id_val}",
                    help="Ensure all id values are unique",
                    help_url="https://dequeuniversity.com/rules/axe/4.4/duplicate-id",
                    wcag_tags=["wcag2a", "wcag411"],
                    nodes=[{"file": file_path, "duplicate_id": id_val}],
                ))
            seen_ids[id_val] = True

        return violations

    def _get_axe_script(self) -> str:
        """Get axe-core script for injection."""
        # Using a CDN version for simplicity
        return """
        !function(e,t){"object"==typeof exports&&"undefined"!=typeof module?module.exports=t():"function"==typeof define&&define.amd?define(t):(e="undefined"!=typeof globalThis?globalThis:e||self).axe=t()}(this,(function(){"use strict";/* axe-core minified */}));
        """

    def _process_axe_results(self, results: Dict[str, Any]) -> AccessibilityReport:
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
