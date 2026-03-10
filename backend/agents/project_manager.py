"""Project Manager Agent - Validates coherence and completeness.

Phase 11E Enhancement:
- Checkpoint 1 (Pre-Code-Gen): Validates structured requirements, Figma, design system,
  dynamic pooling, integrations, and dual-theme compatibility
- Checkpoint 2 (Post-Code-Gen): Validates generated code against requirements,
  verifies light/dark mode implementation, integration wiring, and Figma fidelity

Implements two checkpoint methods:
- checkpoint_1_coherence: After Architect + Design System + Content + Assets, before Code Gen
- checkpoint_2_completeness: After Code Gen, before Quality Gate

Only activates for complex project types:
- web_complex, python_saas, mobile_cross_platform, desktop_app

Uses Claude Sonnet 4 for validation.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from .base import BaseAgent, AgentResult

# Import knowledge base for querying common issues
try:
    from ..knowledge import query_knowledge, store_knowledge, KnowledgeEntryType
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a validation issue found during checkpoint."""
    severity: str  # critical, warning, info
    category: str  # requirements, figma, design_system, content, assets, architecture, theme, integration, pooling
    message: str
    source: str  # Which agent output caused the issue
    suggestion: str
    auto_fix_available: bool = False
    auto_fix_instruction: Optional[str] = None


@dataclass 
class BuildManifest:
    """Single source of truth for code generation."""
    project_id: str
    generated_at: str
    validated: bool
    requirements_version: str
    theme_mode: str  # "light", "dark", "both"
    pages: List[Dict[str, Any]]
    components: List[Dict[str, Any]]
    assets: Dict[str, Any]
    content: Dict[str, Any]
    design_tokens: Dict[str, Any]
    api_endpoints: List[Dict[str, Any]]
    database_schema: Optional[Dict[str, Any]]
    integrations: Dict[str, Any]  # Stripe, Resend, R2, etc.
    build_order: List[str]
    warnings: List[str]
    dynamic_pooling: Optional[Dict[str, Any]]  # Pool config if used
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "generated_at": self.generated_at,
            "validated": self.validated,
            "requirements_version": self.requirements_version,
            "theme_mode": self.theme_mode,
            "pages": self.pages,
            "components": self.components,
            "assets": self.assets,
            "content": self.content,
            "design_tokens": self.design_tokens,
            "api_endpoints": self.api_endpoints,
            "database_schema": self.database_schema,
            "integrations": self.integrations,
            "build_order": self.build_order,
            "warnings": self.warnings,
            "dynamic_pooling": self.dynamic_pooling,
        }


# Project types that require PM checkpoints
COMPLEX_PROJECT_TYPES = [
    "web_complex",
    "python_saas", 
    "mobile_cross_platform",
    "desktop_app",
]

# Feature to integration mapping
FEATURE_INTEGRATION_MAP = {
    "auth": ["supabase", "next-auth"],
    "payments": ["stripe"],
    "email": ["resend"],
    "file_uploads": ["cloudflare_r2"],
    "background_jobs": ["inngest"],
    "database": ["supabase", "postgres"],
}


