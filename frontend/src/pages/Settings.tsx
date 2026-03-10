import { useState } from 'react'
import { Card } from '@/components/Card'
import { Input } from '@/components/Input'
import { Button } from '@/components/Button'
import { Eye, EyeOff, Check } from 'lucide-react'

export default function Settings() {
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})

  const apiKeys = [
    { id: 'openrouter', label: 'OpenRouter API Key', placeholder: 'sk-or-...' },
    { id: 'v0', label: 'Vercel v0 API Key', placeholder: 'v0_...' },
    { id: 'github', label: 'GitHub Token', placeholder: 'ghp_...' },
    { id: 'vercel', label: 'Vercel Token', placeholder: 'vercel_...' },
  ]

  return (
    <div className="space-y-6 pb-20 lg:pb-0">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">Settings</h2>
        <p className="text-text-secondary mt-1">Configure your API keys and preferences</p>
      </div>

      {/* API Keys */}
      <Card>
        <h3 className="font-medium text-text-primary mb-4">API Keys</h3>
        <div className="space-y-4">
          {apiKeys.map((key) => (
            <div key={key.id} className="space-y-1.5">
              <label className="block text-sm font-medium text-text-secondary">
                {key.label}
              </label>
              <div className="relative">
                <input
                  type={showKeys[key.id] ? 'text' : 'password'}
                  placeholder={key.placeholder}
                  className="w-full px-4 py-2.5 pr-12 bg-background-input border border-border-subtle rounded-[10px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-border-focus"
                />
                <button
                  type="button"
                  onClick={() => setShowKeys((s) => ({ ...s, [key.id]: !s[key.id] }))}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-text-tertiary hover:text-text-secondary"
                >
                  {showKeys[key.id] ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-6 pt-4 border-t border-border-subtle">
          <Button>
            <Check className="w-4 h-4" />
            Save API Keys
          </Button>
        </div>
      </Card>

      {/* Default Settings */}
      <Card>
        <h3 className="font-medium text-text-primary mb-4">Default Preferences</h3>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-text-secondary">
              Default Cost Profile
            </label>
            <select className="w-full px-4 py-2.5 bg-background-input border border-border-subtle rounded-[10px] text-text-primary focus:outline-none focus:ring-2 focus:ring-border-focus">
              <option value="budget">Budget</option>
              <option value="balanced">Balanced</option>
              <option value="premium">Premium</option>
            </select>
          </div>
          
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-text-secondary">
              Cost Alert Threshold ($)
            </label>
            <Input type="number" placeholder="50" />
          </div>
        </div>
      </Card>

      {/* Notifications */}
      <Card>
        <h3 className="font-medium text-text-primary mb-4">Notifications</h3>
        <div className="space-y-3">
          {[
            'Project completed',
            'Project failed',
            'Cost threshold exceeded',
          ].map((item) => (
            <label key={item} className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">{item}</span>
              <input
                type="checkbox"
                defaultChecked
                className="w-5 h-5 rounded border-border-subtle bg-background-input text-accent-primary focus:ring-accent-primary focus:ring-offset-0"
              />
            </label>
          ))}
        </div>
      </Card>
    </div>
  )
}
