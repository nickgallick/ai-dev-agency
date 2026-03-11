"""Automated Browser Testing with Video Evidence (#11)

Backend API routes for running Playwright browser tests against generated apps
and recording video evidence of the app functioning.
"""
import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/browser-tests", tags=["browser-testing"])

# Directory where video recordings and screenshots are stored
EVIDENCE_DIR = Path(os.getenv("EVIDENCE_DIR", "data/browser_evidence"))


# ── Request / Response models ──────────────────────────────────────

class BrowserTestRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL to test (defaults to project live_url)")
    viewport: str = Field("desktop", description="Viewport: desktop, tablet, mobile")
    record_video: bool = Field(True, description="Whether to record video")
    take_screenshots: bool = Field(True, description="Capture screenshots at each step")
    test_interactions: bool = Field(True, description="Test clicks, navigation, forms")
    test_themes: bool = Field(False, description="Test both light and dark themes")
    max_duration_seconds: int = Field(60, ge=10, le=300)


class TestStep(BaseModel):
    step: int
    action: str
    selector: Optional[str] = None
    description: str
    status: str  # passed, failed, skipped
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0


class BrowserTestResult(BaseModel):
    id: str
    project_id: str
    url: str
    viewport: str
    status: str  # passed, failed, error
    started_at: str
    completed_at: str
    duration_ms: int
    steps: List[TestStep]
    video_path: Optional[str] = None
    screenshots: List[str] = []
    console_errors: List[str] = []
    network_errors: List[str] = []
    accessibility_issues: List[Dict[str, Any]] = []
    performance_metrics: Dict[str, Any] = {}
    summary: Dict[str, Any] = {}


class BrowserTestHistory(BaseModel):
    project_id: str
    tests: List[Dict[str, Any]]
    total: int


# ── Viewport presets ───────────────────────────────────────────────

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 720},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 812},
}


# ── Helper: run Playwright test ────────────────────────────────────

