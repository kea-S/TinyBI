import { render, screen } from "@testing-library/react"
import { expect, test, vi } from "vitest"
import { QueryPage } from "../pages/QueryPage"

// Mock the components so we just test the layout rendering
vi.mock("../components/builder/DataModal", () => ({
  DataModal: () => <div data-testid="data-modal" />
}))
vi.mock("../components/builder/ChatMessage", () => ({
  ChatMessage: () => <div data-testid="chat-message" />
}))

test("renders purely as a chat interface without the Conversational Data Intelligence header", () => {
  render(<QueryPage />)
  
  // The header text should not be in the document
  expect(screen.queryByText("TinyBI Chat")).not.toBeInTheDocument()
  expect(screen.queryByText("Conversational Data Intelligence")).not.toBeInTheDocument()

  // The chat welcome text should still be there
  expect(screen.getByText("Welcome to TinyBI")).toBeInTheDocument()
})
