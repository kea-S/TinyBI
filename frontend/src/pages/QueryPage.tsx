import { useState } from "react"
import { ArrowLeft, Search, Send } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
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
  onBackToDashboard: () => void
}

export function QueryPage({ onBackToDashboard }: QueryPageProps) {
  const [question, setQuestion] = useState("")
  const [queryState, setQueryState] = useState<QueryState>("idle")
  const [errorMessage, setErrorMessage] = useState("")
  const [result, setResult] = useState<QueryResponse | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!question.trim()) return

    setQueryState("loading")
    setResult(null)
    setErrorMessage("")

    try {
      const response = await submitQuery({ question: question.trim() })

      if (typeof response === "string") {
        throw new Error("Expected a JSON response from the query API.")
      }

      setResult(response)
      setQueryState("success")
    } catch (error) {
      setQueryState("error")
      setErrorMessage(
        error instanceof Error ? error.message : "Query failed."
      )
    }
  }

  const columns = result?.data?.length
    ? Object.keys(result.data[0])
    : []

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <section className="overflow-hidden rounded-[2rem] border border-border/70 bg-card/85 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-5 px-6 py-6 lg:flex-row lg:items-end lg:justify-between lg:px-8">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="ghost" size="sm" onClick={onBackToDashboard}>
                <ArrowLeft />
                Dashboard
              </Button>
              <Badge variant="outline" className="rounded-full px-3 py-1">
                Natural language query
              </Badge>
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                Ask a question about your data.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-muted-foreground">
                The query is extracted into a structured schema, resolved against
                the vector index, and executed as SQL against the database.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.9fr)]">
        <Card className="border-border/70 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="size-4" />
              Query
            </CardTitle>
            <CardDescription>
              Enter a natural language question and press Submit.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex gap-3">
              <Input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="average buyer waiting time by provider in Singapore"
                className="flex-1"
                disabled={queryState === "loading"}
              />
              <Button type="submit" disabled={queryState === "loading" || !question.trim()}>
                {queryState === "loading" ? <Send className="animate-pulse" /> : <Send />}
                Submit
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/80">
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-2xl border border-border/80 bg-muted/50 px-4 py-3">
              <span className="text-sm font-medium">State</span>
              <Badge
                variant={
                  queryState === "success"
                    ? "default"
                    : queryState === "error"
                      ? "destructive"
                      : "outline"
                }
              >
                {queryState}
              </Badge>
            </div>
            {errorMessage && (
              <div className="rounded-2xl bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {errorMessage}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {result && (
        <section className="space-y-4">
          <Card className="border-border/70 bg-card/80">
            <CardHeader>
              <CardTitle>Generated SQL</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-auto rounded-2xl bg-muted px-4 py-3 text-sm leading-6 whitespace-pre-wrap text-muted-foreground">
                {result.sql}
              </pre>
            </CardContent>
          </Card>

          {result.data.length > 0 ? (
            <Card className="border-border/70 bg-card/80">
              <CardHeader>
                <CardTitle>Results</CardTitle>
                <CardDescription>
                  {result.data.length} row{result.data.length === 1 ? "" : "s"} returned.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-auto rounded-2xl border border-border/70">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {columns.map((col) => (
                          <TableHead key={col}>{col}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.data.map((row, rowIndex) => (
                        <TableRow key={rowIndex}>
                          {columns.map((col) => (
                            <TableCell key={col}>
                              {String(row[col] ?? "")}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border/70 bg-card/80">
              <CardContent className="py-8 text-center text-muted-foreground">
                Query returned no results.
              </CardContent>
            </Card>
          )}
        </section>
      )}
    </main>
  )
}