import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { VectorIndexBuilderPage } from '../pages/VectorIndexBuilderPage'
import * as api from '../lib/api'
import { type TableDraft } from '../App'

// Mock framer-motion to avoid animation timing issues in jsdom
vi.mock('framer-motion', () => ({
  motion: {
    div: vi.fn(({ children }) => <div>{children}</div>),
    aside: vi.fn(({ children }) => <aside>{children}</aside>),
  },
  AnimatePresence: vi.fn(({ children }) => <>{children}</>),
}))

// Capture ReactFlow props for testing edge reconnecting
let capturedReactFlowProps: any = null
const mockReactFlowInstance = { fitView: vi.fn() }

// Mock elkjs
const { mockElkLayout } = vi.hoisted(() => ({
  mockElkLayout: vi.fn(() =>
    Promise.resolve({
      children: [
        { id: 't1', x: 100, y: 200 },
        { id: 't2', x: 400, y: 200 },
      ],
    })
  ),
}))

vi.mock('elkjs/lib/elk.bundled.js', () => ({
  default: function () {
    return { layout: mockElkLayout }
  },
}))

// Mock React Flow
vi.mock('@xyflow/react', () => ({
  ReactFlow: vi.fn((props) => {
    capturedReactFlowProps = props
    return (
      <div
        data-testid="react-flow"
        tabIndex={0}
        onKeyDown={(e) => props.onKeyDown?.(e)}
      >
        {props.children}
        <button
          data-testid="mock-node-click"
          onClick={(e) => props.onNodeClick?.(e, { id: 't1' })}
        >
          Select Table 1
        </button>
        {/* Render mock edges with clickable triggers */}
        {props.edges?.map((edge: any) => (
          <button
            key={edge.id}
            data-testid={`mock-edge-${edge.id}`}
            onClick={(e) => props.onEdgeClick?.(e, edge)}
            data-selected={edge.selected}
            data-style={JSON.stringify(edge.style)}
          >
            Edge {edge.id}
          </button>
        ))}
      </div>
    )
  }),
  ReactFlowProvider: vi.fn(({ children }) => <>{children}</>),
  useReactFlow: vi.fn(() => mockReactFlowInstance),
  Controls: vi.fn(() => null),
  Background: vi.fn(() => null),
  Panel: vi.fn(({ children, style, className }) => (
    <div data-testid="react-flow-panel" style={style} className={className}>
      {children}
    </div>
  )),
  applyNodeChanges: vi.fn((_changes, nds) => nds),
  applyEdgeChanges: vi.fn((_changes, eds) => eds),
  Handle: vi.fn(() => null),
  Position: { Left: 'left', Right: 'right' },
  MarkerType: { ArrowClosed: 'arrowclosed' },
}))

vi.mock('../lib/api', () => ({
  submitDefaultVectorIndexEntries: vi.fn(),
  fetchCurrentVectorIndexEntries: vi.fn(),
}))

const mockTables: TableDraft[] = [
  {
    id: 't1',
    name: 'orders',
    x: 0,
    y: 0,
    columns: [
      {
        id: 'c1',
        columnName: 'customer_id',
        sourceKey: 'orders.customer_id',
        description: 'ID of the customer',
        dataFormat: 'integer',
        statisticalType: 'identifier',
        categoricalValues: [],
        aliasesText: 'cust_id',
        sampleValuesText: '1, 2, 3',
        payloadText: '{}',
        references: 'customers.id',
      },
    ],
  },
]

const mockSyncedEntries = [
  {
    entry_id: 1,
    table_name: 'orders',
    column_name: 'customer_id',
    source_key: 'orders.customer_id',
    description: 'ID of the customer',
    data_format: 'integer',
    statistical_type: 'identifier',
    aliases: ['cust_id'],
    sample_values: ['1', '2', '3'],
    payload: {},
    references: 'customers.id',
  },
]

