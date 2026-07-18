import { useState } from "react"
import { Server, Globe, Database, AlertCircle, CheckCircle2, X } from "lucide-react"
import { type ConfigPayload, saveEngineConfig } from "@/lib/api"
import { motion } from "framer-motion"

export function SetupPage({ onComplete, onCancel, canCancel = false }: { onComplete: () => void, onCancel?: () => void, canCancel?: boolean }) {
  const [config, setConfig] = useState<ConfigPayload>({
    active_llm: "local",
    local_llm: { model: "granite4.1:3b", base_url: "http://127.0.0.1:11434" },
    remote_llm: { model: "llama-3.1-8b-instant", api_key: "" },
    embedding: { model: "qwen3-embedding:0.6b", base_url: "http://127.0.0.1:11434", api_key: "" },
  })

  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setError(null)

    try {
      await saveEngineConfig(config)
      onComplete()
    } catch (err) {
      const e = err as Error
      setError(e.message || "Failed to save configuration")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6 pb-20">
      <motion.div 
        initial={{ opacity: 0, y: 20 }} 
        animate={{ opacity: 1, y: 0 }} 
        className="w-full max-w-2xl rounded-2xl border border-border bg-card p-6 shadow-xl"
      >
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Welcome to TinyBI</h1>
            <p className="mt-1 text-sm text-muted-foreground">Let's connect your models to get started.</p>
          </div>
          <div>
            {canCancel && onCancel && (
              <button 
                onClick={onCancel}
                type="button"
                aria-label="Close setup"
                className="flex size-10 items-center justify-center rounded-full bg-muted/30 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
              >
                <X className="size-5" />
              </button>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* LLM Selection */}
          <div className="space-y-3">
            <h2 className="text-base font-semibold flex items-center gap-2 border-b border-border pb-2">
              <Server className="size-4" /> Chat Model Configuration
            </h2>
            
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setConfig({ ...config, active_llm: "local" })}
                aria-label="Local LLM"
                className={`flex flex-col items-center justify-center rounded-xl border p-3 transition-all ${
                  config.active_llm === "local" 
                    ? "border-primary bg-primary/5 text-foreground ring-2 ring-primary/20" 
                    : "border-border bg-muted/50 text-muted-foreground hover:bg-muted"
                }`}
              >
                <Server className="mb-1 size-5" />
                <span className="text-sm font-medium">Local (Ollama)</span>
              </button>
              
              <button
                type="button"
                onClick={() => setConfig({ ...config, active_llm: "remote" })}
                aria-label="Remote LLM"
                className={`flex flex-col items-center justify-center rounded-xl border p-3 transition-all ${
                  config.active_llm === "remote" 
                    ? "border-primary bg-primary/5 text-foreground ring-2 ring-primary/20" 
                    : "border-border bg-muted/50 text-muted-foreground hover:bg-muted"
                }`}
              >
                <Globe className="mb-1 size-5" />
                <span className="text-sm font-medium">Remote (Groq)</span>
              </button>
            </div>

            <div className="pt-2">
              {config.active_llm === "local" ? (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium">Ollama Base URL</label>
                    <input 
                      type="text"
                      className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      value={config.local_llm.base_url}
                      onChange={(e) => setConfig({ ...config, local_llm: { ...config.local_llm, base_url: e.target.value }})}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium">Model Name</label>
                    <input 
                      type="text"
                      className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      value={config.local_llm.model}
                      onChange={(e) => setConfig({ ...config, local_llm: { ...config.local_llm, model: e.target.value }})}
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium">Groq API Key</label>
                    <input 
                      type="password"
                      className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      placeholder="gsk_..."
                      value={config.remote_llm.api_key}
                      onChange={(e) => setConfig({ ...config, remote_llm: { ...config.remote_llm, api_key: e.target.value }})}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium">Model Name</label>
                    <input 
                      type="text"
                      className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      value={config.remote_llm.model}
                      onChange={(e) => setConfig({ ...config, remote_llm: { ...config.remote_llm, model: e.target.value }})}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Embedding Selection */}
          <div className="space-y-3 pt-2">
            <h2 className="text-base font-semibold flex items-center gap-2 border-b border-border pb-2">
              <Database className="size-4" /> Embedding Configuration
            </h2>
            
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium">Model Name</label>
                <input 
                  type="text"
                  className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  value={config.embedding.model}
                  onChange={(e) => setConfig({ ...config, embedding: { ...config.embedding, model: e.target.value }})}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium">Base URL</label>
                <input 
                  type="text"
                  className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  value={config.embedding.base_url}
                  onChange={(e) => setConfig({ ...config, embedding: { ...config.embedding, base_url: e.target.value }})}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium">API Key (Optional for Jina)</label>
              <input 
                type="password"
                className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                value={config.embedding.api_key}
                onChange={(e) => setConfig({ ...config, embedding: { ...config.embedding, api_key: e.target.value }})}
              />
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-start gap-3 rounded-xl border border-destructive/50 bg-destructive/10 p-4 text-destructive"
            >
              <AlertCircle className="mt-0.5 size-5 shrink-0" />
              <div className="text-sm font-medium">{error}</div>
            </motion.div>
          )}

          {/* Submit */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={isSaving}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 cursor-pointer"
            >
              {isSaving ? (
                <div className="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              ) : (
                <>
                  <CheckCircle2 className="size-4" />
                  Save & Connect
                </>
              )}
            </button>
          </div>

        </form>
      </motion.div>
    </div>
  )
}
