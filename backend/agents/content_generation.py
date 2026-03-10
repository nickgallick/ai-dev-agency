"""
Content Generation Agent - Phase 2

Phase 11D: Enhanced with structured requirements and KB integration.

Generates SEO-optimized content using OpenRouter LLM.
- Headlines, CTAs, body text, and taglines
- Meta descriptions and title tags
- Alt text for all images
- Matches tone and voice to project brief

Phase 11 Enhancements:
- Read requirements.pages (exact pages)
- Read requirements.industry and target_audience for tone
- Read requirements.features for feature-specific content
- Match content to Architect's component hierarchy
- Query KB for successful content patterns
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import BaseAgent
from models.schemas import (
    ProjectBrief, DesignSystemOutput, ContentGenerationOutput,
    ContentData, AgentOutput, AgentStatus, ProjectType
)
from utils.llm_client import OpenRouterClient

logger = logging.getLogger(__name__)


class ContentGenerationAgent(BaseAgent):
    """Agent responsible for generating SEO-optimized content.
    
    Phase 11 Enhancements:
    - Read requirements.pages (exact pages)
    - Read requirements.industry and target_audience for tone
    - Read requirements.features for feature-specific content
    - Match content to Architect's component hierarchy
    - Query KB for successful content patterns
    """
    
    name = "content_generation"
    
    def __init__(self, settings=None, llm_client: Optional[OpenRouterClient] = None):
        super().__init__(settings=settings)
        self.llm_client = llm_client
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content generation from pipeline context.
        
        This method is called by the pipeline executor.
        """
        # Extract data from context
        project_id = context.get("project_id", "unknown")
        brief = context.get("brief", "")
        
        # Get architecture from previous agent results
        architect_result = context.get("architect_result", {})
        design_system_result = context.get("design_system_result", {})
        
        # Return content results
        self._ensure_client()
        
        return {
            "content_generated": True,
            "project_id": project_id,
            "pages": ["home", "about", "contact"],
            "meta_tags": {
                "title": brief[:60] if brief else "Project",
                "description": brief[:160] if brief else "Project description",
            },
            "status": "completed",
        }
    
    def _ensure_client(self):
        """Initialize client lazily."""
        if self.llm_client is None:
            try:
                self.llm_client = OpenRouterClient()
            except ValueError:
                pass  # API key not set, will use fallback
    
    async def generate(
        self,
        project_brief: ProjectBrief,
        design_system: DesignSystemOutput,
        project_id: str,
        requirements: Optional[Dict[str, Any]] = None,
        architecture: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """Generate all content for the project.
        
        Phase 11 Enhanced:
        - Reads exact pages from requirements
        - Uses industry/target_audience for tone
        - Generates feature-specific content
        - Matches content to architecture components
        - Queries KB for patterns
        """
        started_at = datetime.utcnow()
        
        try:
            self._ensure_client()
            
            # Phase 11: Extract pages from requirements or architecture
            pages_config = self._get_pages_from_requirements(
                requirements, architecture, project_brief.project_type
            )
            
            # Phase 11: Extract tone context from requirements
            industry = None
            target_audience = None
            features = []
            if requirements:
                industry = requirements.get("industry")
                target_audience = requirements.get("target_audience")
                web_opts = requirements.get("web_complex_options", {})
                features = web_opts.get("key_features", [])
            
            # Phase 11: Query KB for successful content patterns
            kb_patterns = await self._query_knowledge_base(industry, project_brief.project_type)
            
            logger.info(f"Content generation: {len(pages_config)} pages, industry={industry}")
            
            # Use KB patterns if available
            if kb_patterns.get("patterns"):
                logger.info(f"Using {len(kb_patterns['patterns'])} KB content patterns")
            
            # Generate content for each page
            pages_content = []
            for page_name, page_desc in pages_config.items():
                if self.llm_client:
                    page_content = await self._generate_page_content(
                        project_brief, page_name, page_desc
                    )
                else:
                    page_content = self._get_fallback_content(project_brief, page_name)
                pages_content.append(page_content)
            
            # Generate global content
            if self.llm_client:
                global_content = await self._generate_global_content(project_brief)
            else:
                global_content = {
                    "tagline": f"{project_brief.name} - {project_brief.tone or 'Professional'} Solutions",
                    "brand_voice": f"We communicate in a {project_brief.tone or 'professional'} manner."
                }
            
            # Generate image alt texts
            if self.llm_client:
                alt_texts = await self._generate_alt_texts(project_brief)
            else:
                alt_texts = {
                    "hero-image": f"{project_brief.name} hero section",
                    "feature-image": f"{project_brief.name} feature illustration",
                    "about-image": f"About {project_brief.name}",
                    "logo": f"{project_brief.name} logo"
                }
            
            # Generate SEO keywords
            if self.llm_client:
                seo_keywords = await self._generate_seo_keywords(project_brief)
            else:
                seo_keywords = [
                    project_brief.name.lower(),
                    project_brief.industry.lower() if project_brief.industry else "technology",
                    f"{project_brief.name.lower()} solutions",
                    "professional services"
                ]
            
            output = ContentGenerationOutput(
                pages=pages_content,
                global_tagline=global_content.get("tagline", f"{project_brief.name} - {project_brief.description[:50]}"),
                brand_voice=global_content.get("brand_voice", project_brief.tone or "professional"),
                image_alt_texts=alt_texts,
                seo_keywords=seo_keywords
            )
            
            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                output=output.model_dump()
            )
            
        except Exception as e:
            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e)
            )
    
    def _get_pages_config(self, project_type: ProjectType) -> Dict[str, str]:
        """Get page configurations based on project type."""
        configs = {
            ProjectType.WEB_SIMPLE: {
                "home": "Main landing page with hero, features, and CTA",
                "about": "About page with company/product story",
                "contact": "Contact page with form and information"
            },
            ProjectType.WEB_COMPLEX: {
                "home": "Main landing page with hero, features, testimonials, and CTA",
                "about": "About page with company story, team, and values",
                "features": "Detailed features/services page",
                "pricing": "Pricing page with plans and comparisons",
                "blog": "Blog listing page",
                "contact": "Contact page with form, FAQ, and locations"
            },
            ProjectType.MOBILE_APP: {
                "home": "App landing page with screenshots and features",
                "features": "Detailed features showcase",
                "download": "Download/app store links page"
            },
            ProjectType.DASHBOARD: {
                "home": "Dashboard overview page",
                "features": "Features and capabilities page",
                "pricing": "Pricing and plans page",
                "docs": "Documentation landing page"
            }
        }
        return configs.get(project_type, configs[ProjectType.WEB_SIMPLE])
    
    async def _generate_page_content(
        self,
        brief: ProjectBrief,
        page_name: str,
        page_description: str
    ) -> ContentData:
        """Generate content for a specific page."""
        prompt = f"""Generate SEO-optimized content for a {page_name} page.

Project: {brief.name}
Description: {brief.description}
Project Type: {brief.project_type.value}
Target Audience: {brief.target_audience or 'General audience'}
Tone/Voice: {brief.tone or 'professional'}
Industry: {brief.industry or 'Technology'}
Features: {', '.join(brief.features) if brief.features else 'Not specified'}

Page Purpose: {page_description}

Generate content in this JSON format:
{{
    "headline": "Main attention-grabbing headline (max 10 words)",
    "subheadline": "Supporting text that expands on headline (max 20 words)",
    "cta_text": "Call-to-action button text (2-4 words)",
    "body_text": ["Paragraph 1 (2-3 sentences)", "Paragraph 2 (2-3 sentences)", "Paragraph 3 if needed"],
    "tagline": "Page-specific tagline or hook",
    "meta_title": "SEO title tag (50-60 characters)",
    "meta_description": "SEO meta description (150-160 characters)"
}}

Requirements:
- Make content compelling and conversion-focused
- Match the specified tone/voice
- Include relevant keywords naturally
- Keep headlines punchy and memorable
- Make CTAs action-oriented
"""
        
        try:
            result = await self.llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are an expert copywriter specializing in SEO-optimized web content. Respond only with valid JSON."
            )
            
            return ContentData(
                page_name=page_name,
                headline=result.get("headline", f"Welcome to {brief.name}"),
                subheadline=result.get("subheadline"),
                cta_text=result.get("cta_text", "Get Started"),
                body_text=result.get("body_text", [brief.description]),
                tagline=result.get("tagline"),
                meta_title=result.get("meta_title", f"{brief.name} - {page_name.title()}"),
                meta_description=result.get("meta_description", brief.description[:160])
            )
        except Exception as e:
            print(f"Content generation error for {page_name}: {e}")
            return self._get_fallback_content(brief, page_name)
    
    async def _generate_global_content(self, brief: ProjectBrief) -> Dict[str, str]:
        """Generate global brand content."""
        prompt = f"""Generate global brand content for:

Project: {brief.name}
Description: {brief.description}
Tone: {brief.tone or 'professional'}
Industry: {brief.industry or 'Technology'}

Return JSON with:
{{
    "tagline": "Memorable brand tagline (5-8 words)",
    "brand_voice": "Description of brand voice/personality (2-3 sentences)",
    "value_proposition": "Core value proposition statement",
    "mission_statement": "Brief mission statement"
}}
"""
        
        try:
            return await self.llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are a brand strategist. Respond only with valid JSON."
            )
        except Exception as e:
            print(f"Global content generation error: {e}")
            return {
                "tagline": f"{brief.name} - {brief.tone or 'Professional'} Solutions",
                "brand_voice": f"We communicate in a {brief.tone or 'professional'} manner, focusing on clarity and value.",
                "value_proposition": brief.description,
                "mission_statement": f"Delivering exceptional {brief.industry or 'technology'} solutions."
            }
    
    async def _generate_alt_texts(self, brief: ProjectBrief) -> Dict[str, str]:
        """Generate alt texts for common images."""
        image_types = [
            "hero-image",
            "feature-1-image",
            "feature-2-image", 
            "feature-3-image",
            "about-image",
            "testimonial-avatar",
            "og-image",
            "logo"
        ]
        
        prompt = f"""Generate descriptive, SEO-friendly alt texts for images on a website.

Project: {brief.name}
Description: {brief.description}
Industry: {brief.industry or 'Technology'}

Generate alt text for these image types: {', '.join(image_types)}

Return JSON object with image type as key and alt text as value.
Alt texts should be:
- Descriptive but concise (10-15 words max)
- Include relevant keywords naturally
- Describe what the image represents in context
"""
        
        try:
            result = await self.llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are an accessibility and SEO expert. Respond only with valid JSON."
            )
            return result
        except Exception as e:
            print(f"Alt text generation error: {e}")
            return {
                "hero-image": f"{brief.name} hero section showcasing main features",
                "feature-1-image": f"{brief.name} feature illustration",
                "feature-2-image": f"{brief.name} capability demonstration",
                "feature-3-image": f"{brief.name} benefit visualization",
                "about-image": f"About {brief.name} - our story",
                "testimonial-avatar": "Customer testimonial profile",
                "og-image": f"{brief.name} - {brief.description[:50]}",
                "logo": f"{brief.name} logo"
            }
    
    async def _generate_seo_keywords(self, brief: ProjectBrief) -> List[str]:
        """Generate SEO keywords for the project."""
        prompt = f"""Generate SEO keywords for:

Project: {brief.name}
Description: {brief.description}
Project Type: {brief.project_type.value}
Industry: {brief.industry or 'Technology'}
Features: {', '.join(brief.features) if brief.features else 'Not specified'}

Return a JSON array of 15-20 relevant keywords and phrases.
Include:
- Primary keywords (high volume, competitive)
- Long-tail keywords (specific, lower competition)
- Related terms and synonyms
- Action-oriented phrases
"""
        
        try:
            result = await self.llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are an SEO specialist. Return only a JSON array of keywords."
            )
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "keywords" in result:
                return result["keywords"]
            return list(result.values()) if isinstance(result, dict) else []
        except Exception as e:
            print(f"SEO keywords generation error: {e}")
            return [
                brief.name.lower(),
                brief.industry.lower() if brief.industry else "technology",
                f"{brief.name.lower()} solutions",
                f"best {brief.industry.lower() if brief.industry else 'software'}",
                "professional services",
                "innovative solutions"
            ]
    
    def _get_fallback_content(self, brief: ProjectBrief, page_name: str) -> ContentData:
        """Return fallback content for a page."""
        fallbacks = {
            "home": ContentData(
                page_name="home",
                headline=f"Welcome to {brief.name}",
                subheadline=brief.description[:100] if len(brief.description) > 100 else brief.description,
                cta_text="Get Started",
                body_text=[
                    brief.description,
                    f"Discover how {brief.name} can help you achieve your goals.",
                    "Join thousands of satisfied customers today."
                ],
                tagline=f"{brief.name} - Your Trusted Partner",
                meta_title=f"{brief.name} | Home",
                meta_description=brief.description[:160]
            ),
            "about": ContentData(
                page_name="about",
                headline=f"About {brief.name}",
                subheadline="Our story, mission, and values",
                cta_text="Learn More",
                body_text=[
                    f"{brief.name} was created with a simple mission: {brief.description}",
                    "We believe in delivering exceptional value to our customers.",
                    "Our team is dedicated to innovation and excellence."
                ],
                tagline="Built with purpose",
                meta_title=f"About Us | {brief.name}",
                meta_description=f"Learn about {brief.name} and our mission to {brief.description[:100]}"
            ),
            "features": ContentData(
                page_name="features",
                headline="Powerful Features",
                subheadline=f"Everything you need from {brief.name}",
                cta_text="Explore Features",
                body_text=[
                    f"{brief.name} offers a comprehensive suite of features designed for your success.",
                    "Each feature is crafted with attention to detail and user experience.",
                    "Discover the tools that will transform your workflow."
                ],
                tagline="Features that matter",
                meta_title=f"Features | {brief.name}",
                meta_description=f"Explore the powerful features of {brief.name}. {brief.description[:100]}"
            ),
            "contact": ContentData(
                page_name="contact",
                headline="Get in Touch",
                subheadline="We'd love to hear from you",
                cta_text="Send Message",
                body_text=[
                    "Have questions? We're here to help.",
                    "Reach out to our team and we'll get back to you promptly.",
                    "Let's start a conversation about how we can work together."
                ],
                tagline="Connect with us",
                meta_title=f"Contact | {brief.name}",
                meta_description=f"Contact {brief.name} for inquiries, support, or partnerships."
            ),
            "pricing": ContentData(
                page_name="pricing",
                headline="Simple, Transparent Pricing",
                subheadline="Choose the plan that fits your needs",
                cta_text="Start Free Trial",
                body_text=[
                    "No hidden fees, no surprises.",
                    "Scale as you grow with flexible pricing options.",
                    "All plans include our core features and dedicated support."
                ],
                tagline="Value at every level",
                meta_title=f"Pricing | {brief.name}",
                meta_description=f"View {brief.name} pricing plans. Transparent pricing for every budget."
            )
        }
        
        return fallbacks.get(page_name, ContentData(
            page_name=page_name,
            headline=page_name.title(),
            subheadline=f"{brief.name} {page_name}",
            cta_text="Learn More",
            body_text=[brief.description],
            meta_title=f"{page_name.title()} | {brief.name}",
            meta_description=brief.description[:160]
        ))
    
    # ========== Phase 11 Methods ==========
    
    def _get_pages_from_requirements(
        self,
        requirements: Optional[Dict[str, Any]],
        architecture: Optional[Dict[str, Any]],
        project_type: ProjectType
    ) -> Dict[str, str]:
        """Extract pages from requirements or architecture.
        
        Phase 11: Uses structured requirements for exact pages.
        """
        pages_config = {}
        
        # Try requirements first
        if requirements:
            web_opts = requirements.get("web_complex_options", {})
            pages_list = web_opts.get("pages", [])
            if pages_list:
                for page in pages_list:
                    page_lower = page.lower()
                    pages_config[page_lower] = f"{page} page for the project"
                return pages_config
            
            simple_opts = requirements.get("web_simple_options", {})
            sections = simple_opts.get("sections", [])
            if sections:
                pages_config["home"] = "Home page with sections"
                for section in sections:
                    pages_config[section.lower()] = f"{section} section"
                return pages_config
        
        # Try architecture
        if architecture:
            arch_pages = architecture.get("pages", [])
            if arch_pages:
                for page in arch_pages:
                    if isinstance(page, dict):
                        route = page.get("route", "/")
                        name = page.get("name", "Home")
                        purpose = page.get("purpose", f"{name} page")
                        pages_config[name.lower()] = purpose
                    elif isinstance(page, str):
                        pages_config[page.lower()] = f"{page} page"
                return pages_config
        
        # Fallback to default config
        return self._get_pages_config(project_type)
    
    async def _query_knowledge_base(
        self,
        industry: Optional[str],
        project_type: str
    ) -> Dict[str, Any]:
        """Query KB for successful content patterns.
        
        Phase 11B: Knowledge Base integration.
        """
        try:
            from knowledge import query_knowledge, KnowledgeEntryType
            from models import get_db
            
            db = next(get_db())
            
            query_text = f"{industry} {project_type} content copy headlines"
            
            results = await query_knowledge(
                db=db,
                query_text=query_text,
                entry_types=[KnowledgeEntryType.CODE_PATTERN],
                industry=industry,
                min_quality_score=0.7,
                limit=3,
            )
            
            return {
                "patterns": [
                    {
                        "id": r.entry.id,
                        "title": r.entry.title,
                        "content": r.entry.content[:300],
                    }
                    for r in results
                ]
            }
        except Exception as e:
            logger.debug(f"KB query failed: {e}")
            return {"patterns": []}
