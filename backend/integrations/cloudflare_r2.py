"""Cloudflare R2 Storage Integration Helpers.

Generates R2 file storage integration code for projects with uploads.
Used by: Code Generation Agent (for web_complex, python_saas with file uploads)

Generates:
- Upload utility with presigned URLs
- Download utility
- File management helpers
- Environment variables
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class R2Config:
    """R2 configuration."""
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    account_id: str
    
    @property
    def endpoint(self) -> str:
        """Get R2 endpoint URL."""
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


class R2Helper:
    """Helper for Cloudflare R2 integration."""
    
    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        account_id: Optional[str] = None,
    ):
        """Initialize R2 helper.
        
        Args:
            access_key_id: R2 access key ID. Falls back to env var.
            secret_access_key: R2 secret access key. Falls back to env var.
            bucket_name: R2 bucket name. Falls back to env var.
            account_id: Cloudflare account ID. Falls back to env var.
        """
        settings = get_settings()
        self.access_key_id = access_key_id or settings.r2_access_key_id
        self.secret_access_key = secret_access_key or settings.r2_secret_access_key
        self.bucket_name = bucket_name or settings.r2_bucket_name
        self.account_id = account_id or settings.r2_account_id
    
    @property
    def is_configured(self) -> bool:
        """Check if R2 is configured."""
        return bool(
            self.access_key_id and
            self.secret_access_key and
            self.bucket_name and
            self.account_id
        )


def generate_r2_code(
    project_name: str,
    max_file_size_mb: int = 10,
    allowed_types: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Generate R2 integration code for a project.
    
    Args:
        project_name: Name of the project
        max_file_size_mb: Maximum file size in MB
        allowed_types: Allowed MIME types
        
    Returns:
        Dict of filename -> file content
    """
    allowed_types = allowed_types or [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
        "text/plain",
    ]
    
    files = {}
    
    # Generate lib/r2.ts - Main R2 utility
    files["lib/r2.ts"] = f'''import {{ S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand }} from '@aws-sdk/client-s3';
import {{ getSignedUrl }} from '@aws-sdk/s3-request-presigner';

const R2_ENDPOINT = `https://${{process.env.R2_ACCOUNT_ID}}.r2.cloudflarestorage.com`;

const r2Client = new S3Client({{
  region: 'auto',
  endpoint: R2_ENDPOINT,
  credentials: {{
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  }},
}});

const BUCKET_NAME = process.env.R2_BUCKET_NAME!;
const MAX_FILE_SIZE = {max_file_size_mb} * 1024 * 1024; // {max_file_size_mb}MB
const ALLOWED_TYPES = {allowed_types};

export interface UploadOptions {{
  file: File | Buffer;
  key: string;
  contentType?: string;
  metadata?: Record<string, string>;
}}

export interface PresignedUrlOptions {{
  key: string;
  contentType: string;
  expiresIn?: number; // seconds, default 3600
}}

/**
 * Get a presigned URL for direct upload from client.
 */
export async function getUploadUrl(options: PresignedUrlOptions): Promise<string> {{
  const {{ key, contentType, expiresIn = 3600 }} = options;
  
  if (!ALLOWED_TYPES.includes(contentType)) {{
    throw new Error(`File type ${{contentType}} not allowed`);
  }}
  
  const command = new PutObjectCommand({{
    Bucket: BUCKET_NAME,
    Key: key,
    ContentType: contentType,
  }});
  
  return getSignedUrl(r2Client, command, {{ expiresIn }});
}}

/**
 * Get a presigned URL for downloading a file.
 */
export async function getDownloadUrl(key: string, expiresIn = 3600): Promise<string> {{
  const command = new GetObjectCommand({{
    Bucket: BUCKET_NAME,
    Key: key,
  }});
  
  return getSignedUrl(r2Client, command, {{ expiresIn }});
}}

/**
 * Upload a file directly (server-side).
 */
export async function uploadFile(options: UploadOptions): Promise<{{ key: string; url: string }}> {{
  const {{ file, key, contentType, metadata }} = options;
  
  let body: Buffer;
  let size: number;
  
  if (file instanceof Buffer) {{
    body = file;
    size = file.length;
  }} else {{
    body = Buffer.from(await file.arrayBuffer());
    size = file.size;
  }}
  
  if (size > MAX_FILE_SIZE) {{
    throw new Error(`File size exceeds maximum of ${{MAX_FILE_SIZE / 1024 / 1024}}MB`);
  }}
  
  const command = new PutObjectCommand({{
    Bucket: BUCKET_NAME,
    Key: key,
    Body: body,
    ContentType: contentType,
    Metadata: metadata,
  }});
  
  await r2Client.send(command);
  
  return {{
    key,
    url: await getDownloadUrl(key),
  }};
}}

/**
 * Delete a file from R2.
 */
export async function deleteFile(key: string): Promise<void> {{
  const command = new DeleteObjectCommand({{
    Bucket: BUCKET_NAME,
    Key: key,
  }});
  
  await r2Client.send(command);
}}

/**
 * Generate a unique file key.
 */
export function generateFileKey(filename: string, prefix = 'uploads'): string {{
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  const ext = filename.split('.').pop();
  return `${{prefix}}/${{timestamp}}-${{random}}.${{ext}}`;
}}

/**
 * Validate file before upload.
 */
export function validateFile(file: File): {{ valid: boolean; error?: string }} {{
  if (file.size > MAX_FILE_SIZE) {{
    return {{ valid: false, error: `File size exceeds ${{MAX_FILE_SIZE / 1024 / 1024}}MB limit` }};
  }}
  
  if (!ALLOWED_TYPES.includes(file.type)) {{
    return {{ valid: false, error: `File type ${{file.type}} not allowed` }};
  }}
  
  return {{ valid: true }};
}}
'''

    # Generate lib/r2.types.ts
    files["lib/r2.types.ts"] = '''export interface UploadedFile {
  key: string;
  url: string;
  filename: string;
  contentType: string;
  size: number;
  uploadedAt: Date;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface FileValidationResult {
  valid: boolean;
  error?: string;
}
'''

    # Generate hooks/useFileUpload.ts - React hook for uploads
    files["hooks/useFileUpload.ts"] = '''import { useState, useCallback } from 'react';

interface UploadState {
  uploading: boolean;
  progress: number;
  error: string | null;
  url: string | null;
}

export function useFileUpload() {
  const [state, setState] = useState<UploadState>({
    uploading: false,
    progress: 0,
    error: null,
    url: null,
  });

  const upload = useCallback(async (file: File) => {
    setState({ uploading: true, progress: 0, error: null, url: null });

    try {
      // Get presigned URL from API
      const response = await fetch('/api/upload/presigned', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          contentType: file.type,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to get upload URL');
      }

      const { uploadUrl, key, downloadUrl } = await response.json();

      // Upload directly to R2
      const uploadResponse = await fetch(uploadUrl, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type,
        },
      });

      if (!uploadResponse.ok) {
        throw new Error('Upload failed');
      }

      setState({ uploading: false, progress: 100, error: null, url: downloadUrl });
      return { key, url: downloadUrl };
    } catch (err) {
      const error = err instanceof Error ? err.message : 'Upload failed';
      setState({ uploading: false, progress: 0, error, url: null });
      throw err;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ uploading: false, progress: 0, error: null, url: null });
  }, []);

  return {
    ...state,
    upload,
    reset,
  };
}
'''

    # Generate api/upload/presigned/route.ts - API endpoint
    files["app/api/upload/presigned/route.ts"] = '''import { NextResponse } from 'next/server';
import { getUploadUrl, getDownloadUrl, generateFileKey, validateFile } from '@/lib/r2';

export async function POST(request: Request) {
  try {
    const { filename, contentType } = await request.json();

    if (!filename || !contentType) {
      return NextResponse.json(
        { message: 'Missing filename or contentType' },
        { status: 400 }
      );
    }

    // Generate unique key
    const key = generateFileKey(filename);

    // Get presigned upload URL
    const uploadUrl = await getUploadUrl({
      key,
      contentType,
      expiresIn: 3600,
    });

    // Get download URL
    const downloadUrl = await getDownloadUrl(key);

    return NextResponse.json({
      uploadUrl,
      key,
      downloadUrl,
    });
  } catch (err) {
    console.error('Presigned URL error:', err);
    return NextResponse.json(
      { message: err instanceof Error ? err.message : 'Failed to generate URL' },
      { status: 500 }
    );
  }
}
'''

    return files


def get_r2_env_vars() -> Dict[str, str]:
    """Get environment variables needed for R2 integration."""
    return {
        "R2_ACCESS_KEY_ID": "# Get from Cloudflare Dashboard > R2 > Manage R2 API Tokens",
        "R2_SECRET_ACCESS_KEY": "# Get from Cloudflare Dashboard > R2 > Manage R2 API Tokens",
        "R2_BUCKET_NAME": "# Your R2 bucket name",
        "R2_ACCOUNT_ID": "# Your Cloudflare account ID (from dashboard URL)",
    }


def get_r2_packages() -> Dict[str, str]:
    """Get npm packages needed for R2 integration."""
    return {
        "@aws-sdk/client-s3": "^3.500.0",
        "@aws-sdk/s3-request-presigner": "^3.500.0",
    }
