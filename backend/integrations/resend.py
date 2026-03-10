"""Resend Email Integration Helpers.

Generates Resend email integration code for SaaS projects.
Used by: Code Generation Agent (for web_complex, python_saas with auth)

Generates:
- React Email templates
- Email sending utility
- Environment variables
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmailTemplate:
    """Email template definition."""
    name: str
    subject: str
    description: str
    variables: List[str]  # Template variables


# Common email templates for SaaS projects
COMMON_TEMPLATES: List[EmailTemplate] = [
    EmailTemplate(
        name="welcome",
        subject="Welcome to {app_name}!",
        description="Sent when a new user signs up",
        variables=["user_name", "app_name", "login_url"],
    ),
    EmailTemplate(
        name="password_reset",
        subject="Reset your password",
        description="Sent when user requests password reset",
        variables=["user_name", "reset_url", "expiry_hours"],
    ),
    EmailTemplate(
        name="email_verification",
        subject="Verify your email address",
        description="Sent for email verification",
        variables=["user_name", "verification_url", "app_name"],
    ),
    EmailTemplate(
        name="invoice",
        subject="Invoice #{invoice_number}",
        description="Sent when invoice is generated",
        variables=["user_name", "invoice_number", "amount", "due_date", "invoice_url"],
    ),
]


class ResendHelper:
    """Helper for Resend email integration."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Resend helper.
        
        Args:
            api_key: Resend API key. Falls back to env var.
        """
        settings = get_settings()
        self.api_key = api_key or settings.resend_api_key
    
    @property
    def is_configured(self) -> bool:
        """Check if Resend is configured."""
        return bool(self.api_key)


def generate_resend_code(
    project_name: str,
    from_email: str = "noreply@example.com",
    templates: Optional[List[EmailTemplate]] = None,
) -> Dict[str, str]:
    """Generate Resend integration code for a project.
    
    Args:
        project_name: Name of the project
        from_email: Default sender email
        templates: List of email templates to generate
        
    Returns:
        Dict of filename -> file content
    """
    templates = templates or COMMON_TEMPLATES
    files = {}
    
    # Generate lib/email.ts - Email sending utility
    files["lib/email.ts"] = f'''import {{ Resend }} from 'resend';

const resend = new Resend(process.env.RESEND_API_KEY);

export interface SendEmailOptions {{
  to: string | string[];
  subject: string;
  html?: string;
  react?: React.ReactElement;
  from?: string;
  replyTo?: string;
}}

export async function sendEmail(options: SendEmailOptions) {{
  const {{ to, subject, html, react, from, replyTo }} = options;
  
  try {{
    const {{ data, error }} = await resend.emails.send({{
      from: from || '{from_email}',
      to: Array.isArray(to) ? to : [to],
      subject,
      html,
      react,
      replyTo,
    }});
    
    if (error) {{
      console.error('Email send error:', error);
      throw new Error(error.message);
    }}
    
    return {{ success: true, id: data?.id }};
  }} catch (err) {{
    console.error('Failed to send email:', err);
    throw err;
  }}
}}

// Batch email sending
export async function sendBatchEmails(emails: SendEmailOptions[]) {{
  const results = await Promise.allSettled(
    emails.map(email => sendEmail(email))
  );
  
  return results.map((result, index) => ({{
    email: emails[index].to,
    success: result.status === 'fulfilled',
    error: result.status === 'rejected' ? result.reason : null,
  }}));
}}
'''

    # Generate email templates
    for template in templates:
        template_code = _generate_email_template(template, project_name)
        files[f"emails/{template.name}.tsx"] = template_code
    
    # Generate emails/index.ts
    template_exports = "\n".join([
        f"export {{ {_camel_case(t.name)}Email }} from './{t.name}';"
        for t in templates
    ])
    files["emails/index.ts"] = f"// Email templates for {project_name}\n{template_exports}\n"
    
    # Generate types
    files["lib/email.types.ts"] = '''export interface EmailResult {
  success: boolean;
  id?: string;
  error?: string;
}

export interface BatchEmailResult {
  email: string | string[];
  success: boolean;
  error?: string;
}
'''
    
    return files


def _generate_email_template(template: EmailTemplate, project_name: str) -> str:
    """Generate a React Email template component."""
    component_name = _camel_case(template.name) + "Email"
    props_interface = _generate_props_interface(template)
    
    return f'''import {{
  Body,
  Button,
  Container,
  Head,
  Heading,
  Html,
  Link,
  Preview,
  Section,
  Text,
}} from '@react-email/components';
import * as React from 'react';

{props_interface}

export const {component_name} = ({{
  {', '.join(template.variables)}
}}: {component_name}Props) => {{
  return (
    <Html>
      <Head />
      <Preview>{template.subject}</Preview>
      <Body style={{{{ ...main }}}}>
        <Container style={{{{ ...container }}}}>
          <Heading style={{{{ ...h1 }}}}>{template.subject}</Heading>
          <Text style={{{{ ...text }}}}>
            {_generate_template_body(template)}
          </Text>
          <Section style={{{{ ...buttonContainer }}}}>
            <Button style={{{{ ...button }}}} href="#">
              Get Started
            </Button>
          </Section>
          <Text style={{{{ ...footer }}}}>
            © {project_name}. All rights reserved.
          </Text>
        </Container>
      </Body>
    </Html>
  );
}};

export default {component_name};

// Styles
const main = {{
  backgroundColor: '#f6f9fc',
  fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif',
}};

const container = {{
  backgroundColor: '#ffffff',
  margin: '0 auto',
  padding: '40px 20px',
  maxWidth: '560px',
  borderRadius: '8px',
}};

const h1 = {{
  color: '#1a1a1a',
  fontSize: '24px',
  fontWeight: '600',
  lineHeight: '1.3',
  margin: '0 0 20px',
}};

const text = {{
  color: '#4a4a4a',
  fontSize: '16px',
  lineHeight: '1.6',
  margin: '0 0 20px',
}};

const buttonContainer = {{
  textAlign: 'center' as const,
  margin: '30px 0',
}};

const button = {{
  backgroundColor: '#5469d4',
  borderRadius: '6px',
  color: '#fff',
  fontSize: '16px',
  fontWeight: '600',
  textDecoration: 'none',
  textAlign: 'center' as const,
  padding: '12px 24px',
}};

const footer = {{
  color: '#898989',
  fontSize: '12px',
  textAlign: 'center' as const,
  marginTop: '40px',
}};
'''


def _generate_props_interface(template: EmailTemplate) -> str:
    """Generate TypeScript props interface for email template."""
    props = "\n  ".join([f"{var}: string;" for var in template.variables])
    component_name = _camel_case(template.name) + "Email"
    return f"interface {component_name}Props {{\n  {props}\n}}"


def _generate_template_body(template: EmailTemplate) -> str:
    """Generate template body text."""
    if template.name == "welcome":
        return "Hi {user_name}, welcome to {app_name}! We're excited to have you on board."
    elif template.name == "password_reset":
        return "Hi {user_name}, click the button below to reset your password. This link expires in {expiry_hours} hours."
    elif template.name == "email_verification":
        return "Hi {user_name}, please verify your email address to complete your {app_name} account setup."
    elif template.name == "invoice":
        return "Hi {user_name}, your invoice #{invoice_number} for {amount} is ready. Due date: {due_date}."
    return f"Template for {template.name}"


def _camel_case(snake_str: str) -> str:
    """Convert snake_case to CamelCase."""
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)


def get_resend_env_vars() -> Dict[str, str]:
    """Get environment variables needed for Resend integration."""
    return {
        "RESEND_API_KEY": "# Get from https://resend.com/api-keys",
    }


def get_resend_packages() -> Dict[str, str]:
    """Get npm packages needed for Resend integration."""
    return {
        "resend": "^2.0.0",
        "@react-email/components": "^0.0.15",
        "react-email": "^2.0.0",
    }
