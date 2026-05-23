import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryPage } from "./QueryPage"
import * as api from "@/lib/api"

vi.mock("@/lib/api", () => ({
  submitQuery: vi.fn(),
}))

const mockSubmitQuery = vi.mocked(api.submitQuery)

describe("QueryPage Chatbot", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("RED: adds user and assistant messages to history on submit", async () => {
    mockSubmitQuery.mockResolvedValue({
      message: "Here is your data.",
      sql: "SELECT * FROM orders",
      data: [{ id: 1 }],
    } as api.QueryResponse)

    const user = userEvent.setup()
    render(<QueryPage />)

    const input = screen.getByPlaceholderText(/Ask your data anything/i)
    await user.type(input, "hello world")
    await user.click(screen.getByRole("button", { name: /submit/i }))

    await waitFor(() => {
      expect(screen.getByText("hello world")).toBeInTheDocument()
      expect(screen.getByText("Here is your data.")).toBeInTheDocument()
    })
  })

  it("RED: displays 'Inspect Data' button when response has data", async () => {
    mockSubmitQuery.mockResolvedValue({
      message: "Found some records.",
      sql: "SELECT * FROM table",
      data: [{ id: 1 }],
    } as api.QueryResponse)

    const user = userEvent.setup()
    render(<QueryPage />)

    await user.type(screen.getByPlaceholderText(/Ask your data anything/i), "find data")
    await user.click(screen.getByRole("button", { name: /submit/i }))

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /inspect data/i })).toBeInTheDocument()
    })
  })

  it("RED: opens modal with SQL and Data when 'Inspect Data' is clicked", async () => {
    mockSubmitQuery.mockResolvedValue({
      message: "Records found.",
      sql: "SELECT * FROM orders",
      data: [{ id: 123, total: 456 }],
    } as api.QueryResponse)

    const user = userEvent.setup()
    render(<QueryPage />)

    await user.type(screen.getByPlaceholderText(/Ask your data anything/i), "get orders")
    await user.click(screen.getByRole("button", { name: /submit/i }))

    const inspectBtn = await screen.findByRole("button", { name: /inspect data/i })
    await user.click(inspectBtn)

    // Modal check
    expect(screen.getByText("Data Inspection")).toBeInTheDocument()
    expect(screen.getByText("SELECT * FROM orders")).toBeInTheDocument()
    expect(screen.getByText("123")).toBeInTheDocument()
    expect(screen.getByText("456")).toBeInTheDocument()
  })
})
