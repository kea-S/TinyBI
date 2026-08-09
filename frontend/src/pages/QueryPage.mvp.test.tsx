import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryPage } from "./QueryPage"

describe("QueryPage MVP Features", () => {
  it("RED: displays quick-start cards in empty state", () => {
    render(<QueryPage />)
    
    expect(screen.getByText(/How many accounts who choose issuance after transaction/i)).toBeInTheDocument()
    expect(screen.getByText(/percentage of loan amount that has been fully paid/i)).toBeInTheDocument()
    expect(screen.getByText(/percentage of clients who opened their accounts in the district/i)).toBeInTheDocument()
  })

  it("RED: clicking a quick-start card populates and focuses the input", async () => {
    const user = userEvent.setup()
    render(<QueryPage />)
    
    const exampleText = /How many accounts who choose issuance after transaction/i
    const card = screen.getByText(exampleText)
    const input = screen.getByPlaceholderText(/Ask your data anything/i)
    
    await user.click(card)
    
    expect(input).toHaveValue("How many accounts who choose issuance after transaction are staying in East Bohemia region?")
    expect(input).toHaveFocus()
  })
})
