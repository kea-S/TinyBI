import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryPage } from "./QueryPage"

describe("QueryPage MVP Features", () => {
  it("RED: displays quick-start cards in empty state", () => {
    render(<QueryPage />)
    
    expect(screen.getByText(/For the female client who was born in 1976/i)).toBeInTheDocument()
    expect(screen.getByText(/List out the no. of districts that have female average salary/i)).toBeInTheDocument()
    expect(screen.getByText(/List all the withdrawals in cash transactions/i)).toBeInTheDocument()
  })

  it("RED: clicking a quick-start card populates and focuses the input", async () => {
    const user = userEvent.setup()
    render(<QueryPage />)
    
    const exampleText = /For the female client who was born in 1976/i
    const card = screen.getByText(exampleText)
    const input = screen.getByPlaceholderText(/Ask your data anything/i)
    
    await user.click(card)
    
    expect(input).toHaveValue("For the female client who was born in 1976/1/29, which district did she opened her account?")
    expect(input).toHaveFocus()
  })
})