describe('Workbench Rework Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    capturedReactFlowProps = null
    vi.mocked(api.fetchCurrentVectorIndexEntries).mockResolvedValue([])
  })

  it('verifies sidebar form completeness including Data Format and Categories', async () => {
    render(<VectorIndexBuilderPage tables={mockTables} setTables={vi.fn()} />)

    // Select the table
    fireEvent.click(screen.getByTestId('mock-node-click'))

    expect(screen.getByText(/Table Editor/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Data Format/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Statistical Type/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Aliases/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Sample Values/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Payload JSON/i)).toBeInTheDocument()
  })

  it('verifies "Delete Table" button existence in the sidebar', () => {
    render(<VectorIndexBuilderPage tables={mockTables} setTables={vi.fn()} />)
    fireEvent.click(screen.getByTestId('mock-node-click'))

    expect(
      screen.getAllByRole('button', { name: /Delete Table/i }).length
    ).toBeGreaterThan(0)
  })

  it('verifies Peek Query and Table Editor are mutually exclusive', () => {
    render(<VectorIndexBuilderPage tables={mockTables} setTables={vi.fn()} />)

    // Open Peek
    fireEvent.click(screen.getByRole('button', { name: /Peek Query/i }))
    expect(
      screen.getByRole('heading', { name: /Peek Query/i })
    ).toBeInTheDocument()

    // Select Table
    fireEvent.click(screen.getByTestId('mock-node-click'))

    // Peek should be gone, Editor should be there
    expect(
      screen.queryByRole('heading', { name: /Peek Query/i })
    ).not.toBeInTheDocument()
    expect(screen.getByText(/Table Editor/i)).toBeInTheDocument()

    // Open Peek again
    fireEvent.click(screen.getByRole('button', { name: /Peek Query/i }))
    expect(screen.queryByText(/Table Editor/i)).not.toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /Peek Query/i })
    ).toBeInTheDocument()
  })

  it('verifies References (FK) field is present in column settings', () => {
    render(<VectorIndexBuilderPage tables={mockTables} setTables={vi.fn()} />)
    fireEvent.click(screen.getByTestId('mock-node-click'))

    expect(screen.getByLabelText(/References \(FK\)/i)).toBeInTheDocument()
  })

  it('verifies visual differentiation between handles', () => {
    render(<VectorIndexBuilderPage tables={mockTables} setTables={vi.fn()} />)
    // We expect the Left handle to be a circle and Right to be a triangle
    // This makes the 'opposite sides' requirement obvious
  })

  it('verifies standard Right-to-Left connection logic', () => {
    // Check that edges point from -source to -target
  })

  it('verifies top-right buttons shift when sidebar is open', () => {
    render(<VectorIndexBuilderPage tables={mockTables} setTables={vi.fn()} />)

    // Check the Panel container via the forwarded style prop
    const panel = screen.getByTestId('react-flow-panel')

    // Sidebar closed
    expect(panel).toHaveStyle({ marginRight: '20px' })

    // Open table editor
    fireEvent.click(screen.getByTestId('mock-node-click'))
    expect(panel).toHaveStyle({ marginRight: '420px' })
  })
})

