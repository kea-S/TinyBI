import { useState } from "react"
import {
  Download,
  ArrowLeft,
  BookCopy,
  Braces,
  Database,
  Layers3,
  Plus,
  Save,
  Send,
  Trash2,
} from "lucide-react"

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
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import {
  fetchCurrentVectorIndexEntries,
  submitDefaultVectorIndexEntries,
  type BatchColumnVectorIndexResponse,
  type ColumnVectorIndexEntryRequest,
} from "@/lib/api"

type TableDraft = {
  id: string
  name: string
  columns: ColumnDraft[]
}

type ColumnDraft = {
  id: string
  columnName: string
  sourceKey: string
  description: string
  dataFormat: string
  aliasesText: string
  sampleValuesText: string
  payloadText: string
}

type SubmitState = "idle" | "submitting" | "success" | "error"
type LoadState = "idle" | "loading" | "error"

const defaultPayloadText = '{\n  "is_groupable": true\n}'

function sanitisePayload(payload: Record<string, unknown> | null | undefined) {
  if (!payload || Array.isArray(payload)) {
    return {}
  }

  const { data_type: _legacyDataType, ...rest } = payload
  return rest
}

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
    aliasesText: "",
    sampleValuesText: "",
    payloadText: defaultPayloadText,
  }
}

function createEmptyTable(): TableDraft {
  return {
    id: createId("table"),
    name: "",
    columns: [createEmptyColumn()],
  }
}

function parseCommaSeparatedList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

function buildTablesFromEntries(entries: ColumnVectorIndexEntryRequest[]): TableDraft[] {
  const tablesByName = new Map<string, TableDraft>()

  for (const entry of entries) {
    const existingTable = tablesByName.get(entry.table_name)
    const table =
      existingTable ??
      {
        id: createId("table"),
        name: entry.table_name,
        columns: [],
      }

    table.columns.push({
      id: createId("column"),
      columnName: entry.column_name,
      sourceKey: entry.source_key,
      description: entry.description ?? "",
      dataFormat: entry.data_format ?? "",
      aliasesText: entry.aliases.join(", "),
      sampleValuesText: entry.sample_values.join(", "),
      payloadText: JSON.stringify(sanitisePayload(entry.payload), null, 2),
    })

    tablesByName.set(entry.table_name, table)
  }

  const tables = [...tablesByName.values()]
  return tables.length > 0 ? tables : [createEmptyTable()]
}

type VectorIndexBuilderPageProps = {
  onBackToDashboard: () => void
}

