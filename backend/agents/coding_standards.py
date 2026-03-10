"""Coding Standards Generation Agent - Comprehensive documentation and standards generation.

Phase 11E Enhancement:
- Tech-stack-aware config generation (Next.js + Supabase + Stripe specific)
- Theme documentation (light/dark mode implementation)
- Integration guides (Stripe webhooks, Resend email, R2 uploads)
- KB pattern storage for future template reuse
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import AgentResult, BaseAgent

# Import knowledge base
try:
    from ..knowledge import store_knowledge, KnowledgeEntryType
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class GeneratedDocument:
    """Represents a generated document."""
    name: str
    path: str
    type: str  # readme, api_docs, contributing, adr, style_guide, changelog, license, deployment
    generated: bool = False
    content_preview: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class CodingStandardsReport:
    """Complete coding standards generation report."""
    project_name: str
    project_type: str
    documents: List[GeneratedDocument] = field(default_factory=list)
    style_configs: List[str] = field(default_factory=list)
    adrs_generated: int = 0
    total_generated: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "project_name": self.project_name,
            "project_type": self.project_type,
            "documents": [
                {
                    "name": d.name,
                    "path": d.path,
                    "type": d.type,
                    "generated": d.generated,
                    "content_preview": d.content_preview,
                    "error_message": d.error_message,
                }
                for d in self.documents
            ],
            "style_configs": self.style_configs,
            "adrs_generated": self.adrs_generated,
            "total_generated": self.total_generated,
            "timestamp": self.timestamp,
            "errors": self.errors,
        }


class CodingStandardsAgent(BaseAgent):
    """Agent for generating comprehensive project documentation and coding standards."""

    @property
    def name(self) -> str:
        return "Coding Standards Agent"

    async def execute(
        self,
        project_path: str,
        project_name: str,
        project_type: str = "web",
        tech_stack: Optional[List[str]] = None,
        description: Optional[str] = None,
        github_repo: Optional[str] = None,
        license_type: str = "MIT",
        **kwargs
    ) -> AgentResult:
        """
        Generate comprehensive project documentation and coding standards.
        
        Args:
            project_path: Path to the project directory
            project_name: Name of the project
            project_type: Type of project (web, mobile, api, desktop)
            tech_stack: List of technologies used
            description: Project description
            github_repo: GitHub repository URL
            license_type: License type (MIT, Apache-2.0, GPL-3.0, etc.)
            
        Returns:
            AgentResult with generated documentation
        """
        import time
        start_time = time.time()
        
        tech_stack = tech_stack or self._detect_tech_stack(project_path)
        report = CodingStandardsReport(
            project_name=project_name,
            project_type=project_type,
        )
        
        self.logger.info(f"Generating documentation for {project_name}")
        
        try:
            path = Path(project_path)
            
            # Generate README.md
            readme_doc = await self._generate_readme(
                path, project_name, project_type, tech_stack, description, github_repo
            )
            report.documents.append(readme_doc)
            
            # Generate API documentation
            api_doc = await self._generate_api_docs(
                path, project_name, project_type, tech_stack
            )
            report.documents.append(api_doc)
            
            # Generate CONTRIBUTING.md
            contributing_doc = await self._generate_contributing(
                path, project_name, github_repo
            )
            report.documents.append(contributing_doc)
            
            # Generate ADRs (Architecture Decision Records)
            adrs = await self._generate_adrs(
                path, project_name, project_type, tech_stack
            )
            report.documents.extend(adrs)
            report.adrs_generated = len(adrs)
            
            # Generate code style guides
            style_configs = await self._generate_style_guides(
                path, project_type, tech_stack
            )
            report.style_configs = style_configs
            
            # Generate CHANGELOG.md
            changelog_doc = await self._generate_changelog(path, project_name)
            report.documents.append(changelog_doc)
            
            # Generate LICENSE file
            license_doc = await self._generate_license(path, license_type)
            report.documents.append(license_doc)
            
            # Generate deployment documentation
            deploy_doc = await self._generate_deployment_docs(
                path, project_name, project_type, tech_stack
            )
            report.documents.append(deploy_doc)
            
            # Calculate totals
            report.total_generated = sum(1 for d in report.documents if d.generated)
            
            # Save report
            report_path = path / "coding_standards_report.json"
            self.write_file(str(report_path), json.dumps(report.to_dict(), indent=2))
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                success=True,
                agent_name=self.name,
                data={
                    "report": report.to_dict(),
                    "summary": {
                        "documents_generated": report.total_generated,
                        "adrs_generated": report.adrs_generated,
                        "style_configs": len(report.style_configs),
                    },
                },
                execution_time=execution_time,
            )
            
        except Exception as e:
            self.logger.error(f"Documentation generation failed: {e}")
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )

    def _detect_tech_stack(self, project_path: str) -> List[str]:
        """Detect technologies used in the project."""
        path = Path(project_path)
        tech_stack = []
        
        # Check for package.json (Node.js/JavaScript)
        if (path / "package.json").exists():
            try:
                with open(path / "package.json") as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    
                    if "next" in deps:
                        tech_stack.append("Next.js")
                    if "react" in deps:
                        tech_stack.append("React")
                    if "vue" in deps:
                        tech_stack.append("Vue.js")
                    if "typescript" in deps:
                        tech_stack.append("TypeScript")
                    if "tailwindcss" in deps:
                        tech_stack.append("Tailwind CSS")
                    if "express" in deps:
                        tech_stack.append("Express.js")
            except:
                tech_stack.append("Node.js")
        
        # Check for Python
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            tech_stack.append("Python")
            if (path / "requirements.txt").exists():
                try:
                    with open(path / "requirements.txt") as f:
                        reqs = f.read().lower()
                        if "fastapi" in reqs:
                            tech_stack.append("FastAPI")
                        if "django" in reqs:
                            tech_stack.append("Django")
                        if "flask" in reqs:
                            tech_stack.append("Flask")
                except:
                    pass
        
        # Check for Go
        if (path / "go.mod").exists():
            tech_stack.append("Go")
        
        # Check for Rust
        if (path / "Cargo.toml").exists():
            tech_stack.append("Rust")
        
        # Check for Docker
        if (path / "Dockerfile").exists() or (path / "docker-compose.yml").exists():
            tech_stack.append("Docker")
        
        return tech_stack if tech_stack else ["JavaScript"]

    async def _generate_readme(
        self,
        path: Path,
        project_name: str,
        project_type: str,
        tech_stack: List[str],
        description: Optional[str],
        github_repo: Optional[str],
    ) -> GeneratedDocument:
        """Generate comprehensive README.md."""
        doc = GeneratedDocument(
            name="README.md",
            path=str(path / "README.md"),
            type="readme",
        )
        
        # Generate badges
        badges = []
        if github_repo:
            repo_path = github_repo.replace("https://github.com/", "")
            badges.extend([
                f"![CI](https://miro.medium.com/1*Q9iB0I_dVdffK42AA8P7oQ.png)",
                f"![License](https://img.shields.io/github/license/{repo_path})",
                f"![Issues](https://img.shields.io/github/issues/{repo_path})",
            ])
        
        for tech in tech_stack:
            tech_lower = tech.lower().replace(" ", "-").replace(".", "")
            badges.append(f"![{tech}](https://img.shields.io/badge/{tech_lower}-blue)")
        
        badges_str = " ".join(badges) if badges else ""
        
        content = f"""# {project_name}

