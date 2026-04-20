import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VectorIndexBuilderPage } from './VectorIndexBuilderPage'
import * as api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  fetchCurrentVectorIndexEntries: vi.fn(),
  submitDefaultVectorIndexEntries: vi.fn(),
}))

const mockFetchCurrentVectorIndexEntries = vi.mocked(api.fetchCurrentVectorIndexEntries)
const mockSubmitDefaultVectorIndexEntries = vi.mocked(api.submitDefaultVectorIndexEntries)

describe('VectorIndexBuilderPage FK references', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchCurrentVectorIndexEntries.mockResolvedValue([])
    mockSubmitDefaultVectorIndexEntries.mockResolvedValue({
      embedding_model: 'nomic-embed-text',
      entry_count: 1,
      table_names: ['orders'],
      vector_index_path: '/tmp/columns.faiss',
      metadata_path: '/tmp/columns.json',
    })
  })

  it('includes references in submitted payload when set', async () => {
    const user = userEvent.setup()
    render(<VectorIndexBuilderPage onBackToDashboard={() => {}} />)

    await user.type(screen.getByPlaceholderText('orders'), 'customers')
    await user.click(screen.getByText('Add table'))
    await user.type(screen.getAllByPlaceholderText('orders')[1], 'orders')

    await user.type(screen.getAllByPlaceholderText('customer_city')[0], 'customer_id')
    await user.type(screen.getAllByPlaceholderText('orders.customer_id')[0], 'orders.customer_id')

    const select = screen.getByRole('combobox', { name: /references/i })
    await user.click(select)

    await user.click(screen.getByRole('option', { name: 'customers.id' }))

    await user.click(screen.getByRole('button', { name: /submit index batch/i }))

    await waitFor(() => {
      expect(mockSubmitDefaultVectorIndexEntries).toHaveBeenCalled()
    })

    const submittedPayload = mockSubmitDefaultVectorIndexEntries.mock.calls[0]![0]
    const orderColumn = submittedPayload.entries.find((e: { column_name: string }) => e.column_name === 'customer_id')
    expect(orderColumn).toBeDefined()
    expect(orderColumn!.references).toBe('customers.id')
  })

  it('load current index populates columns with references', async () => {
    mockFetchCurrentVectorIndexEntries.mockResolvedValue([
      {
        entry_id: 1,
        table_name: 'customers',
        column_name: 'id',
        source_key: 'customers.id',
        aliases: [],
        sample_values: [],
        payload: {},
        references: null,
      },
      {
        entry_id: 2,
        table_name: 'orders',
        column_name: 'customer_id',
        source_key: 'orders.customer_id',
        aliases: [],
        sample_values: [],
        payload: {},
        references: 'customers.id',
      },
    ])

    render(<VectorIndexBuilderPage onBackToDashboard={() => {}} />)

    await userEvent.click(screen.getByRole('button', { name: /load current index/i }))

    await waitFor(() => {
      expect(mockFetchCurrentVectorIndexEntries).toHaveBeenCalled()
    })

    expect(screen.getByText('customers.id')).toBeInTheDocument()
  })

  it('shows references in column list when set', async () => {
    mockFetchCurrentVectorIndexEntries.mockResolvedValue([
      {
        entry_id: 1,
        table_name: 'customers',
        column_name: 'id',
        source_key: 'customers.id',
        aliases: [],
        sample_values: [],
        payload: {},
        references: null,
      },
      {
        entry_id: 2,
        table_name: 'orders',
        column_name: 'customer_id',
        source_key: 'orders.customer_id',
        aliases: [],
        sample_values: [],
        payload: {},
        references: 'customers.id',
      },
    ])

    render(<VectorIndexBuilderPage onBackToDashboard={() => {}} />)

    await userEvent.click(screen.getByRole('button', { name: /load current index/i }))

    await waitFor(() => {
      expect(screen.getByText('→ customers.id')).toBeInTheDocument()
    })
  })
})
