import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Database, Search, LayoutDashboard } from "lucide-react"

import { VectorIndexBuilderPage } from "@/pages/VectorIndexBuilderPage"
import { QueryPage } from "@/pages/QueryPage"
import { fetchCurrentVectorIndexEntries } from "@/lib/api"

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

type AppTab = "builder" | "query"

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
    x: 100,
    y: 100,
  }
}

function App() {
  const [showSplash, setShowSplash] = useState(true)
  const [activeTab, setActiveTab] = useState<AppTab>("query")
  const [tables, setTables] = useState<TableDraft[]>([createEmptyTable()])

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

      <div className="flex h-full w-full">
        {/* Sidebar Navigation */}
        <aside className="z-40 flex w-20 flex-col items-center border-r border-border bg-card py-8 shadow-sm">
          <div className="mb-12 flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <LayoutDashboard className="size-6" />
          </div>
          
          <nav className="flex flex-1 flex-col gap-6">
            <SidebarButton 
              icon={<Database className="size-5" />} 
              label="Builder" 
              isActive={activeTab === "builder"} 
              onClick={() => setActiveTab("builder")} 
            />
            <SidebarButton 
              icon={<Search className="size-5" />} 
              label="Query" 
              isActive={activeTab === "query"} 
              onClick={() => setActiveTab("query")} 
            />
          </nav>
          

        </aside>

        {/* Main Content Area */}
        <main className="relative flex-1 overflow-hidden bg-muted/20">
          <div className="relative h-full w-full">
            {/* Builder tab — always mounted after first visit to avoid remount flicker */}
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
          </div>
        </main>
      </div>
    </div>
  )
}

function SidebarButton({ 
  icon, 
  label, 
  isActive, 
  onClick 
}: { 
  icon: React.ReactNode; 
  label: string; 
  isActive: boolean; 
  onClick: () => void 
}) {
  return (
    <button
      onClick={onClick}
      className={`group relative flex size-12 items-center justify-center rounded-xl transition-all duration-200 ${
        isActive 
          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20" 
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      }`}
    >
      {icon}
      <span className="absolute left-16 z-50 rounded-md bg-foreground px-2 py-1 text-xs font-medium text-background opacity-0 transition-opacity group-hover:opacity-100 pointer-events-none">
        {label}
      </span>
      {isActive && (
        <motion.div 
          layoutId="sidebar-active"
          className="absolute -right-3 h-8 w-1 rounded-l-full bg-primary"
        />
      )}
    </button>
  )
}

export default App



