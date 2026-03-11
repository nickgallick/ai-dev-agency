import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { lazy, Suspense } from 'react'
import { ArrowLeft, Loader2 } from 'lucide-react'

const LiveCodePreview = lazy(() => import('@/components/LiveCodePreview'))

export default function LivePreview() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => api.getProject(id!),
    enabled: !!id,
  })

  const { data: outputs, isLoading } = useQuery({
    queryKey: ['projectOutputs', id],
    queryFn: () => api.getProjectOutputs(id!),
    enabled: !!id,
  })

  const codeGen = outputs?.agent_outputs?.code_generation
  const codeFiles = codeGen?.files || codeGen?.generated_files || []
  const fileContents = codeGen?.file_contents || codeGen?.code || codeGen?.source_files

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header bar */}
      <div
        className="flex items-center gap-3 px-4 py-2 border-b shrink-0"
        style={{ borderColor: 'var(--border-subtle)', background: 'var(--background-secondary)' }}
      >
        <button
          onClick={() => navigate(`/project/${id}`)}
          className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Project
        </button>
        <div className="w-px h-5" style={{ background: 'var(--border-subtle)' }} />
        <span className="text-sm font-medium text-text-primary truncate">
          {project?.name || 'Project'} — Live Preview
        </span>
      </div>

      {/* Preview area — fills remaining height */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" style={{ color: 'var(--accent-primary)' }} />
              <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Loading project files...</p>
            </div>
          </div>
        ) : codeFiles.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <p className="text-base font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                No code files available yet
              </p>
              <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                The code generation agent hasn't produced output yet. Check back once the pipeline reaches the code generation step.
              </p>
              <button
                onClick={() => navigate(`/project/${id}`)}
                className="mt-4 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                style={{ background: 'var(--accent-primary)', color: 'white' }}
              >
                Back to Pipeline View
              </button>
            </div>
          </div>
        ) : (
          <Suspense fallback={
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" style={{ color: 'var(--accent-primary)' }} />
                <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Loading live preview...</p>
              </div>
            </div>
          }>
            <LiveCodePreview
              files={codeFiles}
              projectType={project?.project_type || undefined}
              fileContents={typeof fileContents === 'object' ? fileContents : undefined}
            />
          </Suspense>
        )}
      </div>
    </div>
  )
}
