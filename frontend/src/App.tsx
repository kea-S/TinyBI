import React, { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { LayoutDashboard } from "lucide-react"

import { VectorIndexBuilderPage } from "@/pages/VectorIndexBuilderPage"
import { QueryPage } from "@/pages/QueryPage"
import { MonitoringPage } from "@/pages/MonitoringPage"
import { SetupPage } from "@/pages/SetupPage"
import { fetchCurrentVectorIndexEntries, fetchEngineConfig } from "@/lib/api"

// --- Types for shared state ---
export type CategoricalValue = {
  id: string
  dbValue: string
  synonymsText: string
}

export type ColumnDraft = {
  id: string
  columnName: string
  sourceKey: string
  description: string
  dataFormat: string
  statisticalType: string
  categoricalValues: CategoricalValue[]
  aliasesText: string
  sampleValuesText: string
  payloadText: string
  references: string
}

export type TableDraft = {
  id: string
  name: string
  columns: ColumnDraft[]
  x?: number
  y?: number
}

type AppTab = "setup" | "builder" | "query" | "monitoring"

function createId(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`
}

function createEmptyColumn(): ColumnDraft {
  return {
    id: createId("column"),
    columnName: "",
    sourceKey: "",
    description: "",
    dataFormat: "",
    statisticalType: "nominal",
    categoricalValues: [],
    aliasesText: "",
    sampleValuesText: "",
    payloadText: '{\n  "is_groupable": true\n}',
    references: "",
  }
}

function createEmptyTable(): TableDraft {
  return {
    id: createId("table"),
    name: "",
    columns: [createEmptyColumn()],
  }
}

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "20px", color: "red", backgroundColor: "black", height: "100vh" }}>
          <h1>Something went wrong.</h1>
          <pre>{this.state.error?.toString()}</pre>
          <pre>{this.state.error?.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

function MainApp() {
  const [showSplash, setShowSplash] = useState(true)
  const [isConfigLoaded, setIsConfigLoaded] = useState(false)
  const [activeTab, setActiveTab] = useState<AppTab>("query")
  const [tables, setTables] = useState<TableDraft[]>([createEmptyTable()])
  const [config, setConfig] = useState({ llm: "Loading...", embedding: "Loading..." })

  const loadConfig = () => {
    fetchEngineConfig().then((data) => {
      if (typeof data === "string") {
        console.error("Expected ConfigResponse, got string", data);
        setIsConfigLoaded(true);
        return;
      }
      if (!data.configured) {
        setActiveTab("setup")
      } else if (data.config) {
        const activeLLM = data.config.active_llm
        setConfig({
          llm: activeLLM === "local" ? data.config.local_llm.model : data.config.remote_llm.model,
          embedding: data.config.embedding.model
        })
        if (activeTab === "setup") {
          setActiveTab("query")
        }
      }
      setIsConfigLoaded(true)
    }).catch((err) => {
      console.error(err)
      setIsConfigLoaded(true)
    })
  }

  // Initial data load
  useEffect(() => {
    const timer = setTimeout(() => setShowSplash(false), 1200)
    
    fetchCurrentVectorIndexEntries().then((result) => {
      if (typeof result !== "string" && result.length > 0) {
        // Simple mapping from API to draft state
        const tablesByName = new Map<string, TableDraft>()
        result.forEach((entry) => {
          let table = tablesByName.get(entry.table_name)
          if (!table) {
            table = {
              id: createId("table"),
              name: entry.table_name,
              columns: [],
              x: 100 + (tablesByName.size * 350),
              y: 100,
            }
            tablesByName.set(entry.table_name, table)
          }
          
          const categoricalValues: CategoricalValue[] = []
          if (entry.categorical_values) {
            Object.entries(entry.categorical_values).forEach(([dbValue, synonyms]) => {
              categoricalValues.push({
                id: createId("cat"),
                dbValue,
                synonymsText: synonyms.join(", "),
              })
            })
          }

          table.columns.push({
            id: createId("column"),
            columnName: entry.column_name,
            sourceKey: entry.source_key,
            description: entry.description ?? "",
            dataFormat: entry.data_format ?? "",
            statisticalType: entry.statistical_type ?? "nominal",
            categoricalValues,
            aliasesText: entry.aliases.join(", "),
            sampleValuesText: entry.sample_values.join(", "),
            payloadText: JSON.stringify(entry.payload, null, 2),
            references: entry.references ?? "",
          })
        })
        if (tablesByName.size > 0) {
          setTables(Array.from(tablesByName.values()))
        }
      }
    })

    loadConfig()

    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="relative h-screen w-full overflow-hidden bg-background text-foreground font-sans">
      <AnimatePresence>
        {showSplash && (
          <motion.div
            key="splash"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.8, ease: "easeInOut" }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="flex items-center gap-4"
            >
              <div className="flex size-16 items-center justify-center rounded-2xl bg-primary shadow-lg shadow-primary/20">
                <LayoutDashboard className="size-8 text-primary-foreground" />
              </div>
              <motion.h1 
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.3, duration: 0.8 }}
                className="text-6xl font-bold tracking-tighter"
              >
                TinyBI
              </motion.h1>
            </motion.div>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8, duration: 0.5 }}
              className="mt-6 text-muted-foreground"
            >
              Your data, naturally understood.
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex h-full w-full flex-col">
        {/* Top Navigation */}
        {activeTab !== "setup" && (
          <header className="z-40 flex h-16 w-full shrink-0 items-center justify-between border-b border-border bg-card px-6 shadow-sm">
          <div className="flex items-center gap-8">
            <button 
              onClick={() => window.location.reload()} 
              className="ml-2 flex items-center transition-opacity hover:opacity-80 cursor-pointer"
              aria-label="Refresh application"
            >
               <img src="/favicon.svg" alt="TinyBI Logo" className="size-8" />
            </button>

            <nav className="flex items-center gap-6">
              <TopNavButton 
                label="Builder" 
                isActive={activeTab === "builder"} 
                onClick={() => setActiveTab("builder")} 
              />
              <TopNavButton 
                label="Query" 
                isActive={activeTab === "query"} 
                onClick={() => setActiveTab("query")} 
              />
              <TopNavButton 
                label="Monitoring" 
                isActive={activeTab === "monitoring"} 
                onClick={() => setActiveTab("monitoring")} 
              />
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <button 
              onClick={() => setActiveTab("setup")}
              className="flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground cursor-pointer"
            >
               <div className="size-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] animate-pulse" />
               LLM: {config.llm}
            </button>
            <button 
              onClick={() => setActiveTab("setup")}
              className="flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground cursor-pointer"
            >
               <div className="size-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)] animate-pulse" />
               Vector: {config.embedding}
            </button>
          </div>
          </header>
        )}

        {/* Main Content Area */}
        <main className="relative flex-1 overflow-hidden bg-muted/20">
          <div className="relative h-full w-full">
            {!isConfigLoaded ? (
              <div className="flex h-full items-center justify-center">
                <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </div>
            ) : activeTab === "setup" ? (
              <SetupPage 
                onComplete={loadConfig} 
                canCancel={config.llm !== "Loading..."} 
                onCancel={() => setActiveTab("query")} 
              />
            ) : (
              <>
                {/* Builder tab */}
                <div
                  className={`absolute inset-0 transition-opacity duration-300 ${
                    activeTab === "builder"
                      ? "opacity-100 z-10"
                      : "opacity-0 z-0 pointer-events-none"
                  }`}
                >
                  <VectorIndexBuilderPage tables={tables} setTables={setTables} isVisible={activeTab === "builder"} />
                </div>
                {/* Query tab */}
                <div
                  className={`absolute inset-0 transition-opacity duration-300 ${
                    activeTab === "query"
                      ? "opacity-100 z-10"
                      : "opacity-0 z-0 pointer-events-none"
                  }`}
                >
                  <QueryPage />
                </div>
                {/* Monitoring tab */}
                <div
                  className={`absolute inset-0 transition-opacity duration-300 ${
                    activeTab === "monitoring"
                      ? "opacity-100 z-10"
                      : "opacity-0 z-0 pointer-events-none"
                  }`}
                >
                  <MonitoringPage />
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

function TopNavButton({ 
  label, 
  isActive, 
  onClick 
}: { 
  label: string; 
  isActive: boolean; 
  onClick: () => void 
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={`relative text-sm font-medium transition-colors hover:text-foreground cursor-pointer ${
        isActive 
          ? "text-foreground underline decoration-primary decoration-2 underline-offset-8" 
          : "text-muted-foreground hover:underline hover:decoration-muted-foreground/50 hover:decoration-2 hover:underline-offset-8"
      }`}
    >
      {label}
    </button>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  )
}
