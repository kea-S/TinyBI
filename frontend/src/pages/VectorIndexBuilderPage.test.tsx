import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VectorIndexBuilderPage } from './VectorIndexBuilderPage'

// Mock React Flow since it doesn't work well in JSDOM
vi.mock('@xyflow/react', () => ({
  ReactFlow: vi.fn(() => <div data-testid="react-flow" />),
  ReactFlowProvider: vi.fn(({ children }) => <>{children}</>),
  useReactFlow: vi.fn(() => ({ fitView: vi.fn() })),
  Controls: vi.fn(() => null),
  Background: vi.fn(() => null),
  Panel: vi.fn(({ children }) => <div>{children}</div>),
  applyNodeChanges: vi.fn(),
  applyEdgeChanges: vi.fn(),
}))

vi.mock('@/lib/api', () => ({
  fetchCurrentVectorIndexEntries: vi.fn(() => Promise.resolve([])),
  submitDefaultVectorIndexEntries: vi.fn(),
}))

describe('VectorIndexBuilderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', () => {
    const mockTables = [
      {
        id: 'table-1',
        name: 'orders',
        columns: [
          {
            id: 'col-1',
            columnName: 'id',
            sourceKey: 'orders.id',
            description: '',
            dataFormat: '',
            statisticalType: 'identifier',
            categoricalValues: [],
            aliasesText: '',
            sampleValuesText: '',
            payloadText: '{}',
            references: '',
          }
        ],
        x: 0,
        y: 0
      }
    ]
    render(<VectorIndexBuilderPage tables={mockTables} setTables={vi.fn()} />)
    expect(screen.getByTestId('react-flow')).toBeInTheDocument()
  })
})
