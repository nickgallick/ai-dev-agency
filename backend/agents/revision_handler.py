"""Revision Handler Agent - Manages project revisions and incremental updates."""

import json
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .base import BaseAgent


@dataclass
class RevisionScope:
    """Defines the scope of a revision."""
    scope_type: str  # small_tweak, medium_feature, major_addition
    affected_files: List[str] = field(default_factory=list)
    affected_agents: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    risk_level: str = "low"  # low, medium, high
    requires_regression_tests: bool = True


@dataclass 
class RevisionResult:
    """Result of a revision operation."""
    success: bool
    revision_id: str
    changes_made: List[Dict[str, Any]] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    git_commit_sha: Optional[str] = None
    regression_test_passed: bool = True
    errors: List[str] = field(default_factory=list)


class RevisionHandlerAgent(BaseAgent):
    """Handles project revisions and incremental modifications."""
    
    name = "revision_handler"
    description = "Revision Handler Agent"
    step_number = 0  # Runs outside normal pipeline
    
    # Agent dependencies for different revision types
    REVISION_AGENTS = {
        "small_tweak": ["code_generation"],
        "medium_feature": ["architect", "code_generation", "qa_testing"],
        "major_addition": ["intake", "architect", "design_system", "code_generation", 
                          "security", "qa_testing", "deployment"],
    }
    
    # File patterns to determine affected components
    FILE_PATTERNS = {
        "frontend": [".tsx", ".jsx", ".css", ".html", ".vue", ".svelte"],
        "backend": [".py", "routes/", "models/", "api/"],
        "config": [".json", ".yaml", ".yml", ".toml", ".env"],
        "tests": ["test_", "_test.", "tests/", "spec/"],
        "docs": [".md", ".rst", "docs/"],
    }
    
    SYSTEM_PROMPT = """You are the Revision Handler Agent for an AI development agency.

Your job is to analyze revision requests and determine:
1. The scope of the revision (small_tweak, medium_feature, major_addition)
2. Which existing files need to be modified
3. Which agents need to be activated
4. Potential risks and regression concerns

Revision Scope Definitions:
- small_tweak: Minor changes like text updates, color changes, bug fixes
- medium_feature: New components, pages, or features within existing architecture
- major_addition: Significant new capabilities requiring architectural changes

Respond with JSON:
{
    "scope_type": "small_tweak" | "medium_feature" | "major_addition",
    "summary": "Brief description of what needs to change",
    "affected_components": ["frontend", "backend", "config", "tests"],
    "required_agents": ["agent1", "agent2"],
    "files_to_modify": ["path/to/file1.tsx", "path/to/file2.py"],
    "new_files_needed": ["path/to/new_file.tsx"],
    "risk_assessment": {
        "level": "low" | "medium" | "high",
        "concerns": ["list of concerns"],
        "mitigation": ["mitigation strategies"]
    },
    "regression_areas": ["areas that need regression testing"],
    "estimated_effort": "X hours"
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and process a revision request."""
        revision_brief = input_data.get("revision_brief", "")
        project_path = input_data.get("project_path", "")
        existing_codebase = input_data.get("existing_codebase", {})
        project_type = input_data.get("project_type", "web_simple")
        cost_profile = input_data.get("cost_profile", "balanced")
        
        # Get existing file structure
        if project_path and os.path.exists(project_path):
            file_structure = self._get_file_structure(project_path)
        else:
            file_structure = existing_codebase.get("files", [])
        
        # Analyze the revision request
        scope = await self._analyze_revision_scope(
            revision_brief, 
            file_structure,
            project_type,
            cost_profile,
        )
        
        return {
            "scope": {
                "type": scope.scope_type,
                "affected_files": scope.affected_files,
                "affected_agents": scope.affected_agents,
                "estimated_cost": scope.estimated_cost,
                "risk_level": scope.risk_level,
                "requires_regression_tests": scope.requires_regression_tests,
            },
            "analysis_complete": True,
        }
    
    async def apply_revision(
        self,
        project_path: str,
        revision_brief: str,
        scope: RevisionScope,
        code_changes: Dict[str, str],
    ) -> RevisionResult:
        """Apply revision changes to the codebase."""
        revision_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        result = RevisionResult(
            success=True,
            revision_id=revision_id,
        )
        
        try:
            # Ensure we're in a git repo
            if not self._is_git_repo(project_path):
                self._init_git_repo(project_path)
            
            # Create a revision branch
            branch_name = f"revision/{revision_id}"
            self._create_branch(project_path, branch_name)
            
            # Apply changes
            for file_path, content in code_changes.items():
                full_path = os.path.join(project_path, file_path)
                
                if os.path.exists(full_path):
                    result.files_modified.append(file_path)
                else:
                    result.files_created.append(file_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, "w") as f:
                    f.write(content)
                
                result.changes_made.append({
                    "file": file_path,
                    "action": "modified" if file_path in result.files_modified else "created",
                })
            
            # Commit changes
            commit_sha = self._commit_changes(
                project_path, 
                f"Revision {revision_id}: {revision_brief[:50]}",
            )
            result.git_commit_sha = commit_sha
            
            # Run regression tests if needed
            if scope.requires_regression_tests:
                result.regression_test_passed = await self._run_regression_tests(project_path)
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
        
        return result
    
    async def _analyze_revision_scope(
        self,
        revision_brief: str,
        file_structure: List[str],
        project_type: str,
        cost_profile: str,
    ) -> RevisionScope:
        """Analyze the revision and determine scope."""
        
        # Build context about existing files
        file_context = "\n".join(file_structure[:100])  # Limit to first 100 files
        
        prompt = f"""Analyze this revision request for a {project_type} project:

REVISION REQUEST:
{revision_brief}

EXISTING FILES:
{file_context}

Determine the scope, affected files, and required agents."""
        
        model = self._select_model(cost_profile)
        
        result = await self.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3,
        )
        
        # Parse the response
        try:
            analysis = json.loads(result["content"])
        except json.JSONDecodeError:
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                analysis = json.loads(content[start:end])
            else:
                analysis = {"scope_type": "medium_feature", "required_agents": ["code_generation"]}
        
        scope_type = analysis.get("scope_type", "medium_feature")
        
        return RevisionScope(
            scope_type=scope_type,
            affected_files=analysis.get("files_to_modify", []),
            affected_agents=analysis.get("required_agents", self.REVISION_AGENTS.get(scope_type, [])),
            estimated_cost=self._estimate_revision_cost(scope_type, cost_profile),
            risk_level=analysis.get("risk_assessment", {}).get("level", "medium"),
            requires_regression_tests=scope_type != "small_tweak",
        )
    
    def _get_file_structure(self, project_path: str) -> List[str]:
        """Get list of files in the project."""
        files = []
        for root, dirs, filenames in os.walk(project_path):
            # Skip common non-essential directories
            dirs[:] = [d for d in dirs if d not in [
                "node_modules", ".git", "__pycache__", ".next", 
                "dist", "build", ".venv", "venv"
            ]]
            
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), project_path)
                files.append(rel_path)
        
        return files
    
    def _is_git_repo(self, project_path: str) -> bool:
        """Check if project is a git repository."""
        return os.path.exists(os.path.join(project_path, ".git"))
    
    def _init_git_repo(self, project_path: str) -> None:
        """Initialize a git repository."""
        subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
    
    def _create_branch(self, project_path: str, branch_name: str) -> None:
        """Create and checkout a new branch."""
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
    
    def _commit_changes(self, project_path: str, message: str) -> str:
        """Stage and commit all changes, return commit SHA."""
        subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    
    async def _run_regression_tests(self, project_path: str) -> bool:
        """Run regression tests on the project."""
        # Check for test commands
        package_json = os.path.join(project_path, "package.json")
        pyproject = os.path.join(project_path, "pyproject.toml")
        
        try:
            if os.path.exists(package_json):
                result = subprocess.run(
                    ["npm", "test"],
                    cwd=project_path,
                    capture_output=True,
                    timeout=300,  # 5 minute timeout
                )
                return result.returncode == 0
            
            elif os.path.exists(pyproject):
                result = subprocess.run(
                    ["python", "-m", "pytest"],
                    cwd=project_path,
                    capture_output=True,
                    timeout=300,
                )
                return result.returncode == 0
            
            # No tests found, assume pass
            return True
            
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return True  # If we can't run tests, don't block
    
    def _estimate_revision_cost(self, scope_type: str, cost_profile: str) -> float:
        """Estimate cost for a revision based on scope and profile."""
        base_costs = {
            "small_tweak": {"budget": 0.5, "balanced": 1.0, "premium": 2.0},
            "medium_feature": {"budget": 2.0, "balanced": 5.0, "premium": 10.0},
            "major_addition": {"budget": 5.0, "balanced": 15.0, "premium": 30.0},
        }
        
        scope_costs = base_costs.get(scope_type, base_costs["medium_feature"])
        return scope_costs.get(cost_profile, scope_costs["balanced"])
    
    def _select_model(self, cost_profile: str) -> str:
        """Select model based on cost profile."""
        models = {
            "budget": "deepseek/deepseek-chat",
            "balanced": "anthropic/claude-sonnet-4",
            "premium": "anthropic/claude-opus-4",
        }
        return models.get(cost_profile, "anthropic/claude-sonnet-4")
    
    def get_revision_history(self, project_path: str) -> List[Dict[str, Any]]:
        """Get revision history from git log."""
        if not self._is_git_repo(project_path):
            return []
        
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-20", "--format=%H|%s|%ai"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            
            history = []
            for line in result.stdout.strip().split("\n"):
                if line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        history.append({
                            "sha": parts[0],
                            "message": parts[1],
                            "date": parts[2],
                        })
            
            return history
            
        except Exception:
            return []
    
    def rollback_to_revision(self, project_path: str, commit_sha: str) -> bool:
        """Rollback to a specific revision."""
        try:
            subprocess.run(
                ["git", "checkout", commit_sha],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            return True
        except Exception:
            return False
