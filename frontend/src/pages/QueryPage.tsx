import { useState } from "react"
import { Search, Send, Code, Table as TableIcon, Sparkles, ChevronDown, ChevronUp } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  submitQuery,
  type QueryResponse,
} from "@/lib/api"

type QueryState = "idle" | "loading" | "success" | "error"

type QueryPageProps = {
  isPeek?: boolean
}

export function QueryPage({ isPeek = false }: QueryPageProps) {
  const [question, setQuestion] = useState("")
  const [queryState, setQueryState] = useState<QueryState>("idle")
  const [errorMessage, setErrorMessage] = useState("")
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [resultsExpanded, setResultsExpanded] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim()) return

    setQueryState("loading")
    setResult(null)
    setErrorMessage("")
    setResultsExpanded(false)

    try {
      const response = await submitQuery({ question: question.trim() })
      if (typeof response === "string") throw new Error("Invalid API response")
      setResult(response)
      setQueryState("success")
    } catch (error) {
      setQueryState("error")
      setErrorMessage(error instanceof Error ? error.message : "Query failed")
    }
  }

  const columns = result?.data?.length ? Object.keys(result.data[0]) : []

  return (
    <div className={`flex flex-col gap-8 ${isPeek ? "p-8" : "mx-auto max-w-6xl px-4 py-12"}`}>
      {/* Search Section */}
      <section className="space-y-6 text-center">
        {!isPeek && (
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Ask your data anything.</h1>
            <p className="text-lg text-muted-foreground">TinyBI translates your natural language into powerful insights.</p>
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="relative mx-auto max-w-3xl">
          <div className="relative group">
            <div className="absolute inset-0 -m-1 rounded-[2rem] bg-gradient-to-r from-primary/20 to-primary/10 opacity-0 blur-xl transition-opacity group-focus-within:opacity-100" />
            <div className="relative flex items-center gap-3 rounded-[1.5rem] border border-border bg-card p-2 shadow-sm transition-all focus-within:ring-2 focus-within:ring-primary/20">
              <Search className="ml-4 size-5 text-muted-foreground" />
              <Input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="How many orders were placed last month in Germany?"
                className="flex-1 border-none bg-transparent text-lg shadow-none focus-visible:ring-0"
                disabled={queryState === "loading"}
              />
              <Button 
                type="submit" 
                size="lg"
                disabled={queryState === "loading" || !question.trim()}
                className="rounded-xl px-6"
              >
                {queryState === "loading" ? <Send className="animate-pulse" /> : "Submit"}
              </Button>
            </div>
          </div>
        </form>
      </section>

      {/* Results Section */}
      <AnimatePresence mode="wait">
        {queryState === "loading" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20 gap-4"
          >
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  animate={{ scale: [1, 1.5, 1], opacity: [0.3, 1, 0.3] }}
                  transition={{ repeat: Infinity, duration: 1, delay: i * 0.2 }}
                  className="size-3 rounded-full bg-primary"
                />
              ))}
            </div>
            <p className="text-sm font-medium text-muted-foreground animate-pulse">Consulting the oracle...</p>
          </motion.div>
        )}

        {queryState === "error" && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-2xl border border-destructive/20 bg-destructive/5 p-6 text-center"
          >
            <p className="text-destructive font-medium">{errorMessage}</p>
          </motion.div>
        )}

        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid gap-6 lg:grid-cols-2"
          >
            {/* SQL Pane */}
            <Card className="overflow-hidden border-border bg-card/50">
              <CardHeader className="flex flex-row items-center gap-2 border-b border-border/50 py-3">
                <Code className="size-4 text-primary" />
                <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Generated SQL</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <pre className="p-6 font-mono text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                  {result.sql}
                </pre>
              </CardContent>
            </Card>

            {/* Explanation Pane */}
            <Card className="overflow-hidden border-border bg-card/50">
              <CardHeader className="flex flex-row items-center gap-2 border-b border-border/50 py-3">
                <Sparkles className="size-4 text-primary" />
                <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">AI Insight</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <p className="text-sm leading-relaxed text-muted-foreground italic">
                  {result.explanation || "No additional insights provided."}
                </p>
              </CardContent>
            </Card>

            {/* Data Table */}
            <Card className="lg:col-span-2 overflow-hidden border-border">
              <CardHeader className="flex flex-row items-center justify-between gap-2 border-b border-border/50 py-4">
                <div className="flex items-center gap-2">
                  <TableIcon className="size-4 text-primary" />
                  <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Results</CardTitle>
                </div>
                <Badge variant="secondary">{result.data.length} Rows</Badge>
              </CardHeader>
              <CardContent className="p-0">
                <div className={`overflow-auto ${resultsExpanded ? "" : "max-h-[400px]"}`}>
                  <Table>
                    <TableHeader className="bg-muted/30">
                      <TableRow>
                        {columns.map((col) => (
                          <TableHead key={col} className="font-bold text-foreground">{col}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.data.map((row, i) => (
                        <TableRow key={i} className="hover:bg-muted/20">
                          {columns.map((col) => (
                            <TableCell key={col}>{String(row[col] ?? "")}</TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                {result.data.length > 10 && (
                  <div className="flex justify-center p-4 border-t border-border/50">
                    <Button variant="ghost" size="sm" onClick={() => setResultsExpanded(!resultsExpanded)}>
                      {resultsExpanded ? <><ChevronUp className="mr-2" /> Show Less</> : <><ChevronDown className="mr-2" /> Show All Rows</>}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