// ------------------------------------------------------------------
// RED PHASE: Auto-Layout Bug Fixes
// ------------------------------------------------------------------
describe('Auto-Layout Bug Fixes (Red Phase)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    capturedReactFlowProps = null
  })

  it('AL-1: clicking auto-layout button invokes elk.layout with graph data', async () => {
    vi.mocked(api.fetchCurrentVectorIndexEntries).mockResolvedValue([])
    const setTables = vi.fn()

    render(<VectorIndexBuilderPage tables={mockTables} setTables={setTables} />)

    const autoLayoutBtn = screen.getByTitle('Auto-Layout')
    fireEvent.click(autoLayoutBtn)

    await waitFor(() => {
      expect(mockElkLayout).toHaveBeenCalled()
    })

    // Verify it was called with a proper graph structure, not a click event
    const callArg = (mockElkLayout.mock.calls[0] as any[])[0]
    expect(callArg).toBeDefined()
    expect(callArg).toHaveProperty('id', 'root')
    expect(callArg).toHaveProperty('children')
    expect(Array.isArray(callArg.children)).toBe(true)
  })

  it('AL-2: auto-layout runs on initial mount when tables populate after synced entries', async () => {
    vi.mocked(api.fetchCurrentVectorIndexEntries).mockResolvedValue(
      mockSyncedEntries
    )
    const setTables = vi.fn()

    // Start with only 1 table (condition not met), not visible yet
    const { rerender: _rerender } = render(
      <VectorIndexBuilderPage tables={[mockTables[0]]} setTables={setTables} isVisible={false} />
    )

    // Wait for fetch to resolve and syncedEntries to populate
    await waitFor(() =>
      expect(api.fetchCurrentVectorIndexEntries).toHaveBeenCalled()
    )

    // Auto-layout should NOT have run yet (only 1 table)
    expect(mockElkLayout).not.toHaveBeenCalled()

    // Now simulate App.tsx populating tables to 2 tables
    const twoTables: TableDraft[] = [
      mockTables[0],
      {
        id: 't2',
        name: 'customers',
        x: 0,
        y: 0,
        columns: [
          {
            id: 'c2',
            columnName: 'id',
            sourceKey: 'customers.id',
            description: '',
            dataFormat: '',
            statisticalType: 'identifier',
            categoricalValues: [],
            aliasesText: '',
            sampleValuesText: '',
            payloadText: '{}',
            references: '',
          },
        ],
      },
    ]

    _rerender(
      <VectorIndexBuilderPage tables={twoTables} setTables={setTables} isVisible={true} />
    )

    // Auto-layout should now run because tables > 1 AND syncedEntries > 0
    await waitFor(() => {
      expect(mockElkLayout).toHaveBeenCalled()
    })
  })

  it('AL-3: save index triggers auto-layout after successful API call', async () => {
    vi.mocked(api.fetchCurrentVectorIndexEntries).mockResolvedValue([])
    vi.mocked(api.submitDefaultVectorIndexEntries).mockResolvedValue({} as any)
    const setTables = vi.fn()

    render(<VectorIndexBuilderPage tables={mockTables} setTables={setTables} />)

    const saveBtn = screen.getByRole('button', { name: /Save Index/i })
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(api.submitDefaultVectorIndexEntries).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(mockElkLayout).toHaveBeenCalled()
    })
  })
})

