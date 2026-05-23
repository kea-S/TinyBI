import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { DataModal } from "./DataModal"

describe("DataModal", () => {
  it("RED: should use max-w-5xl and account for sidebar offset", () => {
    const { container } = render(
      <DataModal isOpen={true} onClose={vi.fn()} sql="SELECT 1" data={[]} />
    )
    
    const outerWrapper = container.firstChild as HTMLElement
    expect(outerWrapper).toHaveClass("ml-20") // Sidebar width is w-20 (80px)
    
    const modalContainer = container.querySelector(".relative.w-full")
    expect(modalContainer).toHaveClass("max-w-5xl")
  })
})
