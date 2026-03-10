import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Card } from '@/components/Card'
import { Button } from '@/components/Button'
import { Input } from '@/components/Input'
import { api } from '@/lib/api'
import { Mic, ChevronDown, ChevronUp } from 'lucide-react'
import { clsx } from 'clsx'

export default function NewProject() {
  const navigate = useNavigate()
  const [brief, setBrief] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [name, setName] = useState('')
  const [costProfile, setCostProfile] = useState('balanced')
  const [referenceUrls, setReferenceUrls] = useState('')

  const createProject = useMutation({
    mutationFn: api.createProject,
    onSuccess: (data) => {
      navigate(`/project/${data.id}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!brief.trim()) return

    createProject.mutate({
      brief,
      name: name || undefined,
      cost_profile: costProfile,
      reference_urls: referenceUrls ? referenceUrls.split('\n').filter(Boolean) : undefined,
    })
  }

  return (
    <div className="space-y-6 pb-24 lg:pb-0">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">New Project</h2>
        <p className="text-text-secondary mt-1">Describe what you want to build</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Main Input - Perplexity-style */}
        <Card padding="none">
          <div className="relative">
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="What do you want built? Describe your project in detail..."
              className="w-full min-h-[150px] p-4 bg-transparent text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none text-base"
              autoFocus
            />
            <div className="flex items-center justify-between p-3 border-t border-border-subtle">
              <button
                type="button"
                className="p-2 rounded-lg hover:bg-background-tertiary text-text-secondary"
                title="Voice input"
              >
                <Mic className="w-5 h-5" />
              </button>
              <span className="text-xs text-text-tertiary">
                {brief.length} characters
              </span>
            </div>
          </div>
        </Card>

        {/* Advanced Options Accordion */}
        <Card padding="none">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between p-4 text-left"
          >
            <span className="text-sm font-medium text-text-secondary">Advanced Options</span>
            {showAdvanced ? (
              <ChevronUp className="w-5 h-5 text-text-tertiary" />
            ) : (
              <ChevronDown className="w-5 h-5 text-text-tertiary" />
            )}
          </button>
          
          {showAdvanced && (
            <div className="p-4 pt-0 space-y-4 border-t border-border-subtle">
              <Input
                label="Project Name (optional)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Awesome Project"
              />
              
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-text-secondary">
                  Cost Profile
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {['budget', 'balanced', 'premium'].map((profile) => (
                    <button
                      key={profile}
                      type="button"
                      onClick={() => setCostProfile(profile)}
                      className={clsx(
                        'px-3 py-2 rounded-lg text-sm font-medium border transition-colors',
                        costProfile === profile
                          ? 'border-accent-primary bg-accent-primary/10 text-accent-primary'
                          : 'border-border-subtle text-text-secondary hover:border-border-focus'
                      )}
                    >
                      {profile.charAt(0).toUpperCase() + profile.slice(1)}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-text-tertiary">
                  {costProfile === 'budget' && 'Estimated: $1-3 for simple sites'}
                  {costProfile === 'balanced' && 'Estimated: $5-10 for simple sites'}
                  {costProfile === 'premium' && 'Estimated: $15-30 for simple sites'}
                </p>
              </div>
              
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-text-secondary">
                  Reference URLs (one per line)
                </label>
                <textarea
                  value={referenceUrls}
                  onChange={(e) => setReferenceUrls(e.target.value)}
                  placeholder="https://example.com\nhttps://inspiration-site.com"
                  className="w-full px-4 py-2.5 bg-background-input border border-border-subtle rounded-[10px] text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none focus:ring-2 focus:ring-border-focus h-24"
                />
              </div>
            </div>
          )}
        </Card>

        {/* Submit Button - Fixed on mobile */}
        <div className="fixed bottom-20 left-4 right-4 lg:static lg:bottom-auto">
          <Button
            type="submit"
            size="lg"
            className="w-full"
            loading={createProject.isPending}
            disabled={!brief.trim()}
          >
            Start Building
          </Button>
        </div>
      </form>
    </div>
  )
}