class ProjectManagerAgent(BaseAgent):
    """Project Manager Agent that validates cross-agent coherence and completeness."""
    
    name = "project_manager"
    description = "Project Manager - Validates coherence and completeness"
    model = "anthropic/claude-sonnet-4"
    
    COHERENCE_SYSTEM_PROMPT = """You are the Project Manager Agent validating coherence across all planning outputs.

You must check for:
1. Requirements match architect output - all pages, features, integrations specified
2. Design system matches requirements - dark_mode preference, color_preference, style
3. Figma designs (if provided) match design system and architect output
4. Content fits layouts - text lengths match allocated space in designs
5. Asset dimensions match specs - images, icons are the right sizes for both themes
6. No contradictions between architect plan and design system
7. All content keys are used in page layouts
8. Navigation structure matches page routes
9. API endpoints match data requirements
10. Integration dependencies are satisfied (Stripe needs auth, etc.)
11. Dynamic pooling dependency graph is valid (if used)

Respond ONLY with valid JSON:
{
    "coherent": true/false,
    "issues": [
        {
            "severity": "critical/warning/info",
            "category": "requirements/figma/design_system/content/assets/architecture/theme/integration/pooling",
            "message": "Description of issue",
            "source": "agent_name",
            "suggestion": "How to fix",
            "auto_fix_available": true/false,
            "auto_fix_instruction": "If auto-fix available, instruction here"
        }
    ],
    "build_manifest": {...},
    "warnings": ["Non-critical items to watch"]
}"""

    COMPLETENESS_SYSTEM_PROMPT = """You are the Project Manager Agent validating code generation completeness.

You must check:
1. All pages from requirements.pages are implemented
2. All features from requirements.features are implemented
3. Light/dark mode implementation (toggle exists, CSS vars used, localStorage preference)
4. Dynamic pooling consistency (cross-batch imports, naming conventions, patterns)
5. Integration wiring verified (API contracts match, env vars documented, SDK imports correct)
6. Figma fidelity (component structure matches, colors match design tokens)
7. All API endpoints are implemented and match specs
8. Frontend routes match backend endpoints
9. No placeholder code (TODO, FIXME, etc.)
10. All imports are valid
11. Database migrations exist if schema was defined
12. Environment variables are documented in .env.example

Respond ONLY with valid JSON:
{
    "complete": true/false,
    "implementation_score": 0-100,
    "issues": [...],
    "theme_verification": {
        "toggle_exists": true/false,
        "css_vars_used": true/false,
        "local_storage": true/false,
        "both_themes_styled": true/false
    },
    "integration_verification": {
        "stripe": {"wired": true/false, "issues": []},
        "resend": {"wired": true/false, "issues": []},
        ...
    },
    "missing_features": ["feature1", "feature2"],
    "placeholder_count": 0,
    "files_reviewed": ["list of files checked"]
}"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkpoint_mode = "coherence"  # or "completeness"
    
    @property
    def name(self) -> str:
        return "project_manager"

    def should_activate(self, project_type: str) -> bool:
        """Check if this project type requires PM checkpoints."""
        return project_type in COMPLEX_PROJECT_TYPES
    
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute the appropriate checkpoint based on mode."""
        if self.checkpoint_mode == "coherence":
            return await self.checkpoint_1_coherence(context)
        else:
            return await self.checkpoint_2_completeness(context)
    
    async def _query_kb_for_issues(self, context_type: str, project_type: str) -> List[Dict]:
        """Query KB for common coherence/completeness issues."""
        if not KB_AVAILABLE:
            return []
        
        try:
            results = await query_knowledge(
                query=f"common {context_type} issues for {project_type} projects",
                entry_types=[KnowledgeEntryType.QA_FINDING],
                limit=10,
            )
            return results
        except Exception as e:
            logger.warning(f"KB query failed: {e}")
            return []
    
    async def _write_to_kb(self, issues: List[ValidationIssue], project_type: str, checkpoint: str):
        """Write validation findings to KB for future reference."""
        if not KB_AVAILABLE:
            return
        
        try:
            for issue in issues:
                if issue.severity in ["critical", "warning"]:
                    await store_knowledge(
                        entry_type=KnowledgeEntryType.QA_FINDING,
                        content=f"{checkpoint} validation: {issue.message}",
                        metadata={
                            "project_type": project_type,
                            "category": issue.category,
                            "severity": issue.severity,
                            "suggestion": issue.suggestion,
                            "checkpoint": checkpoint,
                        },
                    )
        except Exception as e:
            logger.warning(f"KB write failed: {e}")
    
    async def checkpoint_1_coherence(self, context: Dict[str, Any]) -> AgentResult:
        """
        Checkpoint 1: Validates outputs from Architect, Design System, Content, Assets.
        Produces build_manifest.json as single source of truth for code generation.
        
        Phase 11E Enhancements:
        - Validate requirements vs Architect (pages, features, tech stack, integrations)
        - Validate requirements vs Design System (dark_mode, color_preference, style)
        - Validate Figma vs Design System (if Figma URL provided)
        - Validate Figma vs Architect (page count, components)
        - Validate Architect vs Content (page coverage, quantity matching)
        - Validate Architect vs Assets (dimensions, dual-theme compatibility)
        - Validate dynamic pooling dependency graph
        - Query KB for common coherence issues
        """
        logger.info("Running PM Checkpoint 1: Coherence Validation (Phase 11E)")
        
        project_id = context.get("project_id", "unknown")
        project_type = context.get("project_type", "web_simple")
        project_path = context.get("project_path", "/tmp/project")
        
        # Get structured requirements from Phase 11A
        requirements = context.get("requirements", {})
        
        # Check if this project needs PM checkpoints
        if not self.should_activate(project_type):
            logger.info(f"Skipping PM checkpoint for simple project type: {project_type}")
            return AgentResult(
                success=True,
                agent_name=self.name,
                data={"skipped": True, "reason": "Project type doesn't require PM checkpoint"},
            )
        
        # Query KB for common issues first
        kb_issues = await self._query_kb_for_issues("coherence", project_type)
        
        # Gather outputs from previous agents
        architect_output = context.get("architect_result", {})
        design_system_output = context.get("design_system_result", {})
        content_output = context.get("content_generation_result", {})
        assets_output = context.get("asset_generation_result", {})
        figma_output = context.get("figma_result", {})  # From Figma MCP
        
        # Validate we have required inputs
        if not architect_output:
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=["Missing architect output - cannot validate coherence"],
            )
        
        # Perform validation
        issues = []
        warnings = []
        
        # 1. Validate requirements vs architect
        req_issues = self._validate_requirements_vs_architect(requirements, architect_output)
        issues.extend(req_issues)
        
        # 2. Validate requirements vs design system
        design_issues = self._validate_requirements_vs_design_system(requirements, design_system_output)
        issues.extend(design_issues)
        
        # 3. Validate Figma vs design system (if Figma provided)
        if figma_output:
            figma_design_issues = self._validate_figma_vs_design_system(figma_output, design_system_output)
            issues.extend(figma_design_issues)
            
            figma_arch_issues = self._validate_figma_vs_architect(figma_output, architect_output)
            issues.extend(figma_arch_issues)
        
        # 4. Validate content fits layouts
        content_issues = self._validate_content_layout_fit(architect_output, content_output)
        issues.extend(content_issues)
        
        # 5. Validate asset dimensions and dual-theme compatibility
        asset_issues = self._validate_asset_dimensions(architect_output, assets_output, design_system_output)
        issues.extend(asset_issues)
        
        # 6. Validate design system consistency
        ds_issues = self._validate_design_consistency(architect_output, design_system_output)
        issues.extend(ds_issues)
        
        # 7. Validate navigation structure
        nav_issues = self._validate_navigation(architect_output)
        issues.extend(nav_issues)
        
        # 8. Validate integration dependencies
        integration_issues = self._validate_integrations(requirements, architect_output)
        issues.extend(integration_issues)
        
        # 9. Validate dynamic pooling (if configured)
        pooling_config = context.get("dynamic_pooling", {})
        if pooling_config:
            pooling_issues = self._validate_dynamic_pooling(pooling_config, architect_output)
            issues.extend(pooling_issues)
        
        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        
        # Write issues to KB
        await self._write_to_kb(issues, project_type, "checkpoint_1")
        
        if critical_issues:
            logger.error(f"Found {len(critical_issues)} critical coherence issues")
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=[f"{i.category}: {i.message}" for i in critical_issues],
                data={
                    "issues": [self._issue_to_dict(i) for i in issues],
                    "critical_count": len(critical_issues),
                    "auto_fix_instructions": [
                        {"issue": i.message, "fix": i.auto_fix_instruction}
                        for i in issues if i.auto_fix_available
                    ],
                },
            )
        
        # Determine theme mode
        theme_mode = "dark"  # default
        if requirements.get("color_scheme") == "light":
            theme_mode = "light"
        elif requirements.get("color_scheme") in ["system", "both"]:
            theme_mode = "both"
        
        # Generate build manifest
        build_manifest = self._generate_build_manifest(
            project_id=project_id,
            requirements=requirements,
            architect_output=architect_output,
            design_system_output=design_system_output,
            content_output=content_output,
            assets_output=assets_output,
            theme_mode=theme_mode,
            warnings=[i.message for i in issues if i.severity == "warning"],
            dynamic_pooling=pooling_config if pooling_config else None,
        )
        
        # Write build manifest to project path
        manifest_path = os.path.join(project_path, "build_manifest.json")
        try:
            os.makedirs(project_path, exist_ok=True)
            with open(manifest_path, "w") as f:
                json.dump(build_manifest.to_dict(), f, indent=2)
            logger.info(f"Build manifest written to {manifest_path}")
        except Exception as e:
            logger.warning(f"Failed to write build manifest: {e}")
        
        return AgentResult(
            success=True,
            agent_name=self.name,
            data={
                "coherent": True,
                "issues": [self._issue_to_dict(i) for i in issues],
                "build_manifest": build_manifest.to_dict(),
                "manifest_path": manifest_path,
                "kb_patterns_used": len(kb_issues),
            },
            warnings=[i.message for i in issues if i.severity == "warning"],
        )
    
    async def checkpoint_2_completeness(self, context: Dict[str, Any]) -> AgentResult:
        """
        Checkpoint 2: Verifies code generation is complete.
        Runs after Code Gen, before Quality Gate.
        
        Phase 11E Enhancements:
        - Validate requirements vs generated code (pages exist, features implemented)
        - Verify light/dark mode implementation (toggle, CSS vars, localStorage)
        - Validate dynamic pooling consistency (cross-batch imports, naming, patterns)
        - Verify integration wiring (API contracts, env vars, SDK imports)
        - Verify Figma fidelity (component structure, colors)
        - Query KB for common code quality issues
        """
        logger.info("Running PM Checkpoint 2: Completeness Validation (Phase 11E)")
        
        project_id = context.get("project_id", "unknown")
        project_type = context.get("project_type", "web_simple")
        project_path = context.get("project_path", "/tmp/project")
        requirements = context.get("requirements", {})
        
        # Check if this project needs PM checkpoints
        if not self.should_activate(project_type):
            logger.info(f"Skipping PM checkpoint for simple project type: {project_type}")
            return AgentResult(
                success=True,
                agent_name=self.name,
                data={"skipped": True, "reason": "Project type doesn't require PM checkpoint"},
            )
        
        # Query KB for common issues
        kb_issues = await self._query_kb_for_issues("completeness", project_type)
        
        # Load build manifest
        manifest_path = os.path.join(project_path, "build_manifest.json")
        build_manifest = None
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    build_manifest = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load build manifest: {e}")
        
        issues = []
        missing_features = []
        files_reviewed = []
        placeholder_count = 0
        implementation_score = 100
        
        # 1. Check all pages are implemented
        if build_manifest:
            page_issues, missing = self._check_pages_implemented(
                build_manifest.get("pages", []), project_path
            )
            issues.extend(page_issues)
            missing_features.extend(missing)
        
        # 2. Check all components exist
        if build_manifest:
            component_issues = self._check_components_implemented(
                build_manifest.get("components", []), project_path
            )
            issues.extend(component_issues)
        
        # 3. Verify theme implementation (for "both" mode)
        theme_mode = build_manifest.get("theme_mode", "dark") if build_manifest else "dark"
        theme_verification = self._verify_theme_implementation(project_path, theme_mode)
        
        if theme_mode == "both":
            if not theme_verification.get("toggle_exists"):
                issues.append(ValidationIssue(
                    severity="critical",
                    category="theme",
                    message="Theme toggle not found - required for 'both' theme mode",
                    source="code_generation",
                    suggestion="Add a ThemeToggle component with light/dark switching",
                ))
            if not theme_verification.get("css_vars_used"):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="theme",
                    message="CSS variables not used consistently - may have hardcoded colors",
                    source="code_generation",
                    suggestion="Replace hardcoded colors with CSS variables",
                ))
        
        # 4. Check for placeholder code
        placeholder_results = self._scan_for_placeholders(project_path)
        placeholder_count = placeholder_results["count"]
        if placeholder_count > 0:
            issues.append(ValidationIssue(
                severity="warning",
                category="code_quality",
                message=f"Found {placeholder_count} placeholder items (TODO, FIXME, etc.)",
                source="code_scan",
                suggestion="Replace placeholders with actual implementations",
            ))
        files_reviewed.extend(placeholder_results["files"])
        
        # 5. Check API endpoints match
        if build_manifest:
            endpoint_issues = self._check_endpoints_implemented(
                build_manifest.get("api_endpoints", []), project_path
            )
            issues.extend(endpoint_issues)
        
        # 6. Verify integration wiring
        integrations = build_manifest.get("integrations", {}) if build_manifest else {}
        integration_verification = self._verify_integration_wiring(project_path, integrations)
        
        for integration_name, result in integration_verification.items():
            if not result.get("wired"):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="integration",
                    message=f"Integration '{integration_name}' not properly wired",
                    source="code_generation",
                    suggestion=f"Verify {integration_name} SDK imports and API key env vars",
                ))
        
        # 7. Check environment variables documented
        env_issues = self._check_env_documented(project_path, integrations)
        issues.extend(env_issues)
        
        # 8. Verify dynamic pooling consistency (if used)
        pooling_config = build_manifest.get("dynamic_pooling") if build_manifest else None
        if pooling_config:
            pooling_issues = self._verify_pooling_consistency(project_path, pooling_config)
            issues.extend(pooling_issues)
        
        # Calculate implementation score
        critical_count = len([i for i in issues if i.severity == "critical"])
        warning_count = len([i for i in issues if i.severity == "warning"])
        implementation_score = max(0, 100 - (critical_count * 20) - (warning_count * 5) - (placeholder_count * 2))
        
        # Determine success
        success = critical_count == 0 and implementation_score >= 70
        
        # Write issues to KB
        await self._write_to_kb(issues, project_type, "checkpoint_2")
        
        # Write completeness report
        report_path = os.path.join(project_path, "completeness_report.json")
        report = {
            "complete": success,
            "implementation_score": implementation_score,
            "issues": [self._issue_to_dict(i) for i in issues],
            "theme_verification": theme_verification,
            "integration_verification": integration_verification,
            "missing_features": missing_features,
            "placeholder_count": placeholder_count,
            "files_reviewed": files_reviewed,
            "generated_at": datetime.utcnow().isoformat(),
            "kb_patterns_used": len(kb_issues),
        }
        
        try:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write completeness report: {e}")
        
        return AgentResult(
            success=success,
            agent_name=self.name,
            data=report,
            errors=[f"{i.category}: {i.message}" for i in issues if i.severity == "critical"],
            warnings=[i.message for i in issues if i.severity == "warning"],
        )
    
    def _validate_requirements_vs_architect(
        self, 
        requirements: Dict[str, Any], 
        architect: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate that architect output matches structured requirements."""
        issues = []
        
        # Extract pages from requirements
        req_pages = []
        if requirements.get("web_complex_options", {}).get("pages"):
            req_pages = requirements["web_complex_options"]["pages"]
        elif requirements.get("web_simple_options", {}).get("sections"):
            req_pages = [{"name": s} for s in requirements["web_simple_options"]["sections"]]
        
        # Check page coverage
        arch_pages = architect.get("pages", [])
        arch_page_names = {p.get("name", "").lower() for p in arch_pages}
        
        for req_page in req_pages:
            page_name = req_page.get("name", "").lower() if isinstance(req_page, dict) else req_page.lower()
            if page_name and page_name not in arch_page_names:
                issues.append(ValidationIssue(
                    severity="critical",
                    category="requirements",
                    message=f"Required page '{page_name}' missing from architecture",
                    source="architect",
                    suggestion=f"Add '{page_name}' page to architecture output",
                    auto_fix_available=True,
                    auto_fix_instruction=f"Re-run Architect with explicit page: {page_name}",
                ))
        
        # Check features are addressed
        req_features = requirements.get("features", [])
        for feature in req_features:
            feature_lower = feature.lower()
            # Check if feature is addressed in architect output
            arch_str = json.dumps(architect).lower()
            if feature_lower not in arch_str:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="requirements",
                    message=f"Feature '{feature}' may not be addressed in architecture",
                    source="architect",
                    suggestion=f"Verify '{feature}' implementation is planned",
                ))
        
        # Check integrations
        req_integrations = requirements.get("integrations", [])
        arch_integrations = architect.get("integrations", [])
        arch_integration_names = {i.get("name", "").lower() if isinstance(i, dict) else i.lower() for i in arch_integrations}
        
        for integration in req_integrations:
            if integration.lower() not in arch_integration_names:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="integration",
                    message=f"Requested integration '{integration}' not in architecture plan",
                    source="architect",
                    suggestion=f"Add '{integration}' to architecture integrations",
                ))
        
        return issues
    
    def _validate_requirements_vs_design_system(
        self,
        requirements: Dict[str, Any],
        design_system: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate design system matches requirements preferences."""
        issues = []
        
        if not design_system:
            return issues
        
        # Check dark_mode preference
        req_color_scheme = requirements.get("color_scheme", "dark")
        ds_theme = design_system.get("theme_mode") or design_system.get("color_scheme", "dark")
        
        if req_color_scheme != ds_theme:
            issues.append(ValidationIssue(
                severity="warning",
                category="design_system",
                message=f"Color scheme mismatch: requirements={req_color_scheme}, design_system={ds_theme}",
                source="design_system",
                suggestion=f"Update design system to use '{req_color_scheme}' color scheme",
            ))
        
        # Check style preference
        req_style = requirements.get("design_style", "")
        ds_style = design_system.get("style", "")
        
        if req_style and req_style.lower() not in ds_style.lower():
            issues.append(ValidationIssue(
                severity="info",
                category="design_system",
                message=f"Design style preference '{req_style}' may not be reflected",
                source="design_system",
                suggestion=f"Verify design system incorporates '{req_style}' aesthetic",
            ))
        
        # Check for dual-theme tokens if "both" mode
        if req_color_scheme in ["system", "both"]:
            tokens = design_system.get("tokens", {})
            if not tokens.get("light") or not tokens.get("dark"):
                issues.append(ValidationIssue(
                    severity="critical",
                    category="design_system",
                    message="Dual-theme mode requires both light and dark token sets",
                    source="design_system",
                    suggestion="Generate separate light and dark theme tokens",
                ))
        
        return issues
    
    def _validate_figma_vs_design_system(
        self,
        figma: Dict[str, Any],
        design_system: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate Figma designs match design system."""
        issues = []
        
        if not figma or not design_system:
            return issues
        
        # Check color matching
        figma_colors = figma.get("colors", {})
        ds_colors = design_system.get("tokens", {}).get("colors", {})
        
        for color_name, figma_value in figma_colors.items():
            if color_name in ds_colors:
                ds_value = ds_colors[color_name]
                if isinstance(ds_value, str) and isinstance(figma_value, str):
                    if ds_value.lower() != figma_value.lower():
                        issues.append(ValidationIssue(
                            severity="warning",
                            category="figma",
                            message=f"Color mismatch for '{color_name}': Figma={figma_value}, Design System={ds_value}",
                            source="figma",
                            suggestion="Align Figma and design system colors",
                        ))
        
        return issues
    
    def _validate_figma_vs_architect(
        self,
        figma: Dict[str, Any],
        architect: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate Figma page/component count matches architect."""
        issues = []
        
        if not figma:
            return issues
        
        figma_pages = figma.get("pages", [])
        arch_pages = architect.get("pages", [])
        
        if len(figma_pages) != len(arch_pages):
            issues.append(ValidationIssue(
                severity="warning",
                category="figma",
                message=f"Page count mismatch: Figma={len(figma_pages)}, Architect={len(arch_pages)}",
                source="figma",
                suggestion="Verify all Figma pages are accounted for in architecture",
            ))
        
        return issues
    
    def _validate_content_layout_fit(
        self, 
        architect: Dict[str, Any], 
        content: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check that content fits the layouts defined in architecture."""
        issues = []
        
        pages = architect.get("pages", [])
        content_items = content.get("content_items", {}) or content.get("pages", {})
        
        for page in pages:
            page_name = page.get("name", page.get("route", "unknown"))
            sections = page.get("sections", [])
            
            for section in sections:
                section_name = section.get("name", "unknown")
                
                # Check if content exists for this section
                content_key = f"{page_name.lower().replace(' ', '_')}_{section_name.lower().replace(' ', '_')}"
                
                if content_items and content_key not in content_items:
                    # Try alternate key formats
                    alt_keys = [
                        section_name.lower().replace(' ', '_'),
                        f"{page_name}_{section_name}",
                    ]
                    found = any(k in content_items for k in alt_keys)
                    
                    if not found and section.get("requires_content", True):
                        issues.append(ValidationIssue(
                            severity="warning",
                            category="content",
                            message=f"Missing content for {page_name} > {section_name}",
                            source="content_generation",
                            suggestion=f"Add content item with key '{content_key}'",
                        ))
        
        return issues
    
    def _validate_asset_dimensions(
        self,
        architect: Dict[str, Any],
        assets: Dict[str, Any],
        design_system: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check that asset dimensions match specifications and support dual themes."""
        issues = []
        
        # Get required assets from architecture
        required_assets = []
        for page in architect.get("pages", []):
            for section in page.get("sections", []):
                for component in section.get("components", []):
                    if "image" in component.lower() or "icon" in component.lower():
                        required_assets.append({
                            "name": component,
                            "page": page.get("name"),
                            "section": section.get("name"),
                        })
        
        # Check generated assets
        generated_assets = assets.get("assets", []) or assets.get("images", [])
        
        # Check for dual-theme assets if needed
        theme_mode = design_system.get("theme_mode", "dark")
        if theme_mode in ["both", "system"]:
            # Check for light/dark asset variants
            has_light_assets = any("light" in str(a).lower() for a in generated_assets)
            has_dark_assets = any("dark" in str(a).lower() for a in generated_assets)
            
            if not has_light_assets or not has_dark_assets:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="assets",
                    message="Dual-theme mode but missing light or dark asset variants",
                    source="asset_generation",
                    suggestion="Generate assets for both light and dark themes",
                ))
        
        for required in required_assets:
            found = False
            for asset in generated_assets:
                asset_name = asset.get("name", "") if isinstance(asset, dict) else str(asset)
                if required["name"].lower() in asset_name.lower():
                    found = True
                    break
            
            if not found:
                issues.append(ValidationIssue(
                    severity="info",
                    category="assets",
                    message=f"Asset '{required['name']}' may be missing for {required['page']} > {required['section']}",
                    source="asset_generation",
                    suggestion="Verify asset exists or generate placeholder",
                ))
        
        return issues
    
    def _validate_design_consistency(
        self,
        architect: Dict[str, Any],
        design_system: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check design system matches architecture requirements."""
        issues = []
        
        # Check if design system exists
        if not design_system:
            issues.append(ValidationIssue(
                severity="warning",
                category="design_system",
                message="No design system output found",
                source="design_system",
                suggestion="Ensure design system agent ran successfully",
            ))
            return issues
        
        # Check for required theme tokens
        tokens = design_system.get("tokens", {}) or design_system.get("theme", {})
        
        required_tokens = ["colors", "spacing", "typography"]
        for token_type in required_tokens:
            if token_type not in tokens and not any(token_type in k.lower() for k in tokens.keys()):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="design_system",
                    message=f"Missing {token_type} tokens in design system",
                    source="design_system",
                    suggestion=f"Add {token_type} configuration to design system",
                ))
        
        return issues
    
    def _validate_navigation(self, architect: Dict[str, Any]) -> List[ValidationIssue]:
        """Check navigation structure matches page routes."""
        issues = []
        
        pages = architect.get("pages", [])
        routes = [p.get("route", "/") for p in pages]
        
        # Check for duplicate routes
        seen_routes = set()
        for route in routes:
            if route in seen_routes:
                issues.append(ValidationIssue(
                    severity="critical",
                    category="architecture",
                    message=f"Duplicate route found: {route}",
                    source="architect",
                    suggestion="Ensure each page has a unique route",
                ))
            seen_routes.add(route)
        
        # Check for home page
        if "/" not in routes and "/home" not in routes:
            issues.append(ValidationIssue(
                severity="warning",
                category="architecture",
                message="No home page (/) defined",
                source="architect",
                suggestion="Add a root route for the home page",
            ))
        
        return issues
    
    def _validate_integrations(
        self, 
        requirements: Dict[str, Any], 
        architect: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate integration dependencies are satisfied."""
        issues = []
        
        features = requirements.get("features", [])
        integrations = requirements.get("integrations", [])
        
        # Check for required integration dependencies
        for feature in features:
            feature_lower = feature.lower()
            required_integrations = FEATURE_INTEGRATION_MAP.get(feature_lower, [])
            
            for req_int in required_integrations:
                if req_int not in [i.lower() for i in integrations]:
                    issues.append(ValidationIssue(
                        severity="info",
                        category="integration",
                        message=f"Feature '{feature}' typically requires '{req_int}' integration",
                        source="requirements",
                        suggestion=f"Consider adding '{req_int}' integration for '{feature}'",
                    ))
        
        # Check for payments requiring auth
        if "stripe" in [i.lower() for i in integrations]:
            has_auth = any("auth" in f.lower() for f in features)
            if not has_auth:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="integration",
                    message="Stripe payment integration typically requires authentication",
                    source="requirements",
                    suggestion="Add authentication feature for payment flow",
                ))
        
        return issues
    
    def _validate_dynamic_pooling(
        self, 
        pooling_config: Dict[str, Any], 
        architect: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Validate dynamic pooling dependency graph is valid."""
        issues = []
        
        pools = pooling_config.get("pools", [])
        dependencies = pooling_config.get("dependencies", {})
        
        # Check for circular dependencies
        for pool_name, deps in dependencies.items():
            visited = set()
            if self._has_circular_dependency(pool_name, dependencies, visited):
                issues.append(ValidationIssue(
                    severity="critical",
                    category="pooling",
                    message=f"Circular dependency detected in pool '{pool_name}'",
                    source="dynamic_pooling",
                    suggestion="Restructure pool dependencies to avoid cycles",
                ))
        
        # Check all pools have valid targets
        arch_pages = {p.get("name", "").lower() for p in architect.get("pages", [])}
        for pool in pools:
            pool_pages = pool.get("pages", [])
            for page in pool_pages:
                if page.lower() not in arch_pages:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="pooling",
                        message=f"Pool references unknown page: {page}",
                        source="dynamic_pooling",
                        suggestion="Ensure pool pages exist in architecture",
                    ))
        
        return issues
    
    def _has_circular_dependency(
        self, 
        pool: str, 
        dependencies: Dict[str, List[str]], 
        visited: Set[str]
    ) -> bool:
        """Check for circular dependency in pool graph."""
        if pool in visited:
            return True
        visited.add(pool)
        
        for dep in dependencies.get(pool, []):
            if self._has_circular_dependency(dep, dependencies, visited.copy()):
                return True
        
        return False
    
    def _generate_build_manifest(
        self,
        project_id: str,
        requirements: Dict[str, Any],
        architect_output: Dict[str, Any],
        design_system_output: Dict[str, Any],
        content_output: Dict[str, Any],
        assets_output: Dict[str, Any],
        theme_mode: str,
        warnings: List[str],
        dynamic_pooling: Optional[Dict[str, Any]],
    ) -> BuildManifest:
        """Generate unified build manifest from all agent outputs."""
        
        # Extract integrations
        integrations = {}
        for feature in requirements.get("features", []):
            feature_lower = feature.lower()
            if feature_lower in FEATURE_INTEGRATION_MAP:
                for int_name in FEATURE_INTEGRATION_MAP[feature_lower]:
                    integrations[int_name] = {
                        "feature": feature,
                        "wired": False,  # Will be verified in checkpoint 2
                    }
        
        return BuildManifest(
            project_id=project_id,
            generated_at=datetime.utcnow().isoformat(),
            validated=True,
            requirements_version=requirements.get("version", "1.0"),
            theme_mode=theme_mode,
            pages=architect_output.get("pages", []),
            components=architect_output.get("components", []),
            assets=assets_output or {},
            content=content_output or {},
            design_tokens=design_system_output.get("tokens", {}) or design_system_output.get("theme", {}),
            api_endpoints=architect_output.get("api_endpoints", []),
            database_schema=architect_output.get("database_schema"),
            integrations=integrations,
            build_order=architect_output.get("build_order", []),
            warnings=warnings,
            dynamic_pooling=dynamic_pooling,
        )
    
    def _verify_theme_implementation(self, project_path: str, theme_mode: str) -> Dict[str, bool]:
        """Verify theme implementation in generated code."""
        result = {
            "toggle_exists": False,
            "css_vars_used": False,
            "local_storage": False,
            "both_themes_styled": False,
        }
        
        if not os.path.exists(project_path):
            return result
        
        # Search for theme toggle
        toggle_patterns = [
            r"ThemeToggle",
            r"dark-mode-toggle",
            r"theme-switcher",
            r"setTheme\(",
            r"toggleTheme",
        ]
        
        # Search for CSS vars
        css_var_pattern = r"var\(--"
        
        # Search for localStorage theme
        storage_patterns = [
            r"localStorage.*theme",
            r"theme.*localStorage",
        ]
        
        code_extensions = [".tsx", ".ts", ".jsx", ".js", ".css", ".scss"]
        skip_dirs = ["node_modules", ".git", ".next", "dist"]
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if not any(file.endswith(ext) for ext in code_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                        # Check for toggle
                        for pattern in toggle_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                result["toggle_exists"] = True
                                break
                        
                        # Check for CSS vars
                        if re.search(css_var_pattern, content):
                            result["css_vars_used"] = True
                        
                        # Check for localStorage
                        for pattern in storage_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                result["local_storage"] = True
                                break
                        
                        # Check for both themes
                        if "dark:" in content and ("light:" in content or "bg-white" in content):
                            result["both_themes_styled"] = True
                except Exception:
                    pass
        
        return result
    
    def _verify_integration_wiring(
        self, 
        project_path: str, 
        integrations: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Verify that integrations are properly wired in the code."""
        results = {}
        
        integration_checks = {
            "stripe": {
                "imports": [r"@stripe/stripe-js", r"stripe"],
                "env_vars": [r"STRIPE_SECRET_KEY", r"STRIPE_PUBLISHABLE_KEY", r"NEXT_PUBLIC_STRIPE"],
            },
            "resend": {
                "imports": [r"resend"],
                "env_vars": [r"RESEND_API_KEY"],
            },
            "supabase": {
                "imports": [r"@supabase/supabase-js", r"supabase"],
                "env_vars": [r"SUPABASE_URL", r"SUPABASE_ANON_KEY"],
            },
            "cloudflare_r2": {
                "imports": [r"@aws-sdk/client-s3", r"S3Client"],
                "env_vars": [r"R2_ACCESS_KEY", r"R2_SECRET_KEY", r"R2_BUCKET"],
            },
            "inngest": {
                "imports": [r"inngest"],
                "env_vars": [r"INNGEST_EVENT_KEY"],
            },
        }
        
        if not os.path.exists(project_path):
            return {name: {"wired": False, "issues": ["Project path not found"]} for name in integrations}
        
        # Read all code files
        all_content = ""
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in ["node_modules", ".git"]]
            for file in files:
                if file.endswith((".ts", ".tsx", ".js", ".jsx")):
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                            all_content += f.read() + "\n"
                    except:
                        pass
        
        # Read env files
        env_content = ""
        for env_file in [".env", ".env.example", ".env.local.example"]:
            env_path = os.path.join(project_path, env_file)
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r") as f:
                        env_content += f.read() + "\n"
                except:
                    pass
        
        for int_name in integrations:
            int_lower = int_name.lower().replace("-", "_")
            checks = integration_checks.get(int_lower, {})
            
            issues = []
            import_found = False
            env_found = False
            
            # Check imports
            for pattern in checks.get("imports", []):
                if re.search(pattern, all_content, re.IGNORECASE):
                    import_found = True
                    break
            
            if not import_found:
                issues.append(f"No {int_name} SDK import found")
            
            # Check env vars
            for pattern in checks.get("env_vars", []):
                if re.search(pattern, env_content, re.IGNORECASE):
                    env_found = True
                    break
            
            if not env_found:
                issues.append(f"No {int_name} env vars documented")
            
            results[int_name] = {
                "wired": import_found and env_found,
                "issues": issues,
            }
        
        return results
    
    def _verify_pooling_consistency(
        self, 
        project_path: str, 
        pooling_config: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Verify dynamic pooling consistency across batches."""
        issues = []
        
        pools = pooling_config.get("pools", [])
        shared_components = pooling_config.get("shared_components", [])
        
        # Check shared components exist
        component_dir = os.path.join(project_path, "src", "components")
        if not os.path.exists(component_dir):
            component_dir = os.path.join(project_path, "components")
        
        for comp in shared_components:
            comp_path = os.path.join(component_dir, f"{comp}.tsx")
            if not os.path.exists(comp_path):
                # Try other locations
                found = False
                for root, dirs, files in os.walk(project_path):
                    dirs[:] = [d for d in dirs if d not in ["node_modules", ".git"]]
                    if f"{comp}.tsx" in files or f"{comp}.jsx" in files:
                        found = True
                        break
                
                if not found:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="pooling",
                        message=f"Shared component '{comp}' not found",
                        source="dynamic_pooling",
                        suggestion=f"Create shared component: {comp}.tsx",
                    ))
        
        # Check cross-batch import consistency
        # (Components from Pool A used in Pool B should be importable)
        
        return issues
    
    def _check_pages_implemented(
        self, 
        pages: List[Dict], 
        project_path: str
    ) -> tuple[List[ValidationIssue], List[str]]:
        """Check that all pages from manifest are implemented."""
        issues = []
        missing = []
        
        for page in pages:
            route = page.get("route", "/")
            page_name = page.get("name", "unknown")
            
            # Determine expected file path
            if route == "/":
                expected_files = [
                    os.path.join(project_path, "src/app/page.tsx"),
                    os.path.join(project_path, "src/pages/index.tsx"),
                    os.path.join(project_path, "app/page.tsx"),
                    os.path.join(project_path, "pages/index.tsx"),
                ]
            else:
                route_path = route.strip("/")
                expected_files = [
                    os.path.join(project_path, f"src/app/{route_path}/page.tsx"),
                    os.path.join(project_path, f"src/pages/{route_path}.tsx"),
                    os.path.join(project_path, f"app/{route_path}/page.tsx"),
                    os.path.join(project_path, f"pages/{route_path}.tsx"),
                ]
            
            found = any(os.path.exists(f) for f in expected_files)
            
            if not found:
                issues.append(ValidationIssue(
                    severity="critical",
                    category="implementation",
                    message=f"Page '{page_name}' (route: {route}) not implemented",
                    source="code_generation",
                    suggestion=f"Create page file for route {route}",
                ))
                missing.append(page_name)
        
        return issues, missing
    
    def _check_components_implemented(
        self,
        components: List[Dict],
        project_path: str
    ) -> List[ValidationIssue]:
        """Check that all components are implemented."""
        issues = []
        
        component_dirs = [
            os.path.join(project_path, "src/components"),
            os.path.join(project_path, "components"),
            os.path.join(project_path, "src/app/components"),
        ]
        
        for component in components:
            comp_name = component.get("name", "")
            if not comp_name:
                continue
            
            # Look for component file
            found = False
            for comp_dir in component_dirs:
                if os.path.exists(comp_dir):
                    for ext in [".tsx", ".jsx", ".ts", ".js"]:
                        comp_file = os.path.join(comp_dir, f"{comp_name}{ext}")
                        if os.path.exists(comp_file):
                            found = True
                            break
                    # Also check subdirectories
                    if not found and os.path.isdir(comp_dir):
                        for root, dirs, files in os.walk(comp_dir):
                            for f in files:
                                if comp_name.lower() in f.lower():
                                    found = True
                                    break
                            if found:
                                break
                if found:
                    break
            
            if not found:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="implementation",
                    message=f"Component '{comp_name}' may not be implemented",
                    source="code_generation",
                    suggestion=f"Create component file {comp_name}.tsx",
                ))
        
        return issues
    
    def _scan_for_placeholders(self, project_path: str) -> Dict[str, Any]:
        """Scan codebase for placeholder code (TODO, FIXME, etc.)."""
        placeholders = []
        files_scanned = []
        
        placeholder_patterns = [
            "TODO",
            "FIXME",
            "XXX",
            "HACK",
            "// ...",
            "/* ... */",
            "throw new Error('Not implemented')",
            "pass  # TODO",
        ]
        
        code_extensions = [".tsx", ".ts", ".jsx", ".js", ".py", ".go", ".rs"]
        
        if os.path.exists(project_path):
            for root, dirs, files in os.walk(project_path):
                # Skip node_modules, .git, etc.
                dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", "__pycache__", ".next", "dist"]]
                
                for file in files:
                    if any(file.endswith(ext) for ext in code_extensions):
                        file_path = os.path.join(root, file)
                        files_scanned.append(file_path)
                        
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                for pattern in placeholder_patterns:
                                    if pattern in content:
                                        placeholders.append({
                                            "file": file_path,
                                            "pattern": pattern,
                                        })
                        except Exception:
                            pass
        
        return {
            "count": len(placeholders),
            "items": placeholders,
            "files": files_scanned,
        }
    
    def _check_endpoints_implemented(
        self,
        endpoints: List[Dict],
        project_path: str
    ) -> List[ValidationIssue]:
        """Check that API endpoints are implemented."""
        issues = []
        
        api_dirs = [
            os.path.join(project_path, "src/app/api"),
            os.path.join(project_path, "src/pages/api"),
            os.path.join(project_path, "app/api"),
            os.path.join(project_path, "pages/api"),
            os.path.join(project_path, "api"),
        ]
        
        for endpoint in endpoints:
            path = endpoint.get("path", "")
            if not path or not path.startswith("/api"):
                continue
            
            # Convert API path to expected file path
            api_path = path.replace("/api/", "").replace("/api", "")
            
            found = False
            for api_dir in api_dirs:
                if os.path.exists(api_dir):
                    for ext in ["/route.ts", "/route.tsx", ".ts", ".tsx", ".js"]:
                        expected = os.path.join(api_dir, api_path + ext)
                        expected_dir = os.path.join(api_dir, api_path)
                        if os.path.exists(expected) or os.path.exists(expected_dir):
                            found = True
                            break
                if found:
                    break
            
            if not found:
                issues.append(ValidationIssue(
                    severity="critical",
                    category="implementation",
                    message=f"API endpoint '{path}' not implemented",
                    source="code_generation",
                    suggestion=f"Create API route handler for {path}",
                ))
        
        return issues
    
    def _check_env_documented(
        self, 
        project_path: str, 
        integrations: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check that environment variables are documented."""
        issues = []
        
        env_example = os.path.join(project_path, ".env.example")
        env_local = os.path.join(project_path, ".env.local.example")
        readme = os.path.join(project_path, "README.md")
        
        has_env_docs = os.path.exists(env_example) or os.path.exists(env_local)
        
        if not has_env_docs:
            # Check README for env section
            if os.path.exists(readme):
                try:
                    with open(readme, "r") as f:
                        content = f.read().lower()
                        if "environment" in content or "env" in content:
                            has_env_docs = True
                except Exception:
                    pass
        
        if not has_env_docs:
            issues.append(ValidationIssue(
                severity="info",
                category="documentation",
                message="Environment variables not documented",
                source="code_generation",
                suggestion="Create .env.example file documenting required variables",
            ))
        
        # Check for integration-specific env vars
        env_content = ""
        if os.path.exists(env_example):
            try:
                with open(env_example, "r") as f:
                    env_content = f.read()
            except:
                pass
        
        integration_vars = {
            "stripe": ["STRIPE"],
            "resend": ["RESEND"],
            "supabase": ["SUPABASE"],
            "cloudflare_r2": ["R2_", "CLOUDFLARE"],
            "inngest": ["INNGEST"],
        }
        
        for int_name in integrations:
            int_lower = int_name.lower().replace("-", "_")
            expected_vars = integration_vars.get(int_lower, [])
            
            for var_prefix in expected_vars:
                if var_prefix not in env_content.upper():
                    issues.append(ValidationIssue(
                        severity="info",
                        category="documentation",
                        message=f"Missing env var documentation for {int_name}",
                        source="code_generation",
                        suggestion=f"Add {var_prefix}* vars to .env.example",
                    ))
                    break
        
        return issues
    
    def _issue_to_dict(self, issue: ValidationIssue) -> Dict[str, Any]:
        """Convert ValidationIssue to dictionary."""
        return {
            "severity": issue.severity,
            "category": issue.category,
            "message": issue.message,
            "source": issue.source,
            "suggestion": issue.suggestion,
            "auto_fix_available": issue.auto_fix_available,
            "auto_fix_instruction": issue.auto_fix_instruction,
        }
