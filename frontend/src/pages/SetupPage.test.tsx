import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { SetupPage } from "./SetupPage"
import * as api from "@/lib/api"

vi.mock("@/lib/api", () => ({
  saveEngineConfig: vi.fn(),
}))

describe("SetupPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders setup wizard correctly", () => {
    render(<SetupPage onComplete={() => {}} />)
    
    expect(screen.getByText(/Welcome to TinyBI/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Local LLM/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Remote LLM/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Save & Connect/i })).toBeInTheDocument()
  })

  it("submits form and handles error", async () => {
    vi.mocked(api.saveEngineConfig).mockRejectedValueOnce(
      new Error("Ollama is running signature not found")
    )

    render(<SetupPage onComplete={() => {}} />)
    
    fireEvent.click(screen.getByRole("button", { name: /Save & Connect/i }))

    await waitFor(() => {
      expect(screen.getByText(/Ollama is running signature not found/i)).toBeInTheDocument()
    })
  })

  it("submits form and succeeds", async () => {
    vi.mocked(api.saveEngineConfig).mockResolvedValueOnce({
      success: true,
    })

    const onComplete = vi.fn()
    render(<SetupPage onComplete={onComplete} />)
    
    fireEvent.click(screen.getByRole("button", { name: /Save & Connect/i }))

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1)
    })
  })
})
