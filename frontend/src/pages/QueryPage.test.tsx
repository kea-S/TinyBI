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
})
