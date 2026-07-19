import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Activity, Target, Clock, Zap, ExternalLink } from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Line,
} from "recharts"

import {
  fetchOverviewStats,
  fetchDifficultySegregated,
  fetchProviderComparison,
  type OverviewStats,
  type ProviderComparisonStats,
} from "@/lib/api"
import { Button } from "@/components/ui/button"

export function MonitoringPage() {
  const [overview, setOverview] = useState<OverviewStats | null>(null)
  const [breakdown, setBreakdown] = useState<any[]>([])
  const [comparison, setComparison] = useState<ProviderComparisonStats[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const [overviewData, rawSegregated, comparisonData] = await Promise.all([
          fetchOverviewStats(),
          fetchDifficultySegregated(),
          fetchProviderComparison(),
        ])

        if (typeof overviewData === "string" || typeof rawSegregated === "string" || typeof comparisonData === "string") {
          throw new Error("Failed to fetch monitoring stats (got string)")
        }
        
        // Transform segregated data into combined composed chart format
        const mergedByDifficulty: Record<string, any> = {}
        for (const item of rawSegregated) {
          if (!mergedByDifficulty[item.difficulty]) {
            mergedByDifficulty[item.difficulty] = { difficulty: item.difficulty }
          }
          if (item.provider === "TinyBI") {
            mergedByDifficulty[item.difficulty].tinyBIAccuracy = item.accuracy
            mergedByDifficulty[item.difficulty].tinyBITokens = item.tokens
          } else if (item.provider === "Schema Dump") {
            mergedByDifficulty[item.difficulty].schemaDumpAccuracy = item.accuracy
            mergedByDifficulty[item.difficulty].schemaDumpTokens = item.tokens
          }
        }
        
        const order: Record<string, number> = { "simple": 0, "moderate": 1, "challenging": 2 }
        const mergedArray = Object.values(mergedByDifficulty).sort((a, b) => (order[a.difficulty] ?? 99) - (order[b.difficulty] ?? 99))
        
        setOverview(overviewData)
        setBreakdown(mergedArray)
        setComparison(comparisonData)
      } catch (err) {
        console.error("Failed to fetch monitoring stats", err)
      } finally {
        setIsLoading(false)
      }
    }
    loadData()
  }, [])

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 text-muted-foreground">
          <Activity className="size-8 animate-pulse text-primary" />
          <p>Loading System Health...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-background p-6">
      <header className="mb-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">System Health & Evaluation</h1>
            <p className="text-sm text-muted-foreground">Monitoring accuracy, latency, and tokens across the agent pipeline.</p>
          </div>
          <Button variant="outline" className="gap-2" asChild>
            <a href="http://localhost:15500" target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-4" />
              Promptfoo Dashboard
            </a>
          </Button>
        </div>

        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-muted-foreground flex items-start gap-3">
          <Zap className="size-5 shrink-0 text-amber-500 mt-0.5" />
          <div className="flex flex-col gap-1.5">
            <p>
              <strong className="text-foreground font-medium">Evaluation Runtime Environment:</strong> These metrics were captured using a high-performance evaluation cluster equipped with specialized hardware (NVIDIA Tesla GPUs) running accelerated inference via vLLM. Consequently, latency figures reflect this specialized testing environment rather than the standard local TinyBI deployment configuration.
            </p>
            {overview?.lastRun && (
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground/80 font-medium">
                <Clock className="size-3.5" />
                <span>Last evaluation run: {new Date(overview.lastRun).toLocaleString(undefined, {
                  year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                })}</span>
              </p>
            )}
          </div>
        </div>
      </header>

      {/* Headline Stats */}
      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <StatCard
          title="Overall Accuracy"
          value={overview ? `${(overview.overallAccuracy * 100).toFixed(2)}%` : "0%"}
          icon={<Target className="size-5 text-emerald-500" />}
          delay={0.1}
        />
        <StatCard
          title="Mean Latency"
          value={overview ? `${(overview.meanLatencyMs / 1000).toFixed(2)}s` : "0s"}
          icon={<Clock className="size-5 text-blue-500" />}
          delay={0.2}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Difficulty Breakdown Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col"
        >
          <h2 className="mb-4 text-lg font-semibold shrink-0">Performance by Difficulty (TinyBI vs Schema Dump)</h2>
          <div className="h-[300px] w-full mt-auto">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={breakdown}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                <XAxis 
                  dataKey="difficulty" 
                  tick={{ fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  yAxisId="left" 
                  tick={{ fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                />
                <YAxis 
                  yAxisId="right" 
                  orientation="right" 
                  domain={[0, 1]} 
                  tick={{ fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: "var(--background)", borderColor: "var(--border)", borderRadius: "8px", opacity: 1 }}
                  cursor={{ fill: "var(--muted)", opacity: 0.4 }}
                  formatter={(value: any, name: any) => {
                    if (name && String(name).includes("Accuracy")) return [`${(Number(value) * 100).toFixed(2)}%`, name];
                    if (name && String(name).includes("Tokens")) return [`${(Number(value) / 1000).toFixed(2)}k`, name];
                    return [value, name];
                  }}
                />
                <Legend />
                <Bar yAxisId="left" dataKey="tinyBITokens" name="TinyBI Tokens" fill="#a855f7" radius={[4, 4, 0, 0]} />
                <Bar yAxisId="left" dataKey="schemaDumpTokens" name="Schema Dump Tokens" fill="#64748b" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="linear" dataKey="tinyBIAccuracy" name="TinyBI Accuracy" stroke="#10b981" strokeWidth={3} />
                <Line yAxisId="right" type="linear" dataKey="schemaDumpAccuracy" name="Schema Dump Accuracy" stroke="#3b82f6" strokeWidth={3} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Provider Comparison Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col"
        >
          <h2 className="mb-4 text-lg font-semibold shrink-0">Results (TinyBI vs Schema Dump)</h2>
          <div className="h-[300px] w-full mt-auto">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparison}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                <XAxis 
                  dataKey="provider" 
                  tick={{ fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  tick={{ fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: "var(--background)", borderColor: "var(--border)", borderRadius: "8px", opacity: 1 }}
                  cursor={{ fill: "var(--muted)", opacity: 0.4 }}
                />
                <Legend />
                <Bar dataKey="correct" stackId="a" fill="#10b981" name="Correct" />
                <Bar dataKey="fail" stackId="a" fill="#f59e0b" name="Fail (Wrong Answer)" />
                <Bar dataKey="error" stackId="a" fill="#ef4444" name="Error (SQL/Agent Crash)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon, delay }: { title: string; value: string; icon: React.ReactNode; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.4 }}
      className="flex items-center gap-4 rounded-2xl border border-border bg-card p-6 shadow-sm hover:bg-muted/30 transition-colors"
    >
      <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-muted/50">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <p className="text-2xl font-bold tracking-tight">{value}</p>
      </div>
    </motion.div>
  )
}
