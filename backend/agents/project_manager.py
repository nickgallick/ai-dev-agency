"""Project Manager Agent - Validates coherence and completeness.

Implements two checkpoint methods:
- checkpoint_1_coherence: After Architect + Design System + Content + Assets, before Code Gen
- checkpoint_2_completeness: After Code Gen, before Quality Gate

Only activates for complex project types:
- web_complex, python_saas, mobile_cross_platform, desktop_app

Uses Claude Sonnet 4 for validation.
"""

import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .base import BaseAgent, AgentResult


@dataclass
class ValidationIssue:
    """Represents a validation issue found during checkpoint."""
    severity: str  # critical, warning, info
    category: str  # content, assets, architecture, design_system
    message: str
    source: str  # Which agent output caused the issue
    suggestion: str


@dataclass 
class BuildManifest:
    """Single source of truth for code generation."""
    project_id: str
    generated_at: str
    validated: bool
    pages: List[Dict[str, Any]]
    components: List[Dict[str, Any]]
    assets: Dict[str, Any]
    content: Dict[str, Any]
    design_tokens: Dict[str, Any]
    api_endpoints: List[Dict[str, Any]]
    database_schema: Optional[Dict[str, Any]]
    build_order: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "generated_at": self.generated_at,
            "validated": self.validated,
            "pages": self.pages,
            "components": self.components,
            "assets": self.assets,
            "content": self.content,
            "design_tokens": self.design_tokens,
            "api_endpoints": self.api_endpoints,
            "database_schema": self.database_schema,
            "build_order": self.build_order,
            "warnings": self.warnings,
        }


# Project types that require PM checkpoints
COMPLEX_PROJECT_TYPES = [
    "web_complex",
    "python_saas", 
    "mobile_cross_platform",
    "desktop_app",
]