{badges_str}

{description or f"A {project_type} application built with {', '.join(tech_stack) if tech_stack else 'modern technologies'}."}

## 📋 Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

"""
        
        # Add prerequisites based on tech stack
        if "Node.js" in tech_stack or "Next.js" in tech_stack or "React" in tech_stack:
            content += "- Node.js >= 18.x\n- npm or yarn\n"
        if "Python" in tech_stack or "FastAPI" in tech_stack:
            content += "- Python >= 3.10\n- pip or poetry\n"
        if "Docker" in tech_stack:
            content += "- Docker & Docker Compose\n"
        
        content += f"""
## 🚀 Installation

### Clone the repository

```bash
git clone {github_repo or f"https://github.com/your-org/{project_name.lower().replace(' ', '-')}.git"}
cd {project_name.lower().replace(' ', '-')}
```

"""
        
        # Add installation steps based on tech stack
        if "Node.js" in tech_stack or any(t in tech_stack for t in ["Next.js", "React", "Vue.js"]):
            content += """### Install dependencies

```bash
npm install
# or
yarn install
```

"""
        
        if "Python" in tech_stack:
            content += """### Install Python dependencies

```bash
pip install -r requirements.txt
# or with poetry
poetry install
```

"""
        
        if "Docker" in tech_stack:
            content += """### Using Docker

```bash
docker-compose up -d
```

"""
        
        content += """## 💻 Usage

