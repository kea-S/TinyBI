import { motion, AnimatePresence } from "framer-motion"
import { X, Code, Table as TableIcon } from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"

interface DataModalProps {
  isOpen: boolean
  onClose: () => void
  sql?: string | null
  data?: Record<string, unknown>[] | null
}

export function DataModal({ isOpen, onClose, sql, data }: DataModalProps) {
  if (!isOpen) return null

  const columns = data?.length ? Object.keys(data[0]) : []

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-8 ml-20 bg-background/80 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-5xl max-h-[85vh] overflow-hidden rounded-2xl border border-border bg-card shadow-2xl flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border/50 px-6 py-4">
            <h2 className="text-xl font-bold">Data Inspection</h2>
            <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full">
              <X className="size-5" />
            </Button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 grid lg:grid-cols-2 gap-6">
            {/* SQL Pane */}
            <Card className="flex flex-col border-border bg-muted/20 min-w-0">
              <CardHeader className="flex flex-row items-center gap-2 border-b border-border/50 py-3">
                <Code className="size-4 text-primary" />
                <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">SQL Query</CardTitle>
              </CardHeader>
              <CardContent className="p-0 flex-1 overflow-auto">
                <pre className="p-6 font-mono text-sm leading-relaxed text-foreground whitespace-pre-wrap break-words">
                  {sql || "No SQL available"}
                </pre>
              </CardContent>
            </Card>

            {/* Table Pane */}
            <Card className="flex flex-col border-border min-w-0">
              <CardHeader className="flex flex-row items-center justify-between gap-2 border-b border-border/50 py-3">
                <div className="flex items-center gap-2">
                  <TableIcon className="size-4 text-primary" />
                  <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Result Table</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="p-0 flex-1 overflow-auto">
                {data && data.length > 0 ? (
                  <Table>
                    <TableHeader className="bg-muted/30 sticky top-0">
                      <TableRow>
                        {columns.map((col) => (
                          <TableHead key={col} className="font-bold text-foreground">{col}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.map((row, i) => (
                        <TableRow key={i} className="hover:bg-muted/20">
                          {columns.map((col) => (
                            <TableCell key={col}>{String(row[col] ?? "")}</TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="flex h-40 items-center justify-center text-muted-foreground">
                    No data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
