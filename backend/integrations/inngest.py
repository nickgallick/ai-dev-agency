"""Inngest Background Jobs Integration Helpers.

Generates Inngest background job integration code for SaaS projects.
Used by: Code Generation Agent (for python_saas, web_complex with async tasks)

Generates:
- Inngest client setup
- Background job functions
- Event types
- Environment variables
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class BackgroundJob:
    """Background job definition."""
    name: str
    event_name: str
    description: str
    retry_count: int = 3
    timeout: str = "5m"


# Common background jobs for SaaS projects
COMMON_JOBS: List[BackgroundJob] = [
    BackgroundJob(
        name="sendWelcomeEmail",
        event_name="user/created",
        description="Send welcome email to new users",
    ),
    BackgroundJob(
        name="processPayment",
        event_name="payment/initiated",
        description="Process payment and update subscription",
        retry_count=5,
    ),
    BackgroundJob(
        name="generateReport",
        event_name="report/requested",
        description="Generate and email reports asynchronously",
        timeout="15m",
    ),
    BackgroundJob(
        name="syncData",
        event_name="sync/triggered",
        description="Sync data with external services",
    ),
    BackgroundJob(
        name="cleanupExpired",
        event_name="cron/daily",
        description="Clean up expired sessions and data",
    ),
]


class InngestHelper:
    """Helper for Inngest integration."""
    
    def __init__(self, event_key: Optional[str] = None):
        """Initialize Inngest helper.
        
        Args:
            event_key: Inngest event key. Falls back to env var.
        """
        settings = get_settings()
        self.event_key = event_key or settings.inngest_event_key
    
    @property
    def is_configured(self) -> bool:
        """Check if Inngest is configured."""
        return bool(self.event_key)


def generate_inngest_code(
    project_name: str,
    jobs: Optional[List[BackgroundJob]] = None,
) -> Dict[str, str]:
    """Generate Inngest integration code for a project.
    
    Args:
        project_name: Name of the project
        jobs: List of background jobs to generate
        
    Returns:
        Dict of filename -> file content
    """
    jobs = jobs or COMMON_JOBS
    files = {}
    
    # Generate lib/inngest/client.ts - Inngest client setup
    files["lib/inngest/client.ts"] = f'''import {{ Inngest }} from 'inngest';

// Create Inngest client for {project_name}
export const inngest = new Inngest({{
  id: '{_kebab_case(project_name)}',
  eventKey: process.env.INNGEST_EVENT_KEY,
}});
'''

    # Generate lib/inngest/events.ts - Event type definitions
    event_types = _generate_event_types(jobs)
    files["lib/inngest/events.ts"] = event_types
    
    # Generate individual job files
    for job in jobs:
        job_code = _generate_job_function(job, project_name)
        files[f"lib/inngest/functions/{_kebab_case(job.name)}.ts"] = job_code
    
    # Generate lib/inngest/functions/index.ts - Export all functions
    function_exports = "\n".join([
        f"export {{ {job.name} }} from './{_kebab_case(job.name)}';"
        for job in jobs
    ])
    function_array = ", ".join([job.name for job in jobs])
    files["lib/inngest/functions/index.ts"] = f'''// Background job functions for {project_name}
{function_exports}

import {{ {function_array} }} from '.';

// All functions to register with Inngest
export const allFunctions = [
  {function_array},
];
'''

    # Generate lib/inngest/index.ts - Main export
    files["lib/inngest/index.ts"] = '''export { inngest } from './client';
export * from './events';
export { allFunctions } from './functions';
'''

    # Generate app/api/inngest/route.ts - API handler
    files["app/api/inngest/route.ts"] = '''import { serve } from 'inngest/next';
import { inngest } from '@/lib/inngest';
import { allFunctions } from '@/lib/inngest/functions';

// Serve all Inngest functions
export const { GET, POST, PUT } = serve({
  client: inngest,
  functions: allFunctions,
});
'''

    # Generate utility for sending events
    files["lib/inngest/send.ts"] = '''import { inngest } from './client';
import type { Events } from './events';

/**
 * Send an event to trigger background jobs.
 * 
 * @example
 * await sendEvent('user/created', { userId: '123', email: 'user@example.com' });
 */
export async function sendEvent<K extends keyof Events>(
  name: K,
  data: Events[K]['data']
) {
  return inngest.send({
    name,
    data,
  });
}

/**
 * Send multiple events in a batch.
 */
export async function sendEvents<K extends keyof Events>(
  events: Array<{ name: K; data: Events[K]['data'] }>
) {
  return inngest.send(events);
}
'''

    return files


def _generate_event_types(jobs: List[BackgroundJob]) -> str:
    """Generate TypeScript event type definitions."""
    event_interfaces = []
    
    for job in jobs:
        event_name = job.event_name.replace("/", ".")
        interface_name = _pascal_case(job.event_name.replace("/", "_"))
        
        event_interfaces.append(f'''  '{job.event_name}': {{
    name: '{job.event_name}';
    data: {interface_name}Data;
  }};''')
    
    # Generate data interfaces
    data_interfaces = _generate_data_interfaces(jobs)
    
    return f'''// Event type definitions
// Auto-generated - customize data types as needed

{data_interfaces}

export type Events = {{
{chr(10).join(event_interfaces)}
}};
'''


def _generate_data_interfaces(jobs: List[BackgroundJob]) -> str:
    """Generate data interfaces for events."""
    interfaces = []
    
    for job in jobs:
        interface_name = _pascal_case(job.event_name.replace("/", "_"))
        
        # Generate sample data structure based on event type
        if "user" in job.event_name:
            props = "userId: string;\n  email: string;"
        elif "payment" in job.event_name:
            props = "userId: string;\n  amount: number;\n  currency: string;"
        elif "report" in job.event_name:
            props = "userId: string;\n  reportType: string;\n  filters?: Record<string, any>;"
        elif "sync" in job.event_name:
            props = "entityType: string;\n  entityId?: string;"
        elif "cron" in job.event_name:
            props = "scheduledAt: string;"
        else:
            props = "[key: string]: any;"
        
        interfaces.append(f'''interface {interface_name}Data {{
  {props}
}}''')
    
    return "\n\n".join(interfaces)


def _generate_job_function(job: BackgroundJob, project_name: str) -> str:
    """Generate an individual job function."""
    event_type = _pascal_case(job.event_name.replace("/", "_"))
    
    return f'''import {{ inngest }} from '../client';

/**
 * {job.description}
 * 
 * Triggered by: {job.event_name}
 * Retries: {job.retry_count}
 * Timeout: {job.timeout}
 */
export const {job.name} = inngest.createFunction(
  {{
    id: '{_kebab_case(job.name)}',
    name: '{_title_case(job.name)}',
    retries: {job.retry_count},
  }},
  {{ event: '{job.event_name}' }},
  async ({{ event, step }}) => {{
    // Extract event data
    const {{ data }} = event;
    
    // Step 1: Validate input
    await step.run('validate', async () => {{
      console.log('Validating event data:', data);
      // Add validation logic here
    }});
    
    // Step 2: Execute main logic
    const result = await step.run('execute', async () => {{
      console.log('Executing {job.name}...');
      
      // TODO: Implement job logic
      // Example:
      // await someService.process(data);
      
      return {{ success: true }};
    }});
    
    // Step 3: Cleanup / notification
    await step.run('cleanup', async () => {{
      console.log('Job completed:', result);
      // Add cleanup or notification logic here
    }});
    
    return result;
  }}
);
'''


def _kebab_case(s: str) -> str:
    """Convert string to kebab-case."""
    import re
    s = re.sub(r'([A-Z])', r'-\1', s)
    return s.lower().strip('-').replace('_', '-')


def _pascal_case(s: str) -> str:
    """Convert string to PascalCase."""
    return ''.join(word.title() for word in s.replace('-', '_').split('_'))


def _title_case(s: str) -> str:
    """Convert camelCase to Title Case."""
    import re
    s = re.sub(r'([A-Z])', r' \1', s)
    return s.strip().title()


def get_inngest_env_vars() -> Dict[str, str]:
    """Get environment variables needed for Inngest integration."""
    return {
        "INNGEST_EVENT_KEY": "# Get from https://app.inngest.com/env/production/manage/keys",
        "INNGEST_SIGNING_KEY": "# Optional: For webhook signature verification",
    }


def get_inngest_packages() -> Dict[str, str]:
    """Get npm packages needed for Inngest integration."""
    return {
        "inngest": "^3.0.0",
    }