async def run_playwright_test(
    url: str,
    project_id: str,
    viewport: str = "desktop",
    record_video: bool = True,
    take_screenshots: bool = True,
    test_interactions: bool = True,
    test_themes: bool = False,
    max_duration: int = 60,
) -> BrowserTestResult:
    """Run automated browser tests with Playwright and capture evidence."""
    test_id = str(uuid.uuid4())
    started_at = datetime.utcnow()
    vp = VIEWPORTS.get(viewport, VIEWPORTS["desktop"])

    # Create evidence directory
    evidence_path = EVIDENCE_DIR / project_id / test_id
    evidence_path.mkdir(parents=True, exist_ok=True)

    steps: List[TestStep] = []
    console_errors: List[str] = []
    network_errors: List[str] = []
    screenshots: List[str] = []
    video_path: Optional[str] = None
    performance_metrics: Dict[str, Any] = {}
    accessibility_issues: List[Dict[str, Any]] = []

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        # Playwright not installed — generate a structured result from LLM analysis
        return _generate_simulated_result(
            test_id, project_id, url, viewport, started_at,
            "Playwright not installed — install with: pip install playwright && playwright install chromium"
        )

    pw = None
    browser = None
    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)

        context_opts: Dict[str, Any] = {
            "viewport": vp,
            "ignore_https_errors": True,
        }
        if record_video:
            context_opts["record_video_dir"] = str(evidence_path / "videos")
            context_opts["record_video_size"] = vp

        context = await browser.new_context(**context_opts)
        page = await context.new_page()

        # Collect console errors
        page.on("console", lambda msg: (
            console_errors.append(f"[{msg.type}] {msg.text}")
            if msg.type in ("error", "warning") else None
        ))

        # Collect network failures
        page.on("requestfailed", lambda req: network_errors.append(
            f"{req.method} {req.url} — {req.failure}"
        ))

        step_num = 0

        # Step 1: Navigate to URL
        step_num += 1
        nav_start = time.time()
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30000)
            status_code = response.status if response else 0
            nav_ok = 200 <= status_code < 400

            steps.append(TestStep(
                step=step_num,
                action="navigate",
                description=f"Navigate to {url} (HTTP {status_code})",
                status="passed" if nav_ok else "failed",
                error=f"HTTP {status_code}" if not nav_ok else None,
                duration_ms=int((time.time() - nav_start) * 1000),
            ))

            if take_screenshots:
                ss_path = str(evidence_path / f"step_{step_num}_navigate.png")
                await page.screenshot(path=ss_path, full_page=True)
                screenshots.append(ss_path)
                steps[-1].screenshot_path = ss_path
        except Exception as e:
            steps.append(TestStep(
                step=step_num, action="navigate",
                description=f"Navigate to {url}",
                status="failed", error=str(e),
                duration_ms=int((time.time() - nav_start) * 1000),
            ))

        # Step 2: Check page title
        step_num += 1
        title = await page.title()
        steps.append(TestStep(
            step=step_num, action="check_title",
            description=f"Page title: '{title}'",
            status="passed" if title else "failed",
            error="Empty page title" if not title else None,
        ))

        # Step 3: Check for visible content
        step_num += 1
        body_text = await page.inner_text("body")
        has_content = len(body_text.strip()) > 50
        steps.append(TestStep(
            step=step_num, action="check_content",
            description=f"Page has visible content ({len(body_text)} chars)",
            status="passed" if has_content else "failed",
            error="Page appears empty or has minimal content" if not has_content else None,
        ))

        # Step 4: Check for JS errors already captured
        step_num += 1
        js_errors = [e for e in console_errors if "[error]" in e.lower()]
        steps.append(TestStep(
            step=step_num, action="check_console",
            description=f"Console errors: {len(js_errors)}",
            status="passed" if len(js_errors) == 0 else "failed",
            error="; ".join(js_errors[:3]) if js_errors else None,
        ))

        # Step 5: Check responsive layout (no horizontal overflow)
        step_num += 1
        scroll_width = await page.evaluate("document.documentElement.scrollWidth")
        viewport_width = vp["width"]
        has_overflow = scroll_width > viewport_width + 10
        steps.append(TestStep(
            step=step_num, action="check_layout",
            description=f"Layout check — scroll width {scroll_width}px vs viewport {viewport_width}px",
            status="passed" if not has_overflow else "failed",
            error=f"Horizontal overflow: {scroll_width}px > {viewport_width}px" if has_overflow else None,
        ))

        # Step 6: Test interactive elements
        if test_interactions:
            step_num += 1
            t_start = time.time()
            links = await page.query_selector_all("a[href]")
            buttons = await page.query_selector_all("button")
            inputs = await page.query_selector_all("input, textarea, select")
            steps.append(TestStep(
                step=step_num, action="discover_elements",
                description=f"Found {len(links)} links, {len(buttons)} buttons, {len(inputs)} inputs",
                status="passed",
                duration_ms=int((time.time() - t_start) * 1000),
            ))

            # Click first visible button
            if buttons:
                step_num += 1
                t_start = time.time()
                try:
                    btn = buttons[0]
                    btn_text = await btn.inner_text()
                    is_visible = await btn.is_visible()
                    if is_visible:
                        await btn.click(timeout=5000)
                        await page.wait_for_timeout(500)
                        steps.append(TestStep(
                            step=step_num, action="click_button",
                            description=f"Clicked button: '{btn_text[:30]}'",
                            status="passed",
                            duration_ms=int((time.time() - t_start) * 1000),
                        ))
                        if take_screenshots:
                            ss_path = str(evidence_path / f"step_{step_num}_click.png")
                            await page.screenshot(path=ss_path)
                            screenshots.append(ss_path)
                            steps[-1].screenshot_path = ss_path
                    else:
                        steps.append(TestStep(
                            step=step_num, action="click_button",
                            description=f"Button '{btn_text[:30]}' not visible, skipped",
                            status="skipped",
                        ))
                except Exception as e:
                    steps.append(TestStep(
                        step=step_num, action="click_button",
                        description="Click first button",
                        status="failed", error=str(e)[:200],
                        duration_ms=int((time.time() - t_start) * 1000),
                    ))

            # Navigate internal link
            if links:
                step_num += 1
                t_start = time.time()
                try:
                    for link in links[:5]:
                        href = await link.get_attribute("href")
                        if href and not href.startswith("http") and not href.startswith("#"):
                            is_visible = await link.is_visible()
                            if is_visible:
                                await link.click(timeout=5000)
                                await page.wait_for_load_state("networkidle", timeout=10000)
                                steps.append(TestStep(
                                    step=step_num, action="navigate_link",
                                    description=f"Navigated to internal link: {href}",
                                    status="passed",
                                    duration_ms=int((time.time() - t_start) * 1000),
                                ))
                                if take_screenshots:
                                    ss_path = str(evidence_path / f"step_{step_num}_nav.png")
                                    await page.screenshot(path=ss_path)
                                    screenshots.append(ss_path)
                                    steps[-1].screenshot_path = ss_path
                                break
                    else:
                        steps.append(TestStep(
                            step=step_num, action="navigate_link",
                            description="No visible internal links to test",
                            status="skipped",
                        ))
                except Exception as e:
                    steps.append(TestStep(
                        step=step_num, action="navigate_link",
                        description="Navigate internal link",
                        status="failed", error=str(e)[:200],
                        duration_ms=int((time.time() - t_start) * 1000),
                    ))

        # Step: Test dark/light theme toggle
        if test_themes:
            step_num += 1
            t_start = time.time()
            try:
                # Try common theme toggle selectors
                toggle_selectors = [
                    "[data-testid='theme-toggle']",
                    "button[aria-label*='theme']",
                    "button[aria-label*='dark']",
                    "button[aria-label*='mode']",
                    ".theme-toggle",
                    "#theme-toggle",
                ]
                toggled = False
                for selector in toggle_selectors:
                    toggle = await page.query_selector(selector)
                    if toggle and await toggle.is_visible():
                        await toggle.click()
                        await page.wait_for_timeout(500)
                        toggled = True
                        steps.append(TestStep(
                            step=step_num, action="toggle_theme",
                            description=f"Toggled theme via {selector}",
                            status="passed",
                            duration_ms=int((time.time() - t_start) * 1000),
                        ))
                        if take_screenshots:
                            ss_path = str(evidence_path / f"step_{step_num}_theme.png")
                            await page.screenshot(path=ss_path, full_page=True)
                            screenshots.append(ss_path)
                            steps[-1].screenshot_path = ss_path
                        break
                if not toggled:
                    steps.append(TestStep(
                        step=step_num, action="toggle_theme",
                        description="No theme toggle found",
                        status="skipped",
                    ))
            except Exception as e:
                steps.append(TestStep(
                    step=step_num, action="toggle_theme",
                    description="Toggle theme",
                    status="failed", error=str(e)[:200],
                    duration_ms=int((time.time() - t_start) * 1000),
                ))

        # Capture performance metrics
        try:
            perf = await page.evaluate("""() => {
                const perf = performance.getEntriesByType('navigation')[0];
                return perf ? {
                    dom_content_loaded: Math.round(perf.domContentLoadedEventEnd),
                    load_event: Math.round(perf.loadEventEnd),
                    dom_interactive: Math.round(perf.domInteractive),
                    transfer_size: perf.transferSize || 0,
                } : {}
            }""")
            performance_metrics = perf or {}
        except Exception:
            pass

        # Final full-page screenshot
        if take_screenshots:
            ss_path = str(evidence_path / "final.png")
            await page.screenshot(path=ss_path, full_page=True)
            screenshots.append(ss_path)

        # Close context to finalize video
        await context.close()

        # Find the video file
        videos_dir = evidence_path / "videos"
        if videos_dir.exists():
            video_files = list(videos_dir.glob("*.webm"))
            if video_files:
                video_path = str(video_files[0])

        await browser.close()
        await pw.stop()

    except Exception as e:
        logger.error(f"Browser test failed: {e}")
        if browser:
            await browser.close()
        if pw:
            await pw.stop()
        return _generate_simulated_result(
            test_id, project_id, url, viewport, started_at, str(e)
        )

    # Build result
    completed_at = datetime.utcnow()
    passed_steps = sum(1 for s in steps if s.status == "passed")
    failed_steps = sum(1 for s in steps if s.status == "failed")
    total_steps = len(steps)

    overall_status = "passed" if failed_steps == 0 else "failed"

    return BrowserTestResult(
        id=test_id,
        project_id=project_id,
        url=url,
        viewport=viewport,
        status=overall_status,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        steps=steps,
        video_path=video_path,
        screenshots=screenshots,
        console_errors=console_errors,
        network_errors=network_errors,
        accessibility_issues=accessibility_issues,
        performance_metrics=performance_metrics,
        summary={
            "total_steps": total_steps,
            "passed": passed_steps,
            "failed": failed_steps,
            "skipped": total_steps - passed_steps - failed_steps,
            "has_video": video_path is not None,
            "screenshot_count": len(screenshots),
            "console_error_count": len(console_errors),
            "network_error_count": len(network_errors),
        },
    )


