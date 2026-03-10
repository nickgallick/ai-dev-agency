"""
Asset Generation Agent - Phase 2
Generates visual assets using DALL-E or Stable Diffusion API.
- Favicons (16x16, 32x32, 180x180)
- App icons (512x512, 1024x1024)
- Open Graph images (1200x630)
- Placeholder images for content sections
- SVG illustrations matching design system
"""
import os
import io
import base64
import asyncio
import httpx
from PIL import Image
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from ..models.schemas import (
    ProjectBrief, DesignSystemOutput, AssetGenerationOutput, 
    AssetMetadata, AgentOutput, AgentStatus
)
from ..utils.llm_client import StabilityAIClient, OpenRouterClient


class AssetGenerationAgent:
    """Agent responsible for generating visual assets for the project."""
    
    def __init__(
        self, 
        stability_client: Optional[StabilityAIClient] = None,
        llm_client: Optional[OpenRouterClient] = None,
        output_dir: str = "/home/ubuntu/ai-dev-agency/generated_assets"
    ):
        self.stability_client = stability_client
        self.llm_client = llm_client
        self.output_dir = Path(output_dir)
        self.name = "asset_generation"
        
    def _ensure_clients(self):
        """Initialize clients lazily to allow for missing API keys during import."""
        if self.stability_client is None:
            try:
                self.stability_client = StabilityAIClient()
            except ValueError:
                pass  # API key not set, will use fallback
        if self.llm_client is None:
            try:
                self.llm_client = OpenRouterClient()
            except ValueError:
                pass
    
    async def generate(
        self, 
        project_brief: ProjectBrief, 
        design_system: DesignSystemOutput,
        project_id: str
    ) -> AgentOutput:
        """Generate all visual assets for the project."""
        started_at = datetime.utcnow()
        self._ensure_clients()
        
        try:
            # Create project-specific output directory
            project_dir = self.output_dir / project_id
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate all assets in parallel
            results = await asyncio.gather(
                self._generate_favicons(project_brief, design_system, project_dir),
                self._generate_app_icons(project_brief, design_system, project_dir),
                self._generate_og_images(project_brief, design_system, project_dir),
                self._generate_placeholders(project_brief, design_system, project_dir),
                self._generate_svg_illustrations(project_brief, design_system, project_dir),
                return_exceptions=True
            )
            
            # Collect results
            favicons, app_icons, og_images, placeholders, svg_illustrations = results
            
            # Handle any exceptions
            errors = []
            if isinstance(favicons, Exception):
                errors.append(f"Favicons: {str(favicons)}")
                favicons = []
            if isinstance(app_icons, Exception):
                errors.append(f"App Icons: {str(app_icons)}")
                app_icons = []
            if isinstance(og_images, Exception):
                errors.append(f"OG Images: {str(og_images)}")
                og_images = []
            if isinstance(placeholders, Exception):
                errors.append(f"Placeholders: {str(placeholders)}")
                placeholders = []
            if isinstance(svg_illustrations, Exception):
                errors.append(f"SVG Illustrations: {str(svg_illustrations)}")
                svg_illustrations = []
            
            all_assets = favicons + app_icons + og_images + placeholders + svg_illustrations
            
            output = AssetGenerationOutput(
                favicons=favicons,
                app_icons=app_icons,
                og_images=og_images,
                placeholder_images=placeholders,
                svg_illustrations=svg_illustrations,
                all_assets=all_assets
            )
            
            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED if not errors else AgentStatus.COMPLETED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                output=output.model_dump(),
                error="; ".join(errors) if errors else None
            )
            
        except Exception as e:
            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e)
            )
    
    async def _generate_favicons(
        self, 
        brief: ProjectBrief, 
        design_system: DesignSystemOutput,
        output_dir: Path
    ) -> List[AssetMetadata]:
        """Generate favicons in multiple sizes."""
        sizes = [(16, 16), (32, 32), (180, 180)]
        favicons = []
        
        # Generate base icon at highest resolution
        base_image = await self._generate_icon_image(brief, design_system, 512)
        
        for width, height in sizes:
            filename = f"favicon-{width}x{height}.png"
            filepath = output_dir / filename
            
            # Resize the base image
            if base_image:
                resized = base_image.resize((width, height), Image.Resampling.LANCZOS)
                resized.save(filepath, "PNG")
            else:
                # Create a fallback solid color favicon
                self._create_fallback_icon(filepath, width, height, design_system.colors.get("primary", "#3B82F6"))
            
            favicons.append(AssetMetadata(
                filename=filename,
                size=f"{width}x{height}",
                format="png",
                purpose="favicon",
                local_path=str(filepath),
                url=f"/assets/{brief.name}/{filename}"
            ))
        
        return favicons
    
    async def _generate_app_icons(
        self, 
        brief: ProjectBrief, 
        design_system: DesignSystemOutput,
        output_dir: Path
    ) -> List[AssetMetadata]:
        """Generate app icons (512x512, 1024x1024)."""
        sizes = [(512, 512), (1024, 1024)]
        app_icons = []
        
        # Generate base icon
        base_image = await self._generate_icon_image(brief, design_system, 1024)
        
        for width, height in sizes:
            filename = f"app-icon-{width}x{height}.png"
            filepath = output_dir / filename
            
            if base_image:
                if width == 1024:
                    base_image.save(filepath, "PNG")
                else:
                    resized = base_image.resize((width, height), Image.Resampling.LANCZOS)
                    resized.save(filepath, "PNG")
            else:
                self._create_fallback_icon(filepath, width, height, design_system.colors.get("primary", "#3B82F6"))
            
            app_icons.append(AssetMetadata(
                filename=filename,
                size=f"{width}x{height}",
                format="png",
                purpose="app_icon",
                local_path=str(filepath),
                url=f"/assets/{brief.name}/{filename}"
            ))
        
        return app_icons
    
    async def _generate_og_images(
        self, 
        brief: ProjectBrief, 
        design_system: DesignSystemOutput,
        output_dir: Path
    ) -> List[AssetMetadata]:
        """Generate Open Graph images (1200x630)."""
        og_images = []
        
        prompt = self._build_og_image_prompt(brief, design_system)
        
        try:
            if self.stability_client:
                image_data = await self.stability_client.generate_image(
                    prompt=prompt,
                    width=1024,  # Stability AI supported size
                    height=576,  # Close to 1200x630 aspect ratio
                    style_preset="digital-art"
                )
                
                # Load and resize to exact OG dimensions
                image = Image.open(io.BytesIO(image_data))
                image = image.resize((1200, 630), Image.Resampling.LANCZOS)
            else:
                image = self._create_fallback_og_image(brief, design_system)
        except Exception as e:
            print(f"OG image generation error: {e}")
            image = self._create_fallback_og_image(brief, design_system)
        
        filename = "og-image.png"
        filepath = output_dir / filename
        image.save(filepath, "PNG")
        
        og_images.append(AssetMetadata(
            filename=filename,
            size="1200x630",
            format="png",
            purpose="og_image",
            local_path=str(filepath),
            url=f"/assets/{brief.name}/{filename}"
        ))
        
        return og_images
    
    async def _generate_placeholders(
        self, 
        brief: ProjectBrief, 
        design_system: DesignSystemOutput,
        output_dir: Path
    ) -> List[AssetMetadata]:
        """Generate placeholder images for content sections."""
        placeholders = []
        placeholder_configs = [
            ("hero", 1920, 1080, "Hero section background"),
            ("feature-1", 800, 600, "Feature illustration 1"),
            ("feature-2", 800, 600, "Feature illustration 2"),
            ("feature-3", 800, 600, "Feature illustration 3"),
            ("about", 1200, 800, "About section image"),
            ("testimonial", 400, 400, "Testimonial avatar placeholder"),
        ]
        
        for name, width, height, description in placeholder_configs:
            filename = f"placeholder-{name}.png"
            filepath = output_dir / filename
            
            try:
                if self.stability_client and width <= 1024 and height <= 1024:
                    prompt = f"{description} for {brief.name}, {brief.description}. Modern, professional, {brief.tone} style. Primary color: {design_system.colors.get('primary', '#3B82F6')}"
                    
                    image_data = await self.stability_client.generate_image(
                        prompt=prompt,
                        width=min(width, 1024),
                        height=min(height, 1024),
                        style_preset="digital-art"
                    )
                    image = Image.open(io.BytesIO(image_data))
                    if (width, height) != image.size:
                        image = image.resize((width, height), Image.Resampling.LANCZOS)
                else:
                    image = self._create_gradient_placeholder(width, height, design_system)
            except Exception as e:
                print(f"Placeholder generation error for {name}: {e}")
                image = self._create_gradient_placeholder(width, height, design_system)
            
            image.save(filepath, "PNG")
            
            placeholders.append(AssetMetadata(
                filename=filename,
                size=f"{width}x{height}",
                format="png",
                purpose=f"placeholder_{name}",
                local_path=str(filepath),
                url=f"/assets/{brief.name}/{filename}"
            ))
        
        return placeholders
    
    async def _generate_svg_illustrations(
        self, 
        brief: ProjectBrief, 
        design_system: DesignSystemOutput,
        output_dir: Path
    ) -> List[AssetMetadata]:
        """Generate SVG illustrations matching the design system."""
        illustrations = []
        
        svg_configs = [
            ("logo", "Logo/brand mark"),
            ("icon-feature-1", "Abstract icon for feature 1"),
            ("icon-feature-2", "Abstract icon for feature 2"),
            ("icon-feature-3", "Abstract icon for feature 3"),
            ("decoration-1", "Decorative element"),
        ]
        
        primary_color = design_system.colors.get("primary", "#3B82F6")
        secondary_color = design_system.colors.get("secondary", "#6366F1")
        accent_color = design_system.colors.get("accent", "#F59E0B")
        
        for name, description in svg_configs:
            filename = f"{name}.svg"
            filepath = output_dir / filename
            
            # Generate SVG using LLM or use template
            svg_content = await self._generate_svg_with_llm(
                name, description, brief, primary_color, secondary_color, accent_color
            )
            
            with open(filepath, "w") as f:
                f.write(svg_content)
            
            illustrations.append(AssetMetadata(
                filename=filename,
                size="scalable",
                format="svg",
                purpose=f"illustration_{name}",
                local_path=str(filepath),
                url=f"/assets/{brief.name}/{filename}"
            ))
        
        return illustrations
    
    async def _generate_icon_image(
        self, 
        brief: ProjectBrief, 
        design_system: DesignSystemOutput,
        size: int
    ) -> Optional[Image.Image]:
        """Generate a base icon image using Stability AI."""
        if not self.stability_client:
            return None
        
        prompt = f"""App icon for "{brief.name}". 
{brief.description}. 
Simple, modern, minimalist design. 
Single centered symbol or letter.
Primary color: {design_system.colors.get('primary', '#3B82F6')}.
Clean background, professional app icon style.
No text, no complex details."""
        
        try:
            image_data = await self.stability_client.generate_image(
                prompt=prompt,
                width=min(size, 1024),
                height=min(size, 1024),
                style_preset="digital-art"
            )
            return Image.open(io.BytesIO(image_data))
        except Exception as e:
            print(f"Icon generation error: {e}")
            return None
    
    def _create_fallback_icon(self, filepath: Path, width: int, height: int, color: str):
        """Create a simple fallback icon with the primary color."""
        from PIL import ImageDraw
        
        # Parse hex color
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        
        image = Image.new("RGB", (width, height), rgb)
        draw = ImageDraw.Draw(image)
        
        # Add a subtle inner shadow/border
        border_color = tuple(max(0, c - 30) for c in rgb)
        draw.rectangle([0, 0, width-1, height-1], outline=border_color, width=max(1, width//16))
        
        image.save(filepath, "PNG")
    
    def _create_fallback_og_image(
        self, 
        brief: ProjectBrief, 
        design_system: DesignSystemOutput
    ) -> Image.Image:
        """Create a fallback OG image with gradient background."""
        from PIL import ImageDraw, ImageFont
        
        width, height = 1200, 630
        
        # Parse colors
        primary = design_system.colors.get("primary", "#3B82F6").lstrip('#')
        secondary = design_system.colors.get("secondary", "#6366F1").lstrip('#')
        
        primary_rgb = tuple(int(primary[i:i+2], 16) for i in (0, 2, 4))
        secondary_rgb = tuple(int(secondary[i:i+2], 16) for i in (0, 2, 4))
        
        # Create gradient
        image = Image.new("RGB", (width, height))
        for x in range(width):
            ratio = x / width
            r = int(primary_rgb[0] * (1 - ratio) + secondary_rgb[0] * ratio)
            g = int(primary_rgb[1] * (1 - ratio) + secondary_rgb[1] * ratio)
            b = int(primary_rgb[2] * (1 - ratio) + secondary_rgb[2] * ratio)
            for y in range(height):
                image.putpixel((x, y), (r, g, b))
        
        # Add project name text
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except:
            font = ImageFont.load_default()
            small_font = font
        
        # Center text
        text = brief.name
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2 - 30
        
        draw.text((x, y), text, fill="white", font=font)
        
        # Add description
        desc_bbox = draw.textbbox((0, 0), brief.description[:60], font=small_font)
        desc_width = desc_bbox[2] - desc_bbox[0]
        draw.text(
            ((width - desc_width) // 2, y + text_height + 20), 
            brief.description[:60] + ("..." if len(brief.description) > 60 else ""),
            fill=(255, 255, 255), 
            font=small_font
        )
        
        return image
    
    def _create_gradient_placeholder(
        self, 
        width: int, 
        height: int, 
        design_system: DesignSystemOutput
    ) -> Image.Image:
        """Create a gradient placeholder image."""
        primary = design_system.colors.get("primary", "#3B82F6").lstrip('#')
        surface = design_system.colors.get("surface", "#F3F4F6").lstrip('#')
        
        primary_rgb = tuple(int(primary[i:i+2], 16) for i in (0, 2, 4))
        surface_rgb = tuple(int(surface[i:i+2], 16) for i in (0, 2, 4))
        
        image = Image.new("RGB", (width, height))
        for y in range(height):
            ratio = y / height
            r = int(surface_rgb[0] * (1 - ratio) + primary_rgb[0] * ratio * 0.3)
            g = int(surface_rgb[1] * (1 - ratio) + primary_rgb[1] * ratio * 0.3)
            b = int(surface_rgb[2] * (1 - ratio) + primary_rgb[2] * ratio * 0.3)
            for x in range(width):
                image.putpixel((x, y), (r, g, b))
        
        return image
    
    def _build_og_image_prompt(
        self, 
        brief: ProjectBrief, 
        design_system: DesignSystemOutput
    ) -> str:
        """Build a prompt for OG image generation."""
        return f"""Professional marketing banner for "{brief.name}".
{brief.description}.
Modern, clean design with abstract geometric shapes.
Primary color: {design_system.colors.get('primary', '#3B82F6')}.
Secondary color: {design_system.colors.get('secondary', '#6366F1')}.
{brief.tone} tone, {brief.industry or 'technology'} industry.
No text, abstract professional background."""
    
    async def _generate_svg_with_llm(
        self,
        name: str,
        description: str,
        brief: ProjectBrief,
        primary_color: str,
        secondary_color: str,
        accent_color: str
    ) -> str:
        """Generate SVG using LLM or return template."""
        if self.llm_client:
            try:
                prompt = f"""Create a simple, clean SVG illustration for: {description}
Project: {brief.name} - {brief.description}
Use these colors: primary={primary_color}, secondary={secondary_color}, accent={accent_color}

Requirements:
- ViewBox should be "0 0 100 100"
- Keep it simple and minimalist
- Use only the provided colors
- Return ONLY the SVG code, nothing else

Return a complete, valid SVG element."""

                response = await self.llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are an SVG designer. Return only valid SVG code."},
                        {"role": "user", "content": prompt}
                    ],
                    model="anthropic/claude-3.5-sonnet",
                    max_tokens=1000
                )
                
                svg_content = response["choices"][0]["message"]["content"]
                # Extract SVG if wrapped in markdown
                if "```" in svg_content:
                    svg_content = svg_content.split("```")[1]
                    if svg_content.startswith("svg"):
                        svg_content = svg_content[3:]
                    elif svg_content.startswith("xml"):
                        svg_content = svg_content[3:]
                
                svg_content = svg_content.strip()
                if svg_content.startswith("<svg"):
                    return svg_content
            except Exception as e:
                print(f"SVG generation error: {e}")
        
        # Fallback SVG templates
        return self._get_fallback_svg(name, primary_color, secondary_color, accent_color)
    
    def _get_fallback_svg(
        self, 
        name: str, 
        primary: str, 
        secondary: str, 
        accent: str
    ) -> str:
        """Return fallback SVG templates."""
        templates = {
            "logo": f'''<svg viewBox="0 0 100 100" xmlns="https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Urantia_three-concentric-blue-circles-on-white_symbol.svg/960px-Urantia_three-concentric-blue-circles-on-white_symbol.svg.png">
  <circle cx="50" cy="50" r="40" fill="{primary}"/>
  <circle cx="50" cy="50" r="25" fill="{secondary}" opacity="0.8"/>
  <circle cx="50" cy="50" r="10" fill="white"/>
</svg>''',
            "icon-feature-1": f'''<svg viewBox="0 0 100 100" xmlns="https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Circle-icons-check.svg/960px-Circle-icons-check.svg.png">
  <rect x="20" y="20" width="60" height="60" rx="10" fill="{primary}"/>
  <path d="M35 50 L45 60 L65 40" stroke="white" stroke-width="6" fill="none" stroke-linecap="round"/>
</svg>''',
            "icon-feature-2": f'''<svg viewBox="0 0 100 100" xmlns="https://www.shareicon.net/data/2016/05/07/761206_triangle_512x512.png">
  <polygon points="50,15 85,85 15,85" fill="{secondary}"/>
  <circle cx="50" cy="55" r="15" fill="white"/>
</svg>''',
            "icon-feature-3": f'''<svg viewBox="0 0 100 100" xmlns="https://static.vecteezy.com/system/resources/thumbnails/021/574/060/small/geometric-icon-of-triangle-and-circle-blue-triangle-and-circle-with-outline-illustration-of-geometric-for-graphic-resource-simple-shape-of-geometry-for-design-element-decoration-sign-or-symbol-free-vector.jpg">
  <rect x="15" y="30" width="70" height="40" rx="5" fill="{accent}"/>
  <circle cx="35" cy="50" r="10" fill="white"/>
  <rect x="50" y="42" width="25" height="4" fill="white"/>
  <rect x="50" y="52" width="18" height="4" fill="white"/>
</svg>''',
            "decoration-1": f'''<svg viewBox="0 0 100 100" xmlns="https://images.unsplash.com/vector-1748935415614-8e0b0d590d67?ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1yZWxhdGVkfDMyfHx8ZW58MHx8fHx8&fm=jpg&q=60&w=3000">
  <circle cx="25" cy="25" r="20" fill="{primary}" opacity="0.3"/>
  <circle cx="75" cy="75" r="25" fill="{secondary}" opacity="0.3"/>
  <circle cx="70" cy="30" r="15" fill="{accent}" opacity="0.3"/>
</svg>'''
        }
        
        return templates.get(name, templates["logo"])
