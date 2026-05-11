import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryPage } from "./QueryPage"
import * as api from "@/lib/api"

vi.mock("@/lib/api", () => ({
  submitQuery: vi.fn(),
}))

const mockSubmitQuery = vi.mocked(api.submitQuery)

describe("QueryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("displays explanation when present in response", async () => {
    mockSubmitQuery.mockResolvedValue({
      sql: "SELECT provider FROM orders",
      data: [{ provider: "SPX", total: 100 }],
      explanation: "Logistics insight: providers show varied performance.",
    } as unknown as api.QueryResponse)

    const user = userEvent.setup()
    render(<QueryPage />)

    await user.type(
      screen.getByPlaceholderText("How many orders were placed last month in Germany?"),
      "test query",
    )
    await user.click(screen.getByRole("button", { name: /submit/i }))

    await waitFor(() => {
      expect(
        screen.getByText("Logistics insight: providers show varied performance."),
      ).toBeInTheDocument()
    })
  })

  it("does not render explanation section when explanation is absent", async () => {
    mockSubmitQuery.mockResolvedValue({
      sql: "SELECT provider FROM orders",
      data: [{ provider: "SPX", total: 100 }],
    } as unknown as api.QueryResponse)

    const user = userEvent.setup()
    render(<QueryPage />)

    await user.type(
      screen.getByPlaceholderText("How many orders were placed last month in Germany?"),
      "another query",
    )
    await user.click(screen.getByRole("button", { name: /submit/i }))

    await waitFor(() => {
      expect(screen.getByText("Generated SQL")).toBeInTheDocument()
    })

    expect(screen.queryByText(/explanation/i)).not.toBeInTheDocument()
    expect(screen.queryByText("Logistics insight")).not.toBeInTheDocument()
  })

  // ------------------------------------------------------------------
  // RED PHASE: QueryPage Layout Rework
  // ------------------------------------------------------------------
  it("QP-1: results table renders in the two-column grid alongside SQL", async () => {
    mockSubmitQuery.mockResolvedValue({
      sql: "SELECT * FROM orders",
      data: [{ id: 1, total: 100 }],
      explanation: "Some insight.",
    } as unknown as api.QueryResponse)

    const user = userEvent.setup()
    render(<QueryPage />)

    await user.type(
      screen.getByPlaceholderText("How many orders were placed last month in Germany?"),
      "test",
    )
    await user.click(screen.getByRole("button", { name: /submit/i }))

    await waitFor(() => {
      expect(screen.getByText("Generated SQL")).toBeInTheDocument()
    })

    // The results container should NOT have lg:col-span-2 (it should be in the grid)
    const resultsHeading = screen.getByText("Results")
    const resultsCard = resultsHeading.closest("[class*='col-span']") || resultsHeading.closest("div")
    expect(resultsCard).not.toHaveClass("lg:col-span-2")
  })

  it("QP-2: AI Insight renders below the SQL/Results grid", async () => {
    mockSubmitQuery.mockResolvedValue({
      sql: "SELECT * FROM orders",
      data: [{ id: 1 }],
      explanation: "Logistics insight: providers show varied performance.",
    } as unknown as api.QueryResponse)

    const user = userEvent.setup()
    render(<QueryPage />)

    await user.type(
      screen.getByPlaceholderText("How many orders were placed last month in Germany?"),
      "test",
    )
    await user.click(screen.getByRole("button", { name: /submit/i }))

    await waitFor(() => {
      expect(
        screen.getByText("Logistics insight: providers show varied performance."),
      ).toBeInTheDocument()
    })

    // AI Insight should be in a full-width section (col-span-2 or similar)
    const insightHeading = screen.getByText("AI Insight")
    const insightCard = insightHeading.closest("[class*='col-span']") || insightHeading.closest("div")
    expect(insightCard).toHaveClass(/lg:col-span-2/)
  })

  it("QP-3: results table scrolls both vertically and horizontally", async () => {
    mockSubmitQuery.mockResolvedValue({
      sql: "SELECT * FROM orders",
      data: Array.from({ length: 25 }, (_, i) => ({ id: i + 1, col: "val" })),
    } as unknown as api.QueryResponse)

    const user = userEvent.setup()
    render(<QueryPage />)

    await user.type(
      screen.getByPlaceholderText("How many orders were placed last month in Germany?"),
      "test",
    )
    await user.click(screen.getByRole("button", { name: /submit/i }))

    await waitFor(() => {
      expect(screen.getByText("Results")).toBeInTheDocument()
    })

    const tableContainer = document.querySelector("div.overflow-x-auto.overflow-y-auto")
    expect(tableContainer).toBeInTheDocument()
    expect(tableContainer).toHaveClass("overflow-x-auto")
    expect(tableContainer).toHaveClass("overflow-y-auto")

    // No expand/collapse button
    expect(screen.queryByText(/Show All/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Show Less/i)).not.toBeInTheDocument()
  })

  it("QP-4: question input is a textarea supporting multi-line entry", async () => {
    render(<QueryPage />)

    const input = screen.getByPlaceholderText("How many orders were placed last month in Germany?")
    expect(input.tagName.toLowerCase()).toBe("textarea")
  })

  it("QP-5: textarea auto-expands vertically as text grows", async () => {
    render(<QueryPage />)

    const textarea = screen.getByPlaceholderText("How many orders were placed last month in Germany?")
    expect(textarea).toHaveClass(/min-h-/)
    expect(textarea).toHaveClass(/resize-none/)
    expect(textarea).toHaveClass(/overflow-y-auto/)
  })
})