def _generate_simulated_result(
    test_id: str,
    project_id: str,
    url: str,
    viewport: str,
    started_at: datetime,
    error_message: str,
) -> BrowserTestResult:
    """Generate a result when Playwright isn't available."""
    completed_at = datetime.utcnow()
    return BrowserTestResult(
        id=test_id,
        project_id=project_id,
        url=url,
        viewport=viewport,
        status="error",
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        steps=[
            TestStep(
                step=1,
                action="setup",
                description="Initialize browser testing environment",
                status="failed",
                error=error_message,
            )
        ],
        summary={
            "total_steps": 1,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "has_video": False,
            "screenshot_count": 0,
            "error": error_message,
        },
    )


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("", response_model=BrowserTestResult)
async def run_browser_test(
    project_id: str,
    body: BrowserTestRequest,
    db: Session = Depends(get_db),
):
    """Run automated browser tests with video recording against a project's live URL."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Determine URL to test
    url = body.url
    if not url:
        url = project.live_url
    if not url:
        # Try agent_outputs for deployment URL
        outputs = project.agent_outputs or {}
        deploy_out = outputs.get("deployment", {})
        url = deploy_out.get("url") or deploy_out.get("live_url")
    if not url:
        raise HTTPException(status_code=400, detail="No URL available to test. Deploy the project first or provide a URL.")

    result = await run_playwright_test(
        url=url,
        project_id=project_id,
        viewport=body.viewport,
        record_video=body.record_video,
        take_screenshots=body.take_screenshots,
        test_interactions=body.test_interactions,
        test_themes=body.test_themes,
        max_duration=body.max_duration_seconds,
    )

    # Store result in project agent_outputs
    outputs = dict(project.agent_outputs or {})
    browser_tests = outputs.get("browser_tests", [])
    if not isinstance(browser_tests, list):
        browser_tests = []
    browser_tests.append(result.dict())
    # Keep last 10 test runs
    outputs["browser_tests"] = browser_tests[-10:]
    project.agent_outputs = outputs
    db.commit()

    return result


@router.get("", response_model=BrowserTestHistory)
async def get_browser_test_history(
    project_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get browser test history for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    outputs = project.agent_outputs or {}
    browser_tests = outputs.get("browser_tests", [])
    if not isinstance(browser_tests, list):
        browser_tests = []

    # Return most recent first
    tests = list(reversed(browser_tests[-limit:]))

    return BrowserTestHistory(
        project_id=project_id,
        tests=tests,
        total=len(browser_tests),
    )


@router.get("/evidence/{test_id}/{filename}")
async def get_test_evidence(
    project_id: str,
    test_id: str,
    filename: str,
):
    """Serve screenshot or video evidence files."""
    from fastapi.responses import FileResponse

    # Sanitize inputs
    if ".." in test_id or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")

    evidence_path = EVIDENCE_DIR / project_id / test_id
    file_path = evidence_path / filename

    # Also check videos subdirectory
    if not file_path.exists():
        file_path = evidence_path / "videos" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Evidence file not found")

    media_type = "image/png" if filename.endswith(".png") else "video/webm"
    return FileResponse(str(file_path), media_type=media_type)
