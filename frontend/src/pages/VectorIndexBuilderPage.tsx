import React, { useState, useCallback, useEffect, useRef } from "react"
import {
  ReactFlow,
  Controls,
  Background,
  ReactFlowProvider,
  useReactFlow,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  Panel,
  MarkerType,
  type Connection,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { motion, AnimatePresence } from "framer-motion"
import { 
  Plus, 
  Save, 
  Loader2,
  Trash2, 
  X, 
  Search, 
  Database, 
  Braces,
  Layout
} from "lucide-react"
import ELK, { type ElkNode, type ElkExtendedEdge } from "elkjs/lib/elk.bundled.js"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { TableNode, type TableNodeData } from "@/components/builder/TableNode"
import { type TableDraft, type ColumnDraft } from "@/App"
import { 
  submitDefaultVectorIndexEntries, 
  fetchCurrentVectorIndexEntries,
  type ColumnVectorIndexEntryRequest 
} from "@/lib/api"
import { QueryPage } from "./QueryPage"

const elk = new ELK()

const nodeTypes = {
  table: TableNode,
}



type VectorIndexBuilderPageProps = {
  tables: TableDraft[]
  setTables: React.Dispatch<React.SetStateAction<TableDraft[]>>
  isVisible?: boolean
}

function VectorIndexBuilderPageInner({ tables, setTables, isVisible }: VectorIndexBuilderPageProps) {
  const { fitView } = useReactFlow()
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null)
  const [selectedColumnId, setSelectedColumnId] = useState<string | null>(null)
  const [isPeekOpen, setIsPeekOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [syncedEntries, setSyncedEntries] = useState<ColumnVectorIndexEntryRequest[]>([])
  const [isReady, setIsReady] = useState(false)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const selectedEdgeIdRef = useRef<string | null>(null)
  const edgesRef = useRef<Edge[]>([])
  const [pendingDeletions, setPendingDeletions] = useState<Set<string>>(new Set())

  // Fetch current state to determine "synced" status for edges
  useEffect(() => {
    fetchCurrentVectorIndexEntries().then((res) => {
      if (Array.isArray(res)) setSyncedEntries(res)
    })
  }, [])

  // Auto-layout + fitView the first time the builder tab becomes visible with data
  const hasAutoLayouted = useRef(false)
  useEffect(() => {
    if (!hasAutoLayouted.current && isVisible && tables.length > 1 && syncedEntries.length > 0) {
      hasAutoLayouted.current = true
      handleAutoLayout(tables).then(() => {
        setTimeout(() => {
          fitView({ padding: 0.2 })
          setIsReady(true)
        }, 150)
      })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isVisible, tables, syncedEntries, fitView])

  // Global Delete key handler for edge deletion — uses refs to avoid re-registration
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const currentEdgeId = selectedEdgeIdRef.current
      if (!currentEdgeId) return
      if (event.key !== "Delete" && event.key !== "Backspace") return
      const edge = edgesRef.current.find((e) => e.id === currentEdgeId)
      if (edge?.sourceHandle) {
        const sourceColId = edge.sourceHandle.replace("-source", "")
        setPendingDeletions((prev) => {
          const next = new Set(prev)
          if (next.has(sourceColId)) {
            next.delete(sourceColId)
          } else {
            next.add(sourceColId)
          }
          return next
        })
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  // Derived state prototype
  const nodes = React.useMemo<Node<TableNodeData>[]>(() => {
    return tables.map((t) => ({
      id: t.id,
      type: "table",
      position: { x: t.x ?? 0, y: t.y ?? 0 },
      data: {
        name: t.name,
        columns: t.columns.map((c) => ({ id: c.id, columnName: c.columnName })),
        isSelected: selectedTableId === t.id,
      },
    }))
  }, [tables, selectedTableId])

  const edges = React.useMemo<Edge[]>(() => {
    const newEdges: Edge[] = []
    tables.forEach((t) => {
      t.columns.forEach((c) => {
        if (c.references) {
          const [refTable, refCol] = c.references.split(".")
          const targetTable = tables.find((tab) => tab.name === refTable)
          if (targetTable) {
            const targetColumn = targetTable.columns.find((col) => col.columnName === refCol)
            if (targetColumn) {
              const edgeId = `edge-${c.id}-${targetColumn.id}`
              const isDeleted = pendingDeletions.has(c.id)
              const isSynced = syncedEntries.some(
                (se) => se.table_name === t.name &&
                  se.column_name === c.columnName &&
                  se.references === c.references
              )

              if (isDeleted) {
                newEdges.push({
                  id: edgeId,
                  source: t.id,
                  sourceHandle: `${c.id}-source`,
                  target: targetTable.id,
                  targetHandle: `${targetColumn.id}-target`,
                  reconnectable: false,
                  selected: selectedEdgeId === edgeId,
                  animated: true,
                  style: {
                    stroke: "#ef4444",
                    strokeDasharray: "5,5",
                    strokeWidth: 4,
                  },
                  markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: "#ef4444",
                  },
                })
              } else {
                newEdges.push({
                  id: edgeId,
                  source: t.id,
                  sourceHandle: `${c.id}-source`,
                  target: targetTable.id,
                  targetHandle: `${targetColumn.id}-target`,
                  reconnectable: true,
                  selected: selectedEdgeId === edgeId,
                  animated: !isSynced,
                  style: {
                    stroke: isSynced ? "#0f172a" : "#94a3b8",
                    strokeDasharray: isSynced ? "" : "5,5",
                    strokeWidth: 4,
                  },
                  markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: isSynced ? "#0f172a" : "#94a3b8",
                  },
                })
              }
            }
          }
        }
      })
    })
    return newEdges
  }, [tables, syncedEntries, selectedEdgeId, pendingDeletions])

  useEffect(() => {
    edgesRef.current = edges
  }, [edges])

  const onNodesChange: OnNodesChange<Node<TableNodeData>> = useCallback(
    (changes) => {
      changes.forEach((change) => {
        if (change.type === "position" && change.position) {
          setTables((current) =>
            current.map((t) =>
              t.id === change.id ? { ...t, x: change.position!.x, y: change.position!.y } : t
            )
          )
        }
      })
    },
    [setTables]
  )

  const onEdgesChange: OnEdgesChange = useCallback(
    () => {
      // no-op, handled by derived state
    },
    []
  )

  const onConnect: OnConnect = useCallback(
    (connection) => {
      const sourceTable = tables.find((t) => t.id === connection.source)
      const targetTable = tables.find((t) => t.id === connection.target)

      if (sourceTable && targetTable && connection.sourceHandle && connection.targetHandle) {
        // IDs are simple colId-source or colId-target
        const sourceColId = connection.sourceHandle.replace("-source", "")
        const targetColId = connection.targetHandle.replace("-target", "")

        const targetCol = targetTable.columns.find((c) => c.id === targetColId)

        if (targetCol) {
          setTables((current) =>
            current.map((t) => {
              if (t.id !== sourceTable.id) return t
              return {
                ...t,
                columns: t.columns.map((c) =>
                  c.id === sourceColId ? { ...c, references: `${targetTable.name}.${targetCol.columnName}` } : c
                ),
              }
            })
          )
        }
      }
    },
    [tables, setTables]
  )

  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      const newSourceTable = tables.find((t) => t.id === newConnection.source)
      const newTargetTable = tables.find((t) => t.id === newConnection.target)

      if (
        !newSourceTable ||
          !newTargetTable ||
          !newConnection.sourceHandle ||
          !newConnection.targetHandle
      )
        return

      const oldSourceColId = oldEdge.sourceHandle?.replace("-source", "")
      const newSourceColId = newConnection.sourceHandle.replace("-source", "")
      const newTargetColId = newConnection.targetHandle.replace("-target", "")

      const newTargetCol = newTargetTable.columns.find((c) => c.id === newTargetColId)
      if (!newTargetCol) return

      const newReference = `${newTargetTable.name}.${newTargetCol.columnName}`

      // Block if another column on the same source table already references this target.
      // Exclude the old source column since it will be cleared.
      const isSameTable = oldEdge.source === newConnection.source
      const wouldDuplicate = newSourceTable.columns.some(
        (c) =>
          c.id !== newSourceColId &&
            !(isSameTable && c.id === oldSourceColId) &&
            c.references === newReference
      )
      if (wouldDuplicate) return

      setTables((current) =>
        current.map((t) => {
          if (t.id === oldEdge.source && oldSourceColId) {
            // Clear old source column reference
            t = {
              ...t,
              columns: t.columns.map((c) =>
                c.id === oldSourceColId ? { ...c, references: "" } : c
              ),
            }
          }
          if (t.id === newConnection.source) {
            // Set new source column reference
            t = {
              ...t,
              columns: t.columns.map((c) =>
                c.id === newSourceColId ? { ...c, references: newReference } : c
              ),
            }
          }
          return t
        })
      )
    },
    [tables, setTables]
  )

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setIsPeekOpen(false) // Mutex: Close peek when selecting table
    setSelectedEdgeId(null)
    selectedEdgeIdRef.current = null
    setSelectedTableId(node.id)
    const table = tables.find(t => t.id === node.id)
    if (table && table.columns.length > 0) {
      setSelectedColumnId(table.columns[0].id)
    }
  }, [tables])

  const onPaneClick = useCallback(() => {
    setSelectedEdgeId(null)
    selectedEdgeIdRef.current = null
  }, [])

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedTableId(null)
    setSelectedColumnId(null)
    setSelectedEdgeId(edge.id)
    selectedEdgeIdRef.current = edge.id
  }, [])

  const handleAddTable = () => {
    const id = `table-${Math.random().toString(36).slice(2, 10)}`
    const newTable: TableDraft = {
      id,
      name: "new_table",
      x: Math.random() * 400,
      y: Math.random() * 400,
      columns: [
        {
          id: `column-${Math.random().toString(36).slice(2, 10)}`,
          columnName: "id",
          sourceKey: "",
          description: "",
          dataFormat: "",
          statisticalType: "identifier",
          categoricalValues: [],
          aliasesText: "",
          sampleValuesText: "",
          payloadText: '{\n  "is_groupable": false\n}',
          references: "",
        },
      ],
    }
    setTables((current) => [...current, newTable])
    setSelectedTableId(id)
    setSelectedColumnId(newTable.columns[0].id)
  }

  const handleDeleteTable = (id: string) => {
    setTables((current) => current.filter(t => t.id !== id))
    if (selectedTableId === id) {
      setSelectedTableId(null)
      setSelectedColumnId(null)
    }
  }

  const selectedTable = tables.find((t) => t.id === selectedTableId)
  const selectedColumn = selectedTable?.columns.find((c) => c.id === selectedColumnId)

  const handleUpdateColumn = (field: keyof ColumnDraft, value: string) => {
    if (!selectedTableId || !selectedColumnId) return
    setTables((current) =>
      current.map((t) => {
        if (t.id !== selectedTableId) return t
        return {
          ...t,
          columns: t.columns.map((c) =>
            c.id === selectedColumnId ? { ...c, [field]: value } : c
          ),
        }
      })
    )
  }

  const handleAddCategoricalValue = () => {
    if (!selectedTableId || !selectedColumnId) return
    const id = `cat-${Math.random().toString(36).slice(2, 10)}`
    setTables((current) =>
      current.map((t) => {
        if (t.id !== selectedTableId) return t
        return {
          ...t,
          columns: t.columns.map((c) =>
            c.id === selectedColumnId
              ? { ...c, categoricalValues: [...c.categoricalValues, { id, dbValue: "", synonymsText: "" }] }
              : c
          ),
        }
      })
    )
  }

  const handleUpdateCategoricalValue = (catId: string, field: "dbValue" | "synonymsText", value: string) => {
    if (!selectedTableId || !selectedColumnId) return
    setTables((current) =>
      current.map((t) => {
        if (t.id !== selectedTableId) return t
        return {
          ...t,
          columns: t.columns.map((c) =>
            c.id === selectedColumnId
              ? {
                  ...c,
                  categoricalValues: c.categoricalValues.map((cv) =>
                    cv.id === catId ? { ...cv, [field]: value } : cv
                  ),
                }
              : c
          ),
        }
      })
    )
  }

  const handleDeleteCategoricalValue = (catId: string) => {
    if (!selectedTableId || !selectedColumnId) return
    setTables((current) =>
      current.map((t) => {
        if (t.id !== selectedTableId) return t
        return {
          ...t,
          columns: t.columns.map((c) =>
            c.id === selectedColumnId
              ? { ...c, categoricalValues: c.categoricalValues.filter((cv) => cv.id !== catId) }
              : c
          ),
        }
      })
    )
  }

  async function handleAutoLayout(targetTables: TableDraft[]) {
    const elkNodes: ElkNode[] = targetTables.map((t) => ({
      id: t.id,
      width: 250,
      height: 100 + (t.columns.length * 40),
    }))

    const elkEdges: ElkExtendedEdge[] = []
    targetTables.forEach((t) => {
      t.columns.forEach((c) => {
        if (c.references) {
          const refTable = c.references.split(".")[0]
          const targetTable = targetTables.find((tab) => tab.name === refTable)
          if (targetTable) {
            elkEdges.push({
              id: `elk-edge-${c.id}`,
              sources: [t.id],
              targets: [targetTable.id],
            })
          }
        }
      })
    })

    const graph = await elk.layout({
      id: "root",
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": "RIGHT",
        "elk.spacing.nodeNode": "100",
        "elk.layered.spacing.edgeNodeBetweenLayers": "100",
      },
      children: elkNodes,
      edges: elkEdges,
    })

    if (graph.children) {
      setTables((current) => {
        const next = current.map((t) => {
          const node = graph.children?.find((n) => n.id === t.id)
          if (node && node.x !== undefined && node.y !== undefined) {
            return { ...t, x: node.x, y: node.y }
          }
          return t
        })
        return next
      })
    }
  }

  const handleSaveIndex = async () => {
    setIsSubmitting(true)
    try {
      // Apply pending deletions before building entries
      let tablesToSave = tables
      if (pendingDeletions.size > 0) {
        tablesToSave = tables.map((t) => ({
          ...t,
          columns: t.columns.map((c) =>
            pendingDeletions.has(c.id) ? { ...c, references: "" } : c
          ),
        }))
        setTables(tablesToSave)
      }

      const entries: ColumnVectorIndexEntryRequest[] = []
      tablesToSave.forEach((t) => {
        t.columns.forEach((c) => {
          entries.push({
            entry_id: entries.length + 1,
            table_name: t.name,
            column_name: c.columnName,
            source_key: c.sourceKey || `${t.name}.${c.columnName}`,
            description: c.description || null,
            data_format: c.dataFormat || null,
            statistical_type: c.statisticalType,
            categorical_values: Object.fromEntries(
              c.categoricalValues
                .filter(cv => cv.dbValue.trim() !== "")
                .map(cv => [
                  cv.dbValue.trim(),
                  cv.synonymsText.split(",").map(s => s.trim()).filter(Boolean),
                ])
            ),
            aliases: c.aliasesText.split(",").map(a => a.trim()).filter(Boolean),
            sample_values: c.sampleValuesText.split(",").map(a => a.trim()).filter(Boolean),
            payload: JSON.parse(c.payloadText),
            references: c.references || null,
          })
        })
      })
      await submitDefaultVectorIndexEntries({ entries })

      // Update local sync state
      setSyncedEntries(entries)

      // Clear pending deletions
      setPendingDeletions(new Set())

      // Trigger auto-layout on save
      await handleAutoLayout(tablesToSave)

      alert("Index saved and layout optimized!")
    } catch (e) {
      console.error(e)
      alert("Failed to save index.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="relative h-full w-full">
      <div
        className={`h-full w-full transition-opacity duration-500 ${
          isReady ? "opacity-100" : "opacity-0"
        }`}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onReconnect={onReconnect}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          connectionLineStyle={{ stroke: "#0f172a", strokeWidth: 3, strokeDasharray: "5,5" }}
          deleteKeyCode={null}
          fitView
        >
        <Background color="#cbd5e1" gap={20} />
        <Controls />
        <Panel position="top-right" style={{ marginRight: (isPeekOpen || selectedTableId) ? 420 : 20 }} className="flex gap-2 transition-all duration-300">
          <Button onClick={handleAddTable} className="shadow-lg shadow-primary/20">
            <Plus className="mr-2 size-4" /> Add Table
          </Button>
          <Button 
            variant="default" 
            onClick={handleSaveIndex} 
            disabled={isSubmitting}
            className="shadow-lg shadow-primary/20"
          >
            {isSubmitting ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Save className="mr-2 size-4" />}
            Save Index
          </Button>
          <Button 
            variant="secondary" 
            onClick={() => {
              setSelectedTableId(null) // Mutex: Close table editor when opening peek
              setIsPeekOpen(true)
            }}
            className="shadow-lg"
          >
            <Search className="mr-2 size-4" /> Peek Query
          </Button>
          <Button variant="outline" size="icon" onClick={() => handleAutoLayout(tables)} title="Auto-Layout">
            <Layout className="size-4" />
          </Button>
        </Panel>
        </ReactFlow>
      </div>

      {/* Right Sidebar Editor */}
      <AnimatePresence>
        {selectedTable && (
          <motion.aside
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: "spring", damping: 20, stiffness: 100 }}
            className="absolute inset-y-0 right-0 z-30 w-[400px] border-l border-border bg-white dark:bg-slate-900 opacity-100 shadow-2xl"
          >
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-border p-6">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Database className="size-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold tracking-tight">Table Editor</h2>
                    <p className="text-xs text-muted-foreground uppercase tracking-widest">Configuration</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10" onClick={() => handleDeleteTable(selectedTable.id)} title="Delete Table">
                    <Trash2 className="size-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => setSelectedTableId(null)}>
                    <X className="size-5" />
                  </Button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-8">
                <div className="space-y-2">
                  <label className="text-sm font-semibold">Table Name</label>
                  <Input 
                    value={selectedTable.name} 
                    onChange={(e) => setTables(current => current.map(t => t.id === selectedTable.id ? { ...t, name: e.target.value } : t))}
                  />
                </div>

                <Separator />

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-semibold">Columns</label>
                    <Button variant="outline" size="sm" onClick={() => {
                      const id = `column-${Math.random().toString(36).slice(2, 10)}`
                      setTables(current => current.map(t => t.id === selectedTable.id ? { ...t, columns: [...t.columns, {
                        id,
                        columnName: "new_column",
                        sourceKey: "",
                        description: "",
                        dataFormat: "",
                        statisticalType: "nominal",
                        categoricalValues: [],
                        aliasesText: "",
                        sampleValuesText: "",
                        payloadText: '{\n  "is_groupable": true\n}',
                        references: "",
                      }]} : t))
                      setSelectedColumnId(id)
                    }}>
                      <Plus className="mr-1 size-3" /> Add
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedTable.columns.map((col) => (
                      <button
                        key={col.id}
                        onClick={() => setSelectedColumnId(col.id)}
                        className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all ${
selectedColumnId === col.id 
? "bg-primary text-primary-foreground" 
: "bg-muted text-muted-foreground hover:bg-muted/80"
}`}
                      >
                        {col.columnName || "Untitled"}
                      </button>
                    ))}
                  </div>
                </div>

                {selectedColumn && (
                  <motion.div 
                    key={selectedColumn.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-6 pt-4"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-primary">Column Settings</h3>
                      <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10" onClick={() => {
                        setTables(current => current.map(t => {
                          if (t.id !== selectedTableId) return t
                          const nextCols = t.columns.filter(c => c.id !== selectedColumnId)
                          return { ...t, columns: nextCols.length > 0 ? nextCols : t.columns }
                        }))
                        setSelectedColumnId(selectedTable.columns.find(c => c.id !== selectedColumnId)?.id ?? null)
                      }}>
                        <Trash2 className="size-4" />
                      </Button>
                    </div>

                    <div className="grid gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-medium uppercase text-muted-foreground" htmlFor="col-name">Column Name</label>
                        <Input 
                          id="col-name"
                          value={selectedColumn.columnName} 
                          onChange={(e) => handleUpdateColumn("columnName", e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-medium uppercase text-muted-foreground" htmlFor="stat-type">Statistical Type</label>
                        <select
                          id="stat-type"
                          value={selectedColumn.statisticalType}
                          onChange={(e) => handleUpdateColumn("statisticalType", e.target.value)}
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                        >
                          <option value="nominal">Nominal (Categorical)</option>
                          <option value="ordinal">Ordinal</option>
                          <option value="categorical">Categorical</option>
                          <option value="temporal">Temporal</option>
                          <option value="identifier">Identifier</option>
                          <option value="continuous">Continuous</option>
                          <option value="discrete">Discrete</option>
                          <option value="quantitative">Quantitative</option>
                        </select>
                      </div>

                      <Separator />

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-medium uppercase text-muted-foreground">Categorical Values</label>
                          <Button variant="outline" size="sm" onClick={handleAddCategoricalValue}>
                            <Plus className="mr-1 size-3" /> Add
                          </Button>
                        </div>
                        {selectedColumn.categoricalValues.length === 0 ? (
                          <p className="text-xs text-muted-foreground italic">No categorical values defined.</p>
                        ) : (
                          <div className="space-y-2 max-h-[180px] overflow-y-auto">
                            {selectedColumn.categoricalValues.map((cv) => (
                              <div key={cv.id} className="flex items-start gap-1.5 rounded-md border border-border bg-muted/30 p-2">
                                <div className="flex-1 space-y-1.5">
                                  <Input
                                    className="h-7 text-xs"
                                    placeholder="DB value"
                                    value={cv.dbValue}
                                    onChange={(e) => handleUpdateCategoricalValue(cv.id, "dbValue", e.target.value)}
                                  />
                                  <Input
                                    className="h-7 text-xs"
                                    placeholder="Synonyms (comma separated)"
                                    value={cv.synonymsText}
                                    onChange={(e) => handleUpdateCategoricalValue(cv.id, "synonymsText", e.target.value)}
                                  />
                                </div>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="mt-0.5 size-6 shrink-0 text-destructive hover:bg-destructive/10"
                                  onClick={() => handleDeleteCategoricalValue(cv.id)}
                                >
                                  <Trash2 className="size-3.5" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      <Separator />

                      <div className="space-y-2">
                        <label className="text-xs font-medium uppercase text-muted-foreground" htmlFor="data-format">Data Format</label>
                        <Input 
                          id="data-format"
                          value={selectedColumn.dataFormat} 
                          onChange={(e) => handleUpdateColumn("dataFormat", e.target.value)}
                          placeholder="e.g. date, currency, iso_country_code"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-medium uppercase text-muted-foreground" htmlFor="ref-fk">References (FK)</label>
                        <select
                          id="ref-fk"
                          value={selectedColumn.references}
                          onChange={(e) => handleUpdateColumn("references", e.target.value)}
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary"
                        >
                          <option value="">No reference</option>
                          {tables.flatMap(t => t.columns.map(c => ({ 
                            label: `${t.name}.${c.columnName}`, 
                            value: `${t.name}.${c.columnName}` 
                          }))).filter(opt => opt.value !== `${selectedTable.name}.${selectedColumn.columnName}`).map(opt => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs font-medium uppercase text-muted-foreground" htmlFor="col-desc">Description</label>
                      <Textarea 
                        id="col-desc"
                        value={selectedColumn.description} 
                        onChange={(e) => handleUpdateColumn("description", e.target.value)}
                        className="min-h-[100px]"
                        placeholder="What is this column for?"
                      />
                    </div>

                    <div className="grid gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-medium uppercase text-muted-foreground" htmlFor="col-aliases">Aliases</label>
                        <Input 
                          id="col-aliases"
                          value={selectedColumn.aliasesText} 
                          onChange={(e) => handleUpdateColumn("aliasesText", e.target.value)}
                          placeholder="city, location"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-medium uppercase text-muted-foreground" htmlFor="col-samples">Sample Values</label>
                        <Input 
                          id="col-samples"
                          value={selectedColumn.sampleValuesText} 
                          onChange={(e) => handleUpdateColumn("sampleValuesText", e.target.value)}
                          placeholder="Berlin, London"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground" htmlFor="col-payload">
                        <Braces className="size-3" /> Payload JSON
                      </label>
                      <Textarea 
                        id="col-payload"
                        value={selectedColumn.payloadText} 
                        onChange={(e) => handleUpdateColumn("payloadText", e.target.value)}
                        className="font-mono text-xs"
                      />
                    </div>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Peek Query Panel */}
      <AnimatePresence>
        {isPeekOpen && (
          <motion.div
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="absolute inset-y-0 right-0 z-50 w-[400px] border-l border-border bg-white dark:bg-slate-900 opacity-100 shadow-2xl overflow-hidden"
          >
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-border bg-muted/30 px-8 py-6">
                <div className="flex items-center gap-3">
                  <Search className="size-5 text-primary" />
                  <h2 className="text-xl font-bold tracking-tight">Peek Query</h2>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setIsPeekOpen(false)}>
                  <X className="size-6" />
                </Button>
              </div>
              <div className="flex-1 overflow-y-auto">
                <QueryPage isPeek />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function VectorIndexBuilderPage(props: VectorIndexBuilderPageProps) {
  return (
    <ReactFlowProvider>
      <VectorIndexBuilderPageInner {...props} />
    </ReactFlowProvider>
  )
}
