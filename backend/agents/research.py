"""Research Agent - Step 2.

Phase 11D: Enhanced with structured requirements, Figma MCP, KB integration, and caching.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Conducts research on competitors, design trends, and best practices.
    
    Phase 11 Enhancements:
    - Read requirements.industry and requirements.target_audience
    - Read requirements.design.reference_urls - scrape via Browser MCP
    - Read requirements.design.figma_url - call Figma MCP to extract design tokens
    - Query KB before research (check for cached industry research)
    - Check Redis cache for research results
    - Write results to KB after completion
    """
    
    name = "research"
    description = "Research Agent"
    step_number = 2
    
    SYSTEM_PROMPT = """You are the Research Agent for an AI development agency.

Your job is to:
1. Research competitor websites and apps in the same industry
2. Identify current design trends and best practices
3. Recommend UI/UX patterns that work well for this type of project
4. Suggest color schemes, typography, and layout approaches
5. Note any technical considerations or integrations to consider

When Figma design tokens are provided, incorporate them into your recommendations.
When industry-specific research is cached, build upon existing knowledge.

Respond ONLY with valid JSON in this format:
{
    "competitor_analysis": [
        {
            "name": "competitor name",
            "url": "url if known",
            "strengths": ["what they do well"],
            "weaknesses": ["what could be improved"]
        }
    ],
    "design_trends": ["trend1", "trend2", ...],
    "recommended_patterns": [
        {
            "pattern": "pattern name",
            "use_case": "where to use it",
            "rationale": "why it works"
        }
    ],
    "color_recommendations": {
        "primary": "#hex",
        "secondary": "#hex",
        "accent": "#hex",
        "background": "#hex",
        "text": "#hex",
        "rationale": "why these colors"
    },
    "typography_recommendations": {
        "heading_font": "font name",
        "body_font": "font name",
        "rationale": "why these fonts"
    },
    "technical_considerations": ["consideration1", "consideration2"],
    "key_integrations": ["integration1", "integration2"],
    "figma_insights": {...} // If Figma data was provided
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct research based on project classification.
        
        Phase 11 Enhanced:
        - Reads structured requirements
        - Queries KB and cache before researching
        - Scrapes reference URLs via Browser MCP
        - Extracts Figma design tokens via Figma MCP
        - Writes results to KB after completion
        """
        classification = input_data.get("classification", {})
        brief = input_data.get("brief", "")
        cost_profile = input_data.get("cost_profile", "balanced")
        
        # Phase 11: Extract structured requirements
        requirements = input_data.get("requirements", {})
        industry = requirements.get("industry") or classification.get("industry")
        target_audience = requirements.get("target_audience") or classification.get("target_audience")
        design_prefs = requirements.get("design_preferences", {})
        reference_urls = requirements.get("reference_urls", [])
        figma_url = requirements.get("figma_url")
        project_type = requirements.get("project_type") or classification.get("project_type")
        
        # Phase 11B: Check cache first
        cache_key = f"research:{project_type}:{industry}:{hash(brief[:100])}"
        cached_result = await self._check_cache(cache_key)
        if cached_result:
            logger.info("Using cached research results")
            return cached_result
        
        # Phase 11B: Query KB for existing industry research
        kb_context = await self._query_knowledge_base(industry, project_type)
        
        # Phase 11: Scrape reference URLs via Browser MCP
        scraped_data = []
        if reference_urls:
            scraped_data = await self._scrape_reference_urls(reference_urls)
        
        # Phase 11: Extract Figma design tokens
        figma_tokens = None
        if figma_url:
            figma_tokens = await self._extract_figma_tokens(figma_url)
        
        model = self._select_model(cost_profile)
        
        # Build context string
        context_parts = []
        
        if industry:
            context_parts.append(f"Industry: {industry}")
        if target_audience:
            context_parts.append(f"Target Audience: {target_audience}")
        if design_prefs:
            context_parts.append(f"Design Preferences: {json.dumps(design_prefs)}")
        
        # Include KB context
        if kb_context.get("industry_research"):
            context_parts.append(f"\nCached Industry Research:\n{kb_context['industry_research'][:500]}...")
        
        # Include scraped reference data
        if scraped_data:
            context_parts.append(f"\nReference Sites Analyzed:")
            for site in scraped_data[:3]:
                context_parts.append(f"- {site.get('url', 'Unknown')}: {site.get('summary', '')[:200]}")
        
        # Include Figma tokens
        if figma_tokens:
            context_parts.append(f"\nFigma Design Tokens Extracted:")
            context_parts.append(json.dumps(figma_tokens, indent=2)[:500])
        
        context = "\n".join(context_parts)
        
        prompt = f"""Conduct research for this project:

Original Brief:
{brief}

Project Classification:
{json.dumps(classification, indent=2)}

Additional Context:
{context}

Research competitors, design trends, and provide recommendations.
If Figma tokens were provided, incorporate them into your color and typography recommendations."""
        
        result = await self.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.5,
            max_tokens=4096,
        )
        
        try:
            research = json.loads(result["content"])
        except json.JSONDecodeError:
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                research = json.loads(content[start:end])
            else:
                research = {"error": "Failed to parse response", "raw": content}
        
        # Add Figma tokens to research if extracted
        if figma_tokens:
            research["figma_tokens"] = figma_tokens
        
        await self.log_execution(
            input_data=input_data,
            output_data=research,
            model=model,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost=result["cost"],
            duration_ms=result["duration_ms"],
        )
        
        output = {
            "research": research,
            "model_used": model,
            "tokens": result["total_tokens"],
            "cost": result["cost"],
            "figma_tokens": figma_tokens,
            "scraped_references": scraped_data,
        }
        
        # Phase 11B: Cache the results
        await self._cache_result(cache_key, output)
        
        # Phase 11B: Write to KB
        await self._write_to_knowledge_base(research, industry, project_type)
        
        return output
    
    async def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check Redis cache for research results."""
        try:
            from ..cache import get_cache_manager
            cache = get_cache_manager()
            return cache.get(cache_key, "research")
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")
            return None
    
    async def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache research results in Redis."""
        try:
            from ..cache import get_cache_manager
            cache = get_cache_manager()
            cache.set(cache_key, result, "research")  # Uses 7-day TTL
        except Exception as e:
            logger.debug(f"Cache write failed: {e}")
    
    async def _query_knowledge_base(
        self, 
        industry: Optional[str], 
        project_type: Optional[str]
    ) -> Dict[str, Any]:
        """Query KB for existing industry research."""
        try:
            from ..knowledge import query_knowledge, KnowledgeEntryType
            from ..models import get_db
            
            db = next(get_db())
            
            # Query for industry research
            results = await query_knowledge(
                db=db,
                query_text=f"{industry} {project_type} design research trends",
                entry_types=[KnowledgeEntryType.DESIGN_INSPIRATION],
                industry=industry,
                limit=3,
            )
            
            if results:
                return {
                    "industry_research": results[0].entry.content if results else None,
                    "related_entries": [
                        {"title": r.entry.title, "content": r.entry.content[:200]}
                        for r in results
                    ]
                }
            return {}
        except Exception as e:
            logger.debug(f"KB query failed: {e}")
            return {}
    
    async def _write_to_knowledge_base(
        self, 
        research: Dict[str, Any], 
        industry: Optional[str],
        project_type: Optional[str]
    ) -> None:
        """Write research results to KB for future use."""
        try:
            from ..knowledge import store_knowledge, KnowledgeEntryType
            from ..models import get_db
            
            db = next(get_db())
            
            # Store the research findings
            title = f"Research: {industry or 'General'} - {project_type or 'Unknown'}"
            content = json.dumps(research, indent=2)
            
            await store_knowledge(
                db=db,
                entry_type=KnowledgeEntryType.DESIGN_INSPIRATION,
                title=title,
                content=content,
                industry=industry,
                project_type=project_type,
                agent_name=self.name,
                quality_score=0.8,
                tags=["research", "design", industry or "general"],
            )
        except Exception as e:
            logger.debug(f"KB write failed: {e}")
    
    async def _scrape_reference_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape reference URLs via Browser MCP."""
        scraped = []
        try:
            from ..mcp.manager import get_mcp_manager
            
            mcp = get_mcp_manager()
            
            for url in urls[:5]:  # Limit to 5 URLs
                try:
                    result = await mcp.call_tool(
                        server_name="browser",
                        tool_name="scrape_page",
                        arguments={"url": url, "extract": ["title", "description", "colors", "fonts"]}
                    )
                    if result.get("success"):
                        scraped.append({
                            "url": url,
                            "title": result.get("title", ""),
                            "summary": result.get("description", ""),
                            "colors": result.get("colors", []),
                            "fonts": result.get("fonts", []),
                        })
                except Exception as e:
                    logger.debug(f"Failed to scrape {url}: {e}")
                    scraped.append({"url": url, "error": str(e)})
        except Exception as e:
            logger.warning(f"Browser MCP not available: {e}")
        
        return scraped
    
    async def _extract_figma_tokens(self, figma_url: str) -> Optional[Dict[str, Any]]:
        """Extract design tokens from Figma via Figma MCP."""
        try:
            from ..mcp.manager import get_mcp_manager
            
            mcp = get_mcp_manager()
            
            result = await mcp.call_tool(
                server_name="figma",
                tool_name="extract_design_tokens",
                arguments={"file_url": figma_url}
            )
            
            if result.get("success"):
                return {
                    "colors": result.get("colors", {}),
                    "typography": result.get("typography", {}),
                    "spacing": result.get("spacing", {}),
                    "effects": result.get("effects", {}),
                    "components": result.get("components", []),
                }
            return None
        except Exception as e:
            logger.warning(f"Figma MCP extraction failed: {e}")
            return None
    
    def _select_model(self, cost_profile: str) -> str:
        """Select model based on cost profile."""
        models = {
            "budget": "deepseek/deepseek-chat",
            "balanced": "anthropic/claude-sonnet-4",
            "premium": "anthropic/claude-opus-4",
        }
        return models.get(cost_profile, "anthropic/claude-sonnet-4")
