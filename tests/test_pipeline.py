"""
Tests for AI Dev Agency Pipeline - Phase 2
Tests parallel execution of Asset and Content generation agents.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.schemas import ProjectBrief, ProjectType
from backend.agents.design_system import DesignSystemAgent
from backend.agents.asset_generation import AssetGenerationAgent
from backend.agents.content_generation import ContentGenerationAgent
from backend.orchestration.pipeline import AgentPipeline, PipelineConfig


def test_project_brief_creation():
    """Test creating a project brief."""
    brief = ProjectBrief(
        name="Test Project",
        description="A test web application for unit testing",
        project_type=ProjectType.WEB_SIMPLE,
        target_audience="Developers",
        tone="professional",
        primary_color="#3B82F6",
        industry="Technology",
        features=["Authentication", "Dashboard"]
    )
    
    assert brief.name == "Test Project"
    assert brief.project_type == ProjectType.WEB_SIMPLE
    print("✓ Project brief creation works")


async def test_design_system_agent_fallback():
    """Test Design System Agent with fallback (no API key)."""
    agent = DesignSystemAgent(llm_client=None)
    
    brief = ProjectBrief(
        name="Fallback Test",
        description="Testing fallback design system",
        project_type=ProjectType.WEB_SIMPLE,
        primary_color="#FF5733"
    )
    
    design_system = agent.get_default_design_system(brief)
    
    assert design_system.colors["primary"] == "#FF5733"
    assert "typography" in design_system.model_dump()
    assert "spacing" in design_system.model_dump()
    print("✓ Design System fallback works")


async def test_asset_generation_fallback():
    """Test Asset Generation Agent with fallback (no API key)."""
    from backend.models.schemas import DesignSystemOutput
    
    agent = AssetGenerationAgent(
        stability_client=None,
        llm_client=None,
        output_dir="/tmp/test_assets"
    )
    
    brief = ProjectBrief(
        name="Asset Test",
        description="Testing asset generation",
        project_type=ProjectType.WEB_SIMPLE,
        primary_color="#3B82F6"
    )
    
    design_system = DesignSystemOutput(
        colors={"primary": "#3B82F6", "secondary": "#6366F1", "accent": "#F59E0B",
                "background": "#FFFFFF", "surface": "#F3F4F6", "text": "#111827",
                "text_muted": "#6B7280", "error": "#EF4444", "success": "#10B981",
                "warning": "#F59E0B"},
        typography={"font_family": "Inter"},
        spacing={"xs": "0.25rem", "sm": "0.5rem", "md": "1rem", "lg": "1.5rem", 
                 "xl": "2rem", "2xl": "3rem"},
        border_radius={"none": "0", "sm": "0.25rem", "md": "0.5rem", "lg": "1rem", 
                       "full": "9999px"},
        shadows={"sm": "0 1px 2px", "md": "0 4px 6px", "lg": "0 10px 15px", 
                 "xl": "0 25px 50px"},
        components={}
    )
    
    result = await agent.generate(brief, design_system, "test-project-123")
    
    assert result.agent_name == "asset_generation"
    assert result.output is not None
    print(f"✓ Asset Generation fallback works - generated {len(result.output.get('all_assets', []))} assets")


async def test_content_generation_fallback():
    """Test Content Generation Agent with fallback."""
    from backend.models.schemas import DesignSystemOutput
    
    agent = ContentGenerationAgent(llm_client=None)
    
    brief = ProjectBrief(
        name="Content Test",
        description="Testing content generation",
        project_type=ProjectType.WEB_SIMPLE,
        tone="professional"
    )
    
    design_system = DesignSystemOutput(
        colors={"primary": "#3B82F6"},
        typography={},
        spacing={},
        border_radius={},
        shadows={},
        components={}
    )
    
    # Test fallback content generation
    fallback_content = agent._get_fallback_content(brief, "home")
    
    assert fallback_content.page_name == "home"
    assert "Content Test" in fallback_content.headline
    print("✓ Content Generation fallback works")


async def test_pipeline_progress_tracking():
    """Test pipeline progress callback."""
    progress_updates = []
    
    def progress_callback(step, progress, data):
        progress_updates.append({
            "step": step,
            "progress": progress,
            "data": data
        })
    
    config = PipelineConfig(
        enable_asset_generation=True,
        enable_content_generation=True,
        parallel_execution=True,
        output_dir="/tmp/test_pipeline"
    )
    
    pipeline = AgentPipeline(config=config, progress_callback=progress_callback)
    
    brief = ProjectBrief(
        name="Pipeline Test",
        description="Testing pipeline progress",
        project_type=ProjectType.WEB_SIMPLE
    )
    
    result = await pipeline.run(brief)
    
    assert len(progress_updates) > 0
    assert any(u["step"] == "initializing" for u in progress_updates)
    assert any(u["step"] == "design_system" for u in progress_updates)
    print(f"✓ Pipeline progress tracking works - {len(progress_updates)} updates")


async def test_parallel_execution():
    """Test that Asset and Content agents can run in parallel."""
    from backend.models.schemas import DesignSystemOutput
    import time
    
    brief = ProjectBrief(
        name="Parallel Test",
        description="Testing parallel execution",
        project_type=ProjectType.WEB_SIMPLE
    )
    
    design_system = DesignSystemOutput(
        colors={"primary": "#3B82F6", "secondary": "#6366F1", "accent": "#F59E0B",
                "background": "#FFFFFF", "surface": "#F3F4F6", "text": "#111827"},
        typography={},
        spacing={"xs": "0.25rem", "sm": "0.5rem", "md": "1rem", "lg": "1.5rem"},
        border_radius={},
        shadows={},
        components={}
    )
    
    asset_agent = AssetGenerationAgent(output_dir="/tmp/parallel_test")
    content_agent = ContentGenerationAgent()
    
    start_time = time.time()
    
    # Run in parallel
    results = await asyncio.gather(
        asset_agent.generate(brief, design_system, "parallel-test"),
        content_agent.generate(brief, design_system, "parallel-test"),
        return_exceptions=True
    )
    
    parallel_time = time.time() - start_time
    
    # Both should complete
    assert len(results) == 2
    assert all(not isinstance(r, Exception) for r in results)
    
    print(f"✓ Parallel execution works - completed in {parallel_time:.2f}s")


async def test_web_simple_project():
    """Test complete pipeline for web_simple project type."""
    config = PipelineConfig(
        enable_asset_generation=True,
        enable_content_generation=True,
        parallel_execution=True,
        output_dir="/tmp/web_simple_test"
    )
    
    pipeline = AgentPipeline(config=config)
    
    brief = ProjectBrief(
        name="Simple Website",
        description="A simple business website for a consulting firm",
        project_type=ProjectType.WEB_SIMPLE,
        target_audience="Business professionals",
        tone="professional",
        primary_color="#1E40AF",
        industry="Consulting",
        features=["Contact form", "Services overview"]
    )
    
    result = await pipeline.run(brief)
    
    assert result.current_step == "completed"
    assert result.design_system is not None
    
    # Check assets
    if result.asset_urls:
        assert len(result.asset_urls.favicons) >= 3
        assert len(result.asset_urls.app_icons) >= 2
        assert len(result.asset_urls.og_images) >= 1
    
    # Check content
    if result.content_data:
        page_names = [p.page_name for p in result.content_data.pages]
        assert "home" in page_names
        assert "about" in page_names
        assert "contact" in page_names
    
    print("✓ web_simple project pipeline works")
    return result


async def test_web_complex_project():
    """Test complete pipeline for web_complex project type."""
    config = PipelineConfig(
        enable_asset_generation=True,
        enable_content_generation=True,
        parallel_execution=True,
        output_dir="/tmp/web_complex_test"
    )
    
    pipeline = AgentPipeline(config=config)
    
    brief = ProjectBrief(
        name="SaaS Platform",
        description="A comprehensive SaaS platform for project management",
        project_type=ProjectType.WEB_COMPLEX,
        target_audience="Product managers and teams",
        tone="professional",
        primary_color="#7C3AED",
        industry="Software",
        features=["Project tracking", "Team collaboration", "Analytics dashboard"]
    )
    
    result = await pipeline.run(brief)
    
    assert result.current_step == "completed"
    assert result.design_system is not None
    
    # Check content has more pages for complex project
    if result.content_data:
        page_names = [p.page_name for p in result.content_data.pages]
        assert len(page_names) >= 4  # Should have more pages than simple
        assert "features" in page_names or "pricing" in page_names
    
    print("✓ web_complex project pipeline works")
    return result


async def test_error_handling():
    """Test pipeline handles errors gracefully."""
    config = PipelineConfig(
        enable_asset_generation=True,
        enable_content_generation=True,
        parallel_execution=True,
        output_dir="/tmp/error_test"
    )
    
    pipeline = AgentPipeline(config=config)
    
    brief = ProjectBrief(
        name="Error Test",
        description="Testing error handling",
        project_type=ProjectType.WEB_SIMPLE
    )
    
    # This should complete even with fallbacks
    result = await pipeline.run(brief)
    
    # Pipeline should complete even if agents use fallbacks
    assert result.current_step == "completed"
    assert result.progress == 1.0
    
    print("✓ Error handling works - pipeline completed with fallbacks")


def run_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("AI Dev Agency - Phase 2 Tests")
    print("="*60 + "\n")
    
    # Sync tests
    test_project_brief_creation()
    
    # Async tests
    asyncio.run(test_design_system_agent_fallback())
    asyncio.run(test_asset_generation_fallback())
    asyncio.run(test_content_generation_fallback())
    asyncio.run(test_pipeline_progress_tracking())
    asyncio.run(test_parallel_execution())
    asyncio.run(test_web_simple_project())
    asyncio.run(test_web_complex_project())
    asyncio.run(test_error_handling())
    
    print("\n" + "="*60)
    print("All tests passed! ✓")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_tests()