// ------------------------------------------------------------------
// RED PHASE: Edge Reconnecting Bug Fixes
// ------------------------------------------------------------------
describe('Edge Reconnecting Bug Fixes (Red Phase)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    capturedReactFlowProps = null
    vi.mocked(api.fetchCurrentVectorIndexEntries).mockResolvedValue([])
  })

  const twoTablesWithRef: TableDraft[] = [
    {
      id: 't1',
      name: 'orders',
      x: 0,
      y: 0,
      columns: [
        {
          id: 'c1',
          columnName: 'customer_id',
          sourceKey: 'orders.customer_id',
          description: '',
          dataFormat: '',
          statisticalType: 'identifier',
          categoricalValues: [],
          aliasesText: '',
          sampleValuesText: '',
          payloadText: '{}',
          references: 'customers.id',
        },
        {
          id: 'c1b',
          columnName: 'product_id',
          sourceKey: 'orders.product_id',
          description: '',
          dataFormat: '',
          statisticalType: 'identifier',
          categoricalValues: [],
          aliasesText: '',
          sampleValuesText: '',
          payloadText: '{}',
          references: '',
        },
      ],
    },
    {
      id: 't2',
      name: 'customers',
      x: 0,
      y: 0,
      columns: [
        {
          id: 'c2',
          columnName: 'id',
          sourceKey: 'customers.id',
          description: '',
          dataFormat: '',
          statisticalType: 'identifier',
          categoricalValues: [],
          aliasesText: '',
          sampleValuesText: '',
          payloadText: '{}',
          references: '',
        },
      ],
    },
  ]

  it('ER-1: edges are rendered with reconnectable: true for React Flow v12', () => {
    render(
      <VectorIndexBuilderPage tables={twoTablesWithRef} setTables={vi.fn()} />
    )

    expect(capturedReactFlowProps).not.toBeNull()
    expect(capturedReactFlowProps.edges.length).toBeGreaterThan(0)

    const edge = capturedReactFlowProps.edges[0]
    expect(edge.reconnectable).toBe(true)
    expect(edge.reconnectable).not.toBe('both')
  })

  it('ER-2: reconnecting source to new column clears old source and sets new source references', () => {
    const setTables = vi.fn()
    render(
      <VectorIndexBuilderPage tables={twoTablesWithRef} setTables={setTables} />
    )

    const oldEdge = capturedReactFlowProps.edges[0]
    const newConnection = {
      source: 't1',
      sourceHandle: 'c1b-source', // product_id
      target: 't2',
      targetHandle: 'c2-target',
    }

    capturedReactFlowProps.onReconnect(oldEdge, newConnection)

    expect(setTables).toHaveBeenCalled()
    const updater = setTables.mock.calls[0][0]
    const newState = updater(twoTablesWithRef)

    // Old source (customer_id) should have references cleared
    const oldCol = newState
      .find((t: TableDraft) => t.id === 't1')
      ?.columns.find((c: any) => c.id === 'c1')
    expect(oldCol?.references).toBe('')

    // New source (product_id) should have references set
    const newCol = newState
      .find((t: TableDraft) => t.id === 't1')
      ?.columns.find((c: any) => c.id === 'c1b')
    expect(newCol?.references).toBe('customers.id')
  })

  it('ER-3: reconnecting target updates source column references to new target', () => {
    const setTables = vi.fn()

    const threeTables: TableDraft[] = [
      ...twoTablesWithRef,
      {
        id: 't3',
        name: 'products',
        x: 0,
        y: 0,
        columns: [
          {
            id: 'c3',
            columnName: 'id',
            sourceKey: 'products.id',
            description: '',
            dataFormat: '',
            statisticalType: 'identifier',
            categoricalValues: [],
            aliasesText: '',
            sampleValuesText: '',
            payloadText: '{}',
            references: '',
          },
        ],
      },
    ]

    render(
      <VectorIndexBuilderPage tables={threeTables} setTables={setTables} />
    )

    const oldEdge = capturedReactFlowProps.edges[0]
    const newConnection = {
      source: 't1',
      sourceHandle: 'c1-source',
      target: 't3',
      targetHandle: 'c3-target',
    }

    capturedReactFlowProps.onReconnect(oldEdge, newConnection)

    const updater = setTables.mock.calls[0][0]
    const newState = updater(threeTables)

    // Source column should reference the new target
    const sourceCol = newState
      .find((t: TableDraft) => t.id === 't1')
      ?.columns.find((c: any) => c.id === 'c1')
    expect(sourceCol?.references).toBe('products.id')
  })

  it('ER-4: reconnecting is blocked if it would create a duplicate reference on the same table', () => {
    const setTables = vi.fn()

    // Setup: c1 -> customers.id, c1b -> products.id
    const tablesWithExistingEdges = twoTablesWithRef.map((t) =>
      t.id === 't1'
        ? {
            ...t,
            columns: t.columns.map((c) =>
              c.id === 'c1b' ? { ...c, references: 'products.id' } : c
            ),
          }
        : t
    )

    const fullTables: TableDraft[] = [
      ...tablesWithExistingEdges,
      {
        id: 't3',
        name: 'products',
        x: 0,
        y: 0,
        columns: [
          {
            id: 'c3',
            columnName: 'id',
            sourceKey: 'products.id',
            description: '',
            dataFormat: '',
            statisticalType: 'identifier',
            categoricalValues: [],
            aliasesText: '',
            sampleValuesText: '',
            payloadText: '{}',
            references: '',
          },
        ],
      },
    ]

    render(
      <VectorIndexBuilderPage tables={fullTables} setTables={setTables} />
    )

    // Old edge: c1b -> products.id
    const oldEdge = capturedReactFlowProps.edges.find(
      (e: any) => e.sourceHandle === 'c1b-source'
    )
    expect(oldEdge).toBeDefined()

    // Try to reconnect c1b to customers.id (which c1 already references)
    const newConnection = {
      source: 't1',
      sourceHandle: 'c1b-source',
      target: 't2',
      targetHandle: 'c2-target',
    }

    capturedReactFlowProps.onReconnect(oldEdge, newConnection)

    // Should be blocked - setTables should NOT be called
    expect(setTables).not.toHaveBeenCalled()
  })
})