class ProjectManagerAgent(BaseAgent):
    """Project Manager Agent that validates cross-agent coherence and completeness."""
    
    name = "project_manager"
    description = "Project Manager - Validates coherence and completeness"
    model = "anthropic/claude-sonnet-4"
    
    COHERENCE_SYSTEM_PROMPT = """You are the Project Manager Agent validating coherence across all planning outputs.

You must check for:
1. Content fits layouts - text lengths match allocated space in designs
2. Asset dimensions match specs - images, icons are the right sizes
3. No contradictions between architect plan and design system
4. All content keys are used in page layouts
5. Navigation structure matches page routes
6. API endpoints match data requirements

Respond ONLY with valid JSON:
{
    "coherent": true/false,
    "issues": [
        {
            "severity": "critical/warning/info",
            "category": "content/assets/architecture/design_system",
            "message": "Description of issue",
            "source": "agent_name",
            "suggestion": "How to fix"
        }
    ],
    "build_manifest": {
        "pages": [...validated and merged page configs...],
        "components": [...validated component list...],
        "assets": {...validated asset mappings...},
        "content": {...validated content with keys...},
        "design_tokens": {...validated design system tokens...},
        "api_endpoints": [...validated endpoints...],
        "database_schema": {...if applicable...},
        "build_order": ["Step 1...", "Step 2..."]
    },
    "warnings": ["Non-critical items to watch"]
}"""

    COMPLETENESS_SYSTEM_PROMPT = """You are the Project Manager Agent validating code generation completeness.

You must check:
1. All pages from the architecture are implemented
2. All components are created and properly connected
3. All API endpoints are implemented and match specs
4. Frontend routes match backend endpoints
5. No placeholder code (TODO, FIXME, etc.)
6. All imports are valid
7. Database migrations exist if schema was defined
8. Environment variables are documented

Respond ONLY with valid JSON:
{
    "complete": true/false,
    "implementation_score": 0-100,
    "issues": [
        {
            "severity": "critical/warning/info",
            "type": "missing_page/missing_component/missing_endpoint/placeholder_code/missing_file",
            "message": "Description",
            "file": "path/to/file.tsx",
            "suggestion": "How to fix"
        }
    ],
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
    
    async def checkpoint_1_coherence(self, context: Dict[str, Any]) -> AgentResult:
        """
        Checkpoint 1: Validates outputs from Architect, Design System, Content, Assets.
        Produces build_manifest.json as single source of truth for code generation.
        """
        self.logger.info("Running PM Checkpoint 1: Coherence Validation")
        
        project_id = context.get("project_id", "unknown")
        project_type = context.get("project_type", "web_simple")
        project_path = context.get("project_path", "/tmp/project")
        
        # Check if this project needs PM checkpoints
        if not self.should_activate(project_type):
            self.logger.info(f"Skipping PM checkpoint for simple project type: {project_type}")
            return AgentResult(
                success=True,
                agent_name=self.name,
                data={"skipped": True, "reason": "Project type doesn't require PM checkpoint"},
            )
        
        # Gather outputs from previous agents
        architect_output = context.get("architect_result", {})
        design_system_output = context.get("design_system_result", {})
        content_output = context.get("content_generation_result", {})
        assets_output = context.get("asset_generation_result", {})
        
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
        
        # 1. Validate content fits layouts
        content_issues = self._validate_content_layout_fit(
            architect_output, content_output
        )
        issues.extend(content_issues)
        
        # 2. Validate asset dimensions
        asset_issues = self._validate_asset_dimensions(
            architect_output, assets_output
        )
        issues.extend(asset_issues)
        
        # 3. Validate design system consistency
        design_issues = self._validate_design_consistency(
            architect_output, design_system_output
        )
        issues.extend(design_issues)
        
        # 4. Validate navigation structure
        nav_issues = self._validate_navigation(architect_output)
        issues.extend(nav_issues)
        
        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        
        if critical_issues:
            self.logger.error(f"Found {len(critical_issues)} critical coherence issues")
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=[f"{i.category}: {i.message}" for i in critical_issues],
                data={
                    "issues": [self._issue_to_dict(i) for i in issues],
                    "critical_count": len(critical_issues),
                },
            )
        
        # Generate build manifest
        build_manifest = self._generate_build_manifest(
            project_id=project_id,
            architect_output=architect_output,
            design_system_output=design_system_output,
            content_output=content_output,
            assets_output=assets_output,
            warnings=[i.message for i in issues if i.severity == "warning"],
        )
        
        # Write build manifest to project path
        manifest_path = os.path.join(project_path, "build_manifest.json")
        try:
            os.makedirs(project_path, exist_ok=True)
            with open(manifest_path, "w") as f:
                json.dump(build_manifest.to_dict(), f, indent=2)
            self.logger.info(f"Build manifest written to {manifest_path}")
        except Exception as e:
            self.logger.warning(f"Failed to write build manifest: {e}")
        
        return AgentResult(
            success=True,
            agent_name=self.name,
            data={
                "coherent": True,
                "issues": [self._issue_to_dict(i) for i in issues],
                "build_manifest": build_manifest.to_dict(),
                "manifest_path": manifest_path,
            },
            warnings=[i.message for i in issues if i.severity == "warning"],
        )
    
    async def checkpoint_2_completeness(self, context: Dict[str, Any]) -> AgentResult:
        """
        Checkpoint 2: Verifies code generation is complete.
        Runs after Code Gen, before Quality Gate.
        """
        self.logger.info("Running PM Checkpoint 2: Completeness Validation")
        
        project_id = context.get("project_id", "unknown")
        project_type = context.get("project_type", "web_simple")
        project_path = context.get("project_path", "/tmp/project")
        
        # Check if this project needs PM checkpoints
        if not self.should_activate(project_type):
            self.logger.info(f"Skipping PM checkpoint for simple project type: {project_type}")
            return AgentResult(
                success=True,
                agent_name=self.name,
                data={"skipped": True, "reason": "Project type doesn't require PM checkpoint"},
            )
        
        # Load build manifest
        manifest_path = os.path.join(project_path, "build_manifest.json")
        build_manifest = None
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    build_manifest = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load build manifest: {e}")
        
        # Get code generation output
        code_gen_output = context.get("code_generation_result", {})
        
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
        
        # 3. Check for placeholder code
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
        
        # 4. Check API endpoints match
        if build_manifest:
            endpoint_issues = self._check_endpoints_implemented(
                build_manifest.get("api_endpoints", []), project_path
            )
            issues.extend(endpoint_issues)
        
        # 5. Check environment variables documented
        env_issues = self._check_env_documented(project_path)
        issues.extend(env_issues)
        
        # Calculate implementation score
        critical_count = len([i for i in issues if i.severity == "critical"])
        warning_count = len([i for i in issues if i.severity == "warning"])
        implementation_score = max(0, 100 - (critical_count * 20) - (warning_count * 5) - (placeholder_count * 2))
        
        # Determine success
        success = critical_count == 0 and implementation_score >= 70
        
        # Write completeness report
        report_path = os.path.join(project_path, "completeness_report.json")
        report = {
            "complete": success,
            "implementation_score": implementation_score,
            "issues": [self._issue_to_dict(i) for i in issues],
            "missing_features": missing_features,
            "placeholder_count": placeholder_count,
            "files_reviewed": files_reviewed,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        try:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to write completeness report: {e}")
        
        return AgentResult(
            success=success,
            agent_name=self.name,
            data=report,
            errors=[f"{i.category}: {i.message}" for i in issues if i.severity == "critical"],
            warnings=[i.message for i in issues if i.severity == "warning"],
        )
    
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
        assets: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Check that asset dimensions match specifications."""
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
    
    def _generate_build_manifest(
        self,
        project_id: str,
        architect_output: Dict[str, Any],
        design_system_output: Dict[str, Any],
        content_output: Dict[str, Any],
        assets_output: Dict[str, Any],
        warnings: List[str],
    ) -> BuildManifest:
        """Generate unified build manifest from all agent outputs."""
        return BuildManifest(
            project_id=project_id,
            generated_at=datetime.utcnow().isoformat(),
            validated=True,
            pages=architect_output.get("pages", []),
            components=architect_output.get("components", []),
            assets=assets_output or {},
            content=content_output or {},
            design_tokens=design_system_output.get("tokens", {}) or design_system_output.get("theme", {}),
            api_endpoints=architect_output.get("api_endpoints", []),
            database_schema=architect_output.get("database_schema"),
            build_order=architect_output.get("build_order", []),
            warnings=warnings,
        )
    
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
    
    def _check_env_documented(self, project_path: str) -> List[ValidationIssue]:
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
        
        return issues
    
    def _issue_to_dict(self, issue: ValidationIssue) -> Dict[str, Any]:
        """Convert ValidationIssue to dictionary."""
        return {
            "severity": issue.severity,
            "category": issue.category,
            "message": issue.message,
            "source": issue.source,
            "suggestion": issue.suggestion,
        }