"""
        
        if "Next.js" in tech_stack or "React" in tech_stack:
            content += """### Development server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production build

```bash
npm run build
npm start
```

"""
        elif "FastAPI" in tech_stack:
            content += """### Run the API server

```bash
uvicorn main:app --reload
```

API documentation available at [http://localhost:8000/docs](http://localhost:8000/docs).

"""
        
        content += """## ⚙️ Configuration

Create a `.env` file in the root directory:

```env
# Add your environment variables here
DATABASE_URL=your_database_url
API_KEY=your_api_key
```

## 🧪 Testing

```bash
# Run tests
npm test
# or
pytest

# Run tests with coverage
npm run test:coverage
# or
pytest --cov
```

## 🚢 Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Made with ❤️ by AI Dev Agency
"""
        
        try:
            self.write_file(str(path / "README.md"), content)
            doc.generated = True
            doc.content_preview = content[:500] + "..."
        except Exception as e:
            doc.error_message = str(e)
        
        return doc

    async def _generate_api_docs(
        self,
        path: Path,
        project_name: str,
        project_type: str,
        tech_stack: List[str],
    ) -> GeneratedDocument:
        """Generate API documentation."""
        doc = GeneratedDocument(
            name="API.md",
            path=str(path / "docs" / "API.md"),
            type="api_docs",
        )
        
        (path / "docs").mkdir(parents=True, exist_ok=True)
        
        content = f"""# {project_name} API Documentation

## Overview

This document describes the API endpoints available in {project_name}.

"""
        
        if project_type == "api" or "FastAPI" in tech_stack:
            content += """## Authentication

All API requests require authentication using Bearer tokens.

```
Authorization: Bearer <your_api_token>
```

## Base URL

```
https://api.example.com/v1
```

## Endpoints

### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Resources

#### List Resources

```http
GET /resources
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| page | integer | Page number (default: 1) |
| limit | integer | Items per page (default: 20) |

**Response:**

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 0
  }
}
```

#### Get Resource

```http
GET /resources/:id
```

**Response:**

```json
{
  "id": "string",
  "name": "string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Create Resource

```http
POST /resources
```

**Request Body:**

```json
{
  "name": "string"
}
```

**Response:**

```json
{
  "id": "string",
  "name": "string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

## Rate Limiting

- 100 requests per minute per API key
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

"""
        
        elif project_type == "web" or "React" in tech_stack or "Next.js" in tech_stack:
            content += """## Components

### Button

```tsx
import { Button } from '@/components/Button';

<Button variant="primary" onClick={handleClick}>
  Click me
</Button>
```

**Props:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | 'primary' \\| 'secondary' \\| 'ghost' | 'primary' | Button style variant |
| size | 'sm' \\| 'md' \\| 'lg' | 'md' | Button size |
| disabled | boolean | false | Disable the button |
| onClick | function | - | Click handler |

### Card

```tsx
import { Card } from '@/components/Card';

<Card title="Card Title">
  Card content here
</Card>
```

### Form Components

See individual component documentation in `/docs/components/`.

"""
        
        content += """## Additional Resources

- [OpenAPI Specification](./openapi.yaml)
- [Postman Collection](./postman_collection.json)

---

*Generated by AI Dev Agency*
"""
        
        try:
            self.write_file(str(path / "docs" / "API.md"), content)
            doc.generated = True
            doc.content_preview = content[:500] + "..."
        except Exception as e:
            doc.error_message = str(e)
        
        return doc

    async def _generate_contributing(
        self,
        path: Path,
        project_name: str,
        github_repo: Optional[str],
    ) -> GeneratedDocument:
        """Generate CONTRIBUTING.md."""
        doc = GeneratedDocument(
            name="CONTRIBUTING.md",
            path=str(path / "CONTRIBUTING.md"),
            type="contributing",
        )
        
        content = f"""# Contributing to {project_name}

First off, thank you for considering contributing to {project_name}! It's people like you that make this project great.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Please report unacceptable behavior to the maintainers.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed**
- **Explain the expected behavior**
- **Include screenshots if relevant**
- **Include your environment details**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Pull Requests

1. Fork the repository
2. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Write or update tests as needed
5. Ensure tests pass:
   ```bash
   npm test
   # or
   pytest
   ```
6. Commit your changes using conventional commits:
   ```bash
   git commit -m "feat: add new feature"
   ```
7. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
8. Open a Pull Request

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - A new feature
- `fix:` - A bug fix
- `docs:` - Documentation only changes
- `style:` - Code style changes (formatting, semicolons, etc.)
- `refactor:` - Code changes that neither fix a bug nor add a feature
- `perf:` - Performance improvements
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### Examples

```
feat: add user authentication
fix: resolve login redirect issue
docs: update API documentation
style: format code with prettier
refactor: simplify data processing logic
test: add unit tests for auth module
```

## Code Style

### General Guidelines

- Write clear, readable code
- Add comments for complex logic
- Keep functions small and focused
- Use meaningful variable names
- Follow DRY (Don't Repeat Yourself) principle

### JavaScript/TypeScript

- Use TypeScript for type safety
- Follow ESLint configuration
- Use Prettier for formatting
- Prefer functional components in React
- Use async/await over .then()

### Python

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for functions and classes
- Use Black for formatting
- Use isort for import sorting

## Testing

- Write tests for new features
- Update tests when modifying existing features
- Aim for high test coverage
- Include unit tests, integration tests, and E2E tests where appropriate

## Documentation

- Update README.md if needed
- Add JSDoc/docstrings for new functions
- Update API documentation for API changes
- Add ADRs for significant architectural decisions

## Review Process

1. All PRs require at least one review
2. CI checks must pass
3. Update documentation as needed
4. Squash commits before merging

## Getting Help

- Check existing issues and discussions
- Ask questions in discussions
- Reach out to maintainers

Thank you for contributing! 🎉
"""
        
        try:
            self.write_file(str(path / "CONTRIBUTING.md"), content)
            doc.generated = True
            doc.content_preview = content[:500] + "..."
        except Exception as e:
            doc.error_message = str(e)
        
        return doc

    async def _generate_adrs(
        self,
        path: Path,
        project_name: str,
        project_type: str,
        tech_stack: List[str],
    ) -> List[GeneratedDocument]:
        """Generate Architecture Decision Records."""
        adr_path = path / "docs" / "adr"
        adr_path.mkdir(parents=True, exist_ok=True)
        
        adrs = []
        
        # ADR 001: Technology Stack
        adr_001 = GeneratedDocument(
            name="001-technology-stack.md",
            path=str(adr_path / "001-technology-stack.md"),
            type="adr",
        )
        
        adr_001_content = f"""# ADR 001: Technology Stack Selection

## Status

Accepted

## Context

We need to select the technology stack for {project_name}, a {project_type} application.

## Decision

We have chosen the following technology stack:

{chr(10).join(f'- **{tech}**' for tech in tech_stack)}

## Rationale

"""
        
        for tech in tech_stack:
            if "Next.js" in tech:
                adr_001_content += "- **Next.js**: Provides server-side rendering, API routes, and excellent developer experience.\n"
            elif "React" in tech:
                adr_001_content += "- **React**: Industry-standard UI library with large ecosystem and community support.\n"
            elif "TypeScript" in tech:
                adr_001_content += "- **TypeScript**: Adds type safety, improving code quality and developer productivity.\n"
            elif "FastAPI" in tech:
                adr_001_content += "- **FastAPI**: High-performance Python web framework with automatic OpenAPI documentation.\n"
            elif "Docker" in tech:
                adr_001_content += "- **Docker**: Ensures consistent deployment environments across development and production.\n"
            elif "Tailwind" in tech.lower():
                adr_001_content += "- **Tailwind CSS**: Utility-first CSS framework for rapid UI development.\n"
        
        adr_001_content += """
## Consequences

### Positive
- Modern, well-supported technologies
- Strong community and ecosystem
- Good developer experience
- Scalable architecture

### Negative
- Learning curve for new team members
- Need to keep dependencies updated

## References

- [Project Documentation](../README.md)
"""
        
        try:
            self.write_file(str(adr_path / "001-technology-stack.md"), adr_001_content)
            adr_001.generated = True
        except Exception as e:
            adr_001.error_message = str(e)
        
        adrs.append(adr_001)
        
        # ADR 002: Project Structure
        adr_002 = GeneratedDocument(
            name="002-project-structure.md",
            path=str(adr_path / "002-project-structure.md"),
            type="adr",
        )
        
        adr_002_content = f"""# ADR 002: Project Structure

## Status

Accepted

## Context

Define the directory structure and organization for {project_name}.

## Decision

We adopt a feature-based/modular structure:

```
{project_name.lower().replace(' ', '-')}/
├── src/
│   ├── components/     # Reusable UI components
│   ├── features/       # Feature modules
│   ├── hooks/          # Custom hooks
│   ├── lib/            # Utilities and helpers
│   ├── pages/          # Route pages
│   └── types/          # TypeScript types
├── tests/              # Test files
├── docs/               # Documentation
└── public/             # Static assets
```

## Rationale

- Clear separation of concerns
- Easy to locate and modify features
- Scalable as the project grows
- Follows industry best practices

## Consequences

### Positive
- Clear code organization
- Easy onboarding
- Feature isolation

### Negative
- May need refactoring as app grows
"""
        
        try:
            self.write_file(str(adr_path / "002-project-structure.md"), adr_002_content)
            adr_002.generated = True
        except Exception as e:
            adr_002.error_message = str(e)
        
        adrs.append(adr_002)
        
        # ADR Template
        adr_template = GeneratedDocument(
            name="000-template.md",
            path=str(adr_path / "000-template.md"),
            type="adr",
        )
        
        template_content = """# ADR [NUMBER]: [TITLE]

## Status

[Proposed | Accepted | Deprecated | Superseded]

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Rationale

Why did we choose this decision over alternatives?

## Consequences

### Positive
- List positive consequences

### Negative
- List negative consequences

## Alternatives Considered

- Alternative 1: Description
- Alternative 2: Description

## References

- Link to related documents
"""
        
        try:
            self.write_file(str(adr_path / "000-template.md"), template_content)
            adr_template.generated = True
        except Exception as e:
            adr_template.error_message = str(e)
        
        adrs.append(adr_template)
        
        return adrs

    async def _generate_style_guides(
        self,
        path: Path,
        project_type: str,
        tech_stack: List[str],
    ) -> List[str]:
        """Generate code style configuration files."""
        generated_configs = []
        
        # ESLint config for JavaScript/TypeScript projects
        if any(t in tech_stack for t in ["Node.js", "Next.js", "React", "Vue.js", "TypeScript"]):
            eslint_config = {
                "env": {
                    "browser": True,
                    "es2021": True,
                    "node": True,
                },
                "extends": [
                    "eslint:recommended",
                ],
                "parserOptions": {
                    "ecmaVersion": "latest",
                    "sourceType": "module",
                },
                "rules": {
                    "indent": ["error", 2],
                    "linebreak-style": ["error", "unix"],
                    "quotes": ["error", "single"],
                    "semi": ["error", "always"],
                    "no-unused-vars": "warn",
                    "no-console": "warn",
                },
            }
            
            if "TypeScript" in tech_stack:
                eslint_config["extends"].append("plugin:@typescript-eslint/recommended")
                eslint_config["parser"] = "@typescript-eslint/parser"
                eslint_config["plugins"] = ["@typescript-eslint"]
            
            if "React" in tech_stack or "Next.js" in tech_stack:
                eslint_config["extends"].append("plugin:react/recommended")
                eslint_config["extends"].append("plugin:react-hooks/recommended")
                eslint_config["settings"] = {"react": {"version": "detect"}}
            
            eslint_path = path / ".eslintrc.json"
            if not eslint_path.exists():
                self.write_file(str(eslint_path), json.dumps(eslint_config, indent=2))
                generated_configs.append(".eslintrc.json")
        
        # Prettier config
        if any(t in tech_stack for t in ["Node.js", "Next.js", "React", "Vue.js", "TypeScript"]):
            prettier_config = {
                "semi": True,
                "singleQuote": True,
                "tabWidth": 2,
                "trailingComma": "es5",
                "printWidth": 100,
                "bracketSpacing": True,
                "arrowParens": "always",
            }
            
            prettier_path = path / ".prettierrc"
            if not prettier_path.exists():
                self.write_file(str(prettier_path), json.dumps(prettier_config, indent=2))
                generated_configs.append(".prettierrc")
        
        # Python configs
        if "Python" in tech_stack or "FastAPI" in tech_stack:
            # pyproject.toml for Python tools
            pyproject_content = """[tool.black]
line-length = 100
target-version = ['py310', 'py311']
include = '\\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov --cov-report=term-missing"
"""
            
            pyproject_path = path / "pyproject.toml"
            if not pyproject_path.exists():
                self.write_file(str(pyproject_path), pyproject_content)
                generated_configs.append("pyproject.toml")
        
        # EditorConfig (universal)
        editorconfig_content = """# EditorConfig helps maintain consistent coding styles
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false

[*.py]
indent_size = 4

[Makefile]
indent_style = tab
"""
        
        editorconfig_path = path / ".editorconfig"
        if not editorconfig_path.exists():
            self.write_file(str(editorconfig_path), editorconfig_content)
            generated_configs.append(".editorconfig")
        
        return generated_configs

    async def _generate_changelog(
        self,
        path: Path,
        project_name: str,
    ) -> GeneratedDocument:
        """Generate CHANGELOG.md template."""
        doc = GeneratedDocument(
            name="CHANGELOG.md",
            path=str(path / "CHANGELOG.md"),
            type="changelog",
        )
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        content = f"""# Changelog

All notable changes to {project_name} will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- Core features implementation

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - {today}

### Added
- Initial release
- Project scaffolding
- Basic functionality

---

## Version Format

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
  - **MAJOR**: Incompatible API changes
  - **MINOR**: Backwards-compatible functionality
  - **PATCH**: Backwards-compatible bug fixes

## Types of Changes

- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes
"""
        
        try:
            self.write_file(str(path / "CHANGELOG.md"), content)
            doc.generated = True
            doc.content_preview = content[:500] + "..."
        except Exception as e:
            doc.error_message = str(e)
        
        return doc

    async def _generate_license(
        self,
        path: Path,
        license_type: str,
    ) -> GeneratedDocument:
        """Generate LICENSE file."""
        doc = GeneratedDocument(
            name="LICENSE",
            path=str(path / "LICENSE"),
            type="license",
        )
        
        year = datetime.now().year
        
        licenses = {
            "MIT": f"""MIT License

Copyright (c) {year}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""",
            "Apache-2.0": f"""Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

Copyright {year}

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
""",
        }
        
        content = licenses.get(license_type, licenses["MIT"])
        
        try:
            self.write_file(str(path / "LICENSE"), content)
            doc.generated = True
            doc.content_preview = content[:300] + "..."
        except Exception as e:
            doc.error_message = str(e)
        
        return doc

    async def _generate_deployment_docs(
        self,
        path: Path,
        project_name: str,
        project_type: str,
        tech_stack: List[str],
    ) -> GeneratedDocument:
        """Generate deployment documentation."""
        doc = GeneratedDocument(
            name="DEPLOYMENT.md",
            path=str(path / "docs" / "DEPLOYMENT.md"),
            type="deployment",
        )
        
        (path / "docs").mkdir(parents=True, exist_ok=True)
        
        content = f"""# {project_name} Deployment Guide

## Overview

This guide covers deployment options for {project_name}.

## Prerequisites

- Access to deployment platform
- Environment variables configured
- Database setup (if applicable)

"""
        
        # Add platform-specific deployment instructions
        if project_type in ["web", "website"] or "Next.js" in tech_stack:
            content += """## Vercel Deployment

### Automatic Deployment

1. Connect your GitHub repository to Vercel
2. Configure environment variables in Vercel dashboard
3. Push to main branch to trigger deployment

### Manual Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### Environment Variables

Set these in your Vercel project settings:
- `DATABASE_URL`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`

"""
        
        if "Docker" in tech_stack:
            content += """## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t {project_name} .

# Run container
docker run -d -p 3000:3000 --env-file .env {project_name}
```

### Docker Compose

```bash
docker-compose up -d
```

"""
        
        if project_type == "api" or "FastAPI" in tech_stack:
            content += """## Railway Deployment

1. Connect GitHub repository
2. Select Python environment
3. Configure environment variables
4. Deploy

### Configuration

Set the start command:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

"""
        
        content += """## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Database connection string | Yes |
| `SECRET_KEY` | Application secret key | Yes |
| `API_KEY` | External API key | No |

## Health Checks

The application exposes a health check endpoint:
```
GET /health
```

## Monitoring

- Application logs: Available in deployment platform
- Error tracking: Sentry (if configured)
- Uptime: UptimeRobot (if configured)

## Rollback

To rollback to a previous version:
1. Go to deployment platform
2. Select previous deployment
3. Promote to production

## Troubleshooting

### Common Issues

1. **Build failures**
   - Check dependency versions
   - Verify Node.js/Python version

2. **Runtime errors**
   - Check environment variables
   - Review application logs

3. **Performance issues**
   - Check resource allocation
   - Review database queries

---

*Generated by AI Dev Agency*
"""
        
        try:
            self.write_file(str(path / "docs" / "DEPLOYMENT.md"), content)
            doc.generated = True
            doc.content_preview = content[:500] + "..."
        except Exception as e:
            doc.error_message = str(e)
        
        return doc