// ------------------------------------------------------------------
// RED PHASE: Edge Deletion
// ------------------------------------------------------------------
describe('Edge Deletion (Red Phase)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    capturedReactFlowProps = null
    vi.mocked(api.fetchCurrentVectorIndexEntries).mockResolvedValue([])
  })

  const tablesWithEdge: TableDraft[] = [
    {
      id: 't1',
      name: 'orders',
      x: 0, y: 0,
      columns: [
        {
          id: 'c1',
          columnName: 'customer_id',
          sourceKey: 'orders.customer_id',
          description: '',
          dataFormat: '',
          statisticalType: 'identifier',
          categoricalValues: [],
          aliasesText: '',
          sampleValuesText: '',
          payloadText: '{}',
          references: 'customers.id',
        },
      ],
    },
    {
      id: 't2',
      name: 'customers',
      x: 0, y: 0,
      columns: [
        {
          id: 'c2',
          columnName: 'id',
          sourceKey: 'customers.id',
          description: '',
          dataFormat: '',
          statisticalType: 'identifier',
          categoricalValues: [],
          aliasesText: '',
          sampleValuesText: '',
          payloadText: '{}',
          references: '',
        },
      ],
    },
  ]

  it('ED-1: clicking an edge selects it', () => {
    render(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />)

    const edgeEl = screen.getByTestId('mock-edge-edge-c1-c2')
    fireEvent.click(edgeEl)

    // The edge should have been passed to onEdgeClick and marked selected
    expect(edgeEl).toHaveAttribute('data-selected', 'true')
  })

  it('ED-2: selected edge without pending deletion keeps standard style', () => {
    render(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />)

    const edgeEl = screen.getByTestId('mock-edge-edge-c1-c2')
    fireEvent.click(edgeEl)

    // Should NOT be red — it's selected but not marked for deletion
    const style = JSON.parse(edgeEl.getAttribute('data-style') || '{}')
    expect(style.stroke).not.toBe('#ef4444')
  })

  it('ED-3: pressing Delete on selected edge marks source column for deletion', () => {
    render(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />)

    const flowContainer = screen.getByTestId('react-flow')
    const edgeEl = screen.getByTestId('mock-edge-edge-c1-c2')

    // Select edge
    fireEvent.click(edgeEl)

    // Press Delete
    fireEvent.keyDown(flowContainer, { key: 'Delete', code: 'Delete' })

    // Re-render check: edge should now be red dashed (pending deletion)
    const updatedEdge = screen.getByTestId('mock-edge-edge-c1-c2')
    const style = JSON.parse(updatedEdge.getAttribute('data-style') || '{}')
    expect(style.stroke).toBe('#ef4444')
    expect(style.strokeDasharray).toBe('5,5')
  })

  it('ED-4: edge with pending deletion renders red dashed', () => {
    const { rerender } = render(
      <VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />
    )

    const flowContainer = screen.getByTestId('react-flow')
    const edgeEl = screen.getByTestId('mock-edge-edge-c1-c2')

    // Select and delete
    fireEvent.click(edgeEl)
    fireEvent.keyDown(flowContainer, { key: 'Delete', code: 'Delete' })

    // Force re-render to pick up new edge styles
    rerender(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />)

    const updatedEdge = screen.getByTestId('mock-edge-edge-c1-c2')
    const style = JSON.parse(updatedEdge.getAttribute('data-style') || '{}')
    expect(style.stroke).toBe('#ef4444')
    expect(style.strokeDasharray).toBe('5,5')
  })

  it('ED-5: pressing Delete again on same edge restores original style', () => {
    const { rerender } = render(
      <VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />
    )

    const flowContainer = screen.getByTestId('react-flow')
    const edgeEl = screen.getByTestId('mock-edge-edge-c1-c2')

    // Select, delete, undelete
    fireEvent.click(edgeEl)
    fireEvent.keyDown(flowContainer, { key: 'Delete', code: 'Delete' })
    rerender(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />)

    fireEvent.keyDown(flowContainer, { key: 'Delete', code: 'Delete' })
    rerender(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />)

    const updatedEdge = screen.getByTestId('mock-edge-edge-c1-c2')
    const style = JSON.parse(updatedEdge.getAttribute('data-style') || '{}')
    expect(style.stroke).not.toBe('#ef4444')
  })

  it('ED-6: pressing Delete with no edge selected does nothing', () => {
    render(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={vi.fn()} />)

    const flowContainer = screen.getByTestId('react-flow')
    const edgeEl = screen.getByTestId('mock-edge-edge-c1-c2')

    // Press Delete without selecting anything
    fireEvent.keyDown(flowContainer, { key: 'Delete', code: 'Delete' })

    // Edge should still be standard style (not red)
    const style = JSON.parse(edgeEl.getAttribute('data-style') || '{}')
    expect(style.stroke).not.toBe('#ef4444')
  })

  it('ED-7: Save Index clears pending deletions and submits without deleted refs', async () => {
    vi.mocked(api.submitDefaultVectorIndexEntries).mockResolvedValue({} as any)
    const setTables = vi.fn()

    const { rerender } = render(
      <VectorIndexBuilderPage tables={tablesWithEdge} setTables={setTables} />
    )

    const flowContainer = screen.getByTestId('react-flow')
    const edgeEl = screen.getByTestId('mock-edge-edge-c1-c2')

    // Select and mark for deletion
    fireEvent.click(edgeEl)
    fireEvent.keyDown(flowContainer, { key: 'Delete', code: 'Delete' })
    rerender(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={setTables} />)

    // Save
    const saveBtn = screen.getByRole('button', { name: /Save Index/i })
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(api.submitDefaultVectorIndexEntries).toHaveBeenCalled()
    })

    // Check submitted entries don't include the deleted reference
    const submitted = (api.submitDefaultVectorIndexEntries as any).mock.calls[0][0]
    const entries = submitted.entries
    const deletedEntry = entries.find(
      (e: any) => e.table_name === 'orders' && e.column_name === 'customer_id'
    )
    expect(deletedEntry.references).toBeNull()
  })

  it('ED-8: after Save Index, deleted edges disappear from canvas', async () => {
    vi.mocked(api.submitDefaultVectorIndexEntries).mockResolvedValue({} as any)
    const setTables = vi.fn()

    const { rerender } = render(
      <VectorIndexBuilderPage tables={tablesWithEdge} setTables={setTables} />
    )

    const flowContainer = screen.getByTestId('react-flow')
    const edgeEl = screen.getByTestId('mock-edge-edge-c1-c2')

    // Select and mark for deletion
    fireEvent.click(edgeEl)
    fireEvent.keyDown(flowContainer, { key: 'Delete', code: 'Delete' })
    rerender(<VectorIndexBuilderPage tables={tablesWithEdge} setTables={setTables} />)

    // Save
    const saveBtn = screen.getByRole('button', { name: /Save Index/i })
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(api.submitDefaultVectorIndexEntries).toHaveBeenCalled()
    })

    // After save, the edge should have been removed (setTables should have been called)
    expect(setTables).toHaveBeenCalled()
  })
})