export function VectorIndexBuilderPage({
  onBackToDashboard,
}: VectorIndexBuilderPageProps) {
  const [tables, setTables] = useState<TableDraft[]>([createEmptyTable()])
  const [selectedTableId, setSelectedTableId] = useState(tables[0].id)
  const [selectedColumnId, setSelectedColumnId] = useState(tables[0].columns[0].id)
  const [submitState, setSubmitState] = useState<SubmitState>("idle")
  const [loadState, setLoadState] = useState<LoadState>("idle")
  const [submitMessage, setSubmitMessage] = useState(
    "No batch submitted yet. Build out your tables and linked columns first."
  )
  const [submitResponse, setSubmitResponse] =
    useState<BatchColumnVectorIndexResponse | null>(null)

  const selectedTable =
    tables.find((table) => table.id === selectedTableId) ?? tables[0] ?? null
  const selectedColumn =
    selectedTable?.columns.find((column) => column.id === selectedColumnId) ??
    selectedTable?.columns[0] ??
    null

  function ensureSelectedIds(nextTables: TableDraft[]) {
    const nextSelectedTable =
      nextTables.find((table) => table.id === selectedTableId) ?? nextTables[0] ?? null
    const nextSelectedColumn =
      nextSelectedTable?.columns.find((column) => column.id === selectedColumnId) ??
      nextSelectedTable?.columns[0] ??
      null

    setSelectedTableId(nextSelectedTable?.id ?? "")
    setSelectedColumnId(nextSelectedColumn?.id ?? "")
  }

  function updateTables(updater: (current: TableDraft[]) => TableDraft[]) {
    setTables((current) => {
      const nextTables = updater(current)
      ensureSelectedIds(nextTables)
      return nextTables
    })
  }

  function handleAddTable() {
    const newTable = createEmptyTable()
    setTables((current) => [...current, newTable])
    setSelectedTableId(newTable.id)
    setSelectedColumnId(newTable.columns[0].id)
  }

  function handleRemoveTable(tableId: string) {
    updateTables((current) => {
      if (current.length === 1) {
        return [createEmptyTable()]
      }

      return current.filter((table) => table.id !== tableId)
    })
  }

  function handleUpdateTableName(tableId: string, name: string) {
    updateTables((current) =>
      current.map((table) => (table.id === tableId ? { ...table, name } : table))
    )
  }

  function handleAddColumn(tableId: string) {
    const newColumn = createEmptyColumn()
    updateTables((current) =>
      current.map((table) =>
        table.id === tableId
          ? { ...table, columns: [...table.columns, newColumn] }
          : table
      )
    )
    setSelectedTableId(tableId)
    setSelectedColumnId(newColumn.id)
  }

  function handleRemoveColumn(tableId: string, columnId: string) {
    updateTables((current) =>
      current.map((table) => {
        if (table.id !== tableId) {
          return table
        }

        if (table.columns.length === 1) {
          return { ...table, columns: [createEmptyColumn()] }
        }

        return {
          ...table,
          columns: table.columns.filter((column) => column.id !== columnId),
        }
      })
    )
  }

  function updateColumnField(
    tableId: string,
    columnId: string,
    field: keyof ColumnDraft,
    value: string
  ) {
    updateTables((current) =>
      current.map((table) => {
        if (table.id !== tableId) {
          return table
        }

        return {
          ...table,
          columns: table.columns.map((column) =>
            column.id === columnId ? { ...column, [field]: value } : column
          ),
        }
      })
    )
  }

  function buildRequestEntries() {
    const entries: ColumnVectorIndexEntryRequest[] = []
    let nextEntryId = 1

    for (const table of tables) {
      const tableName = table.name.trim()
      if (!tableName) {
        throw new Error("Each table needs a name before you can submit the index batch.")
      }

      for (const column of table.columns) {
        const columnName = column.columnName.trim()
        if (!columnName) {
          throw new Error(`Table "${tableName}" has a column without a column name.`)
        }

        let payload: Record<string, unknown> = {}
        const trimmedPayload = column.payloadText.trim()
        if (trimmedPayload) {
          try {
            const parsedPayload = JSON.parse(trimmedPayload) as unknown
            if (
              !parsedPayload ||
              Array.isArray(parsedPayload) ||
              typeof parsedPayload !== "object"
            ) {
              throw new Error("Payload must be a JSON object.")
            }
            payload = sanitisePayload(parsedPayload as Record<string, unknown>)
          } catch (error) {
            if (error instanceof Error && error.message === "Payload must be a JSON object.") {
              throw error
            }

            throw new Error(
              `Payload JSON is invalid for ${tableName}.${columnName}.`
            )
          }
        }

        const sourceKey =
          column.sourceKey.trim() || `${tableName}.${columnName}`

        entries.push({
          entry_id: nextEntryId,
          table_name: tableName,
          column_name: columnName,
          source_key: sourceKey,
          description: column.description.trim() || null,
          data_format: column.dataFormat.trim() || null,
          aliases: parseCommaSeparatedList(column.aliasesText),
          sample_values: parseCommaSeparatedList(column.sampleValuesText),
          payload,
        })

        nextEntryId += 1
      }
    }

    if (entries.length === 0) {
      throw new Error("Add at least one column entry before submitting.")
    }

    return entries
  }

  async function handleSubmit() {
    setSubmitState("submitting")
    setSubmitResponse(null)

    try {
      const entries = buildRequestEntries()
      const response = await submitDefaultVectorIndexEntries({ entries })

      if (typeof response === "string") {
        throw new Error("Expected a JSON response from the vector index API.")
      }

      setSubmitState("success")
      setSubmitResponse(response)
      setSubmitMessage(
        `Indexed ${response.entry_count} columns across ${response.table_names.length} tables with ${response.embedding_model}.`
      )
    } catch (error) {
      setSubmitState("error")
      setSubmitMessage(
        error instanceof Error ? error.message : "Unable to submit the vector index batch."
      )
    }
  }

  async function handleLoadCurrentIndex() {
    setLoadState("loading")

    try {
      const response = await fetchCurrentVectorIndexEntries()
      if (typeof response === "string") {
        throw new Error("Expected a JSON response when loading the current index.")
      }

      const nextTables = buildTablesFromEntries(response)
      setTables(nextTables)
      setSelectedTableId(nextTables[0]?.id ?? "")
      setSelectedColumnId(nextTables[0]?.columns[0]?.id ?? "")
      setLoadState("idle")

      if (response.length === 0) {
        setSubmitMessage("No persisted index was found yet. You are editing a fresh draft.")
        setSubmitState("idle")
        setSubmitResponse(null)
        return
      }

      setSubmitState("success")
      setSubmitResponse(null)
      setSubmitMessage(`Loaded ${response.length} persisted entries into the editor.`)
    } catch (error) {
      setLoadState("error")
      setSubmitState("error")
      setSubmitMessage(
        error instanceof Error ? error.message : "Unable to load the current vector index."
      )
    }
  }

  const totalColumns = tables.reduce((count, table) => count + table.columns.length, 0)

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <section className="overflow-hidden rounded-[2rem] border border-border/70 bg-card/88 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-5 px-6 py-6 lg:flex-row lg:items-end lg:justify-between lg:px-8">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="ghost" size="sm" onClick={onBackToDashboard}>
                <ArrowLeft />
                Dashboard
              </Button>
              <Badge variant="outline" className="rounded-full px-3 py-1">
                Default embedder
              </Badge>
              <Badge className="rounded-full px-3 py-1">nomic-embed-text</Badge>
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                Build column vectors by table, then submit one batch.
              </h1>
              <p className="max-w-3xl text-base leading-7 text-muted-foreground">
                Create a table on the left, attach linked columns on the right, and send
                the flattened `ColumnVectorIndexEntry` list to the default FastAPI endpoint
                once the draft is complete.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-2xl border border-border/80 bg-background/70 px-4 py-3 text-sm text-muted-foreground">
              {tables.length} tables · {totalColumns} columns
            </div>
            <Button
              variant="outline"
              onClick={handleLoadCurrentIndex}
              disabled={loadState === "loading"}
            >
              <Download />
              {loadState === "loading" ? "Loading current index" : "Load current index"}
            </Button>
            <Button onClick={handleSubmit} disabled={submitState === "submitting"}>
              {submitState === "submitting" ? <Save className="animate-pulse" /> : <Send />}
              Submit index batch
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)_360px]">
        <Card className="border-border/70 bg-card/82">
          <CardHeader>
            <CardTitle>Tables</CardTitle>
            <CardDescription>
              Each table groups the columns that will later flatten into index entries.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button className="w-full justify-center" variant="outline" onClick={handleAddTable}>
              <Plus />
              Add table
            </Button>
            <div className="space-y-3">
              {tables.map((table, index) => {
                const isSelected = table.id === selectedTableId

                return (
                  <button
                    key={table.id}
                    type="button"
                    onClick={() => {
                      setSelectedTableId(table.id)
                      setSelectedColumnId(table.columns[0]?.id ?? "")
                    }}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      isSelected
                        ? "border-primary/40 bg-primary/8 shadow-sm"
                        : "border-border/80 bg-background/55 hover:bg-muted/55"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                          Table {index + 1}
                        </p>
                        <p className="font-medium text-foreground">
                          {table.name.trim() || "Untitled table"}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {table.columns.length} linked column
                          {table.columns.length === 1 ? "" : "s"}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={(event) => {
                          event.stopPropagation()
                          handleRemoveTable(table.id)
                        }}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </button>
                )
              })}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/82">
          <CardHeader className="gap-4 border-b border-border/70 pb-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="flex items-center gap-2">
                  <Database className="size-4" />
                  Table workspace
                </CardTitle>
                <CardDescription>
                  Pick a table, define its name, then edit the linked column metadata below.
                </CardDescription>
              </div>
              {selectedTable ? (
                <Button variant="outline" size="sm" onClick={() => handleAddColumn(selectedTable.id)}>
                  <Plus />
                  Add column
                </Button>
              ) : null}
            </div>

            {selectedTable ? (
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px]">
                <label className="space-y-2">
                  <span className="text-sm font-medium text-foreground">Table name</span>
                  <Input
                    value={selectedTable.name}
                    onChange={(event) =>
                      handleUpdateTableName(selectedTable.id, event.target.value)
                    }
                    placeholder="orders"
                  />
                </label>
                <div className="rounded-2xl border border-dashed border-border/80 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                  Every column in this table inherits the same `table_name` when the batch is built.
                </div>
              </div>
            ) : null}
          </CardHeader>

          <CardContent className="space-y-6 pt-5">
            {selectedTable ? (
              <>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-foreground">Columns for this table</p>
                      <p className="text-sm text-muted-foreground">
                        Select a column to edit its `ColumnVectorIndexEntry` fields.
                      </p>
                    </div>
                    <Badge variant="outline">{selectedTable.columns.length} total</Badge>
                  </div>

                  <div className="grid gap-2 md:grid-cols-2">
                    {selectedTable.columns.map((column, index) => {
                      const isSelected = column.id === selectedColumnId

                      return (
                        <button
                          key={column.id}
                          type="button"
                          onClick={() => setSelectedColumnId(column.id)}
                          className={`rounded-2xl border p-3 text-left transition ${
                            isSelected
                              ? "border-primary/40 bg-primary/8"
                              : "border-border/80 bg-background/60 hover:bg-muted/50"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                                Column {index + 1}
                              </p>
                              <p className="font-medium text-foreground">
                                {column.columnName.trim() || "Untitled column"}
                              </p>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={(event) => {
                                event.stopPropagation()
                                handleRemoveColumn(selectedTable.id, column.id)
                              }}
                            >
                              <Trash2 />
                            </Button>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>

                <Separator />

                {selectedColumn ? (
                  <div className="space-y-5">
                    <div className="space-y-1">
                      <p className="text-lg font-medium text-foreground">Selected column</p>
                      <p className="text-sm text-muted-foreground">
                        This form maps directly to a `ColumnVectorIndexEntry` once submitted.
                      </p>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="space-y-2">
                        <span className="text-sm font-medium">Column name</span>
                        <Input
                          value={selectedColumn.columnName}
                          onChange={(event) =>
                            updateColumnField(
                              selectedTable.id,
                              selectedColumn.id,
                              "columnName",
                              event.target.value
                            )
                          }
                          placeholder="customer_city"
                        />
                      </label>
                      <label className="space-y-2">
                        <span className="text-sm font-medium">Source key</span>
                        <Input
                          value={selectedColumn.sourceKey}
                          onChange={(event) =>
                            updateColumnField(
                              selectedTable.id,
                              selectedColumn.id,
                              "sourceKey",
                              event.target.value
                            )
                          }
                          placeholder={
                            selectedTable.name && selectedColumn.columnName
                              ? `${selectedTable.name}.${selectedColumn.columnName}`
                              : "orders.customer_city"
                          }
                        />
                      </label>
                    </div>

                    <label className="space-y-2">
                      <span className="text-sm font-medium">Data format</span>
                      <Input
                        value={selectedColumn.dataFormat}
                        onChange={(event) =>
                          updateColumnField(
                            selectedTable.id,
                            selectedColumn.id,
                            "dataFormat",
                            event.target.value
                          )
                        }
                        placeholder="date, currency, percentage, iso_country_code"
                      />
                    </label>

                    <label className="space-y-2">
                      <span className="text-sm font-medium">Description</span>
                      <Textarea
                        value={selectedColumn.description}
                        onChange={(event) =>
                          updateColumnField(
                            selectedTable.id,
                            selectedColumn.id,
                            "description",
                            event.target.value
                          )
                        }
                        placeholder="City where the customer received the parcel."
                        className="min-h-28"
                      />
                    </label>

                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="space-y-2">
                        <span className="text-sm font-medium">Aliases</span>
                        <Input
                          value={selectedColumn.aliasesText}
                          onChange={(event) =>
                            updateColumnField(
                              selectedTable.id,
                              selectedColumn.id,
                              "aliasesText",
                              event.target.value
                            )
                          }
                          placeholder="city, customer city, destination city"
                        />
                      </label>
                      <label className="space-y-2">
                        <span className="text-sm font-medium">Sample values</span>
                        <Input
                          value={selectedColumn.sampleValuesText}
                          onChange={(event) =>
                            updateColumnField(
                              selectedTable.id,
                              selectedColumn.id,
                              "sampleValuesText",
                              event.target.value
                            )
                          }
                          placeholder="Berlin, Munich, Warsaw"
                        />
                      </label>
                    </div>

                    <label className="space-y-2">
                      <span className="flex items-center gap-2 text-sm font-medium">
                        <Braces className="size-4" />
                        Payload JSON
                      </span>
                      <Textarea
                        value={selectedColumn.payloadText}
                        onChange={(event) =>
                          updateColumnField(
                            selectedTable.id,
                            selectedColumn.id,
                            "payloadText",
                            event.target.value
                          )
                        }
                        className="min-h-40 font-mono text-sm"
                        spellCheck={false}
                      />
                    </label>
                  </div>
                ) : null}
              </>
            ) : (
              <div className="rounded-2xl border border-dashed border-border/80 bg-muted/40 p-6 text-sm text-muted-foreground">
                Add a table to start building the index batch.
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-border/70 bg-card/82">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers3 className="size-4" />
                Batch preview
              </CardTitle>
              <CardDescription>
                Submission always goes to the default backend route and uses the current default embedder.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-2xl border border-border/80 bg-muted/45 p-4">
                  <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                    API target
                  </p>
                  <p className="mt-2 font-medium text-foreground">
                    POST /vector/index-entries/batch
                  </p>
                </div>
                <div className="rounded-2xl border border-border/80 bg-muted/45 p-4">
                  <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                    Generated entries
                  </p>
                  <p className="mt-2 font-medium text-foreground">{totalColumns}</p>
                </div>
                <div className="rounded-2xl border border-border/80 bg-muted/45 p-4">
                  <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                    Recovery flow
                  </p>
                  <p className="mt-2 font-medium text-foreground">
                    Load current index, edit, then resubmit the whole batch
                  </p>
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                {tables.map((table) => (
                  <div key={table.id} className="rounded-2xl border border-border/70 bg-background/65 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-foreground">
                        {table.name.trim() || "Untitled table"}
                      </p>
                      <Badge variant="outline">{table.columns.length} columns</Badge>
                    </div>
                    <div className="mt-3 space-y-2">
                      {table.columns.map((column) => (
                        <div key={column.id} className="rounded-xl bg-muted/45 px-3 py-2 text-sm text-muted-foreground">
                          {(column.columnName || "Untitled column").trim() || "Untitled column"}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-card/82">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookCopy className="size-4" />
                Submission status
              </CardTitle>
              <CardDescription>
                Backend response after the batch is flattened and posted.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Badge
                variant={
                  submitState === "success"
                    ? "default"
                    : submitState === "error"
                      ? "destructive"
                      : "outline"
                }
              >
                {submitState}
              </Badge>
              <div className="rounded-2xl bg-muted px-4 py-3 text-sm leading-6 text-muted-foreground">
                {submitMessage}
              </div>
              {submitResponse ? (
                <pre className="overflow-auto rounded-2xl bg-muted px-4 py-3 text-sm leading-6 whitespace-pre-wrap text-muted-foreground">
                  {JSON.stringify(submitResponse, null, 2)}
                </pre>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  )
}

