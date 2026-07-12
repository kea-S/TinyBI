import { render, screen } from "@testing-library/react"
import { expect, test } from "vitest"
import App from "../App"

// Mock the components so we just test the layout rendering
vi.mock("../pages/VectorIndexBuilderPage", () => ({
  VectorIndexBuilderPage: () => <div data-testid="vector-builder" />
}))
vi.mock("../pages/QueryPage", () => ({
  QueryPage: () => <div data-testid="query-page" />
}))
vi.mock("../pages/MonitoringPage", () => ({
  MonitoringPage: () => <div data-testid="monitoring-page" />
}))
vi.mock("../lib/api", () => ({
  fetchCurrentVectorIndexEntries: vi.fn().mockResolvedValue([]),
  fetchEngineConfig: vi.fn().mockResolvedValue({ llm: "Mock-LLM", embedding: "Mock-Vector" })
}))

test("renders top navigation instead of sidebar and includes engine status", async () => {
  render(<App />)
  
  // The global nav should have the TinyBI logo image
  const logo = screen.getByAltText("TinyBI Logo")
  expect(logo).toBeInTheDocument()
  
  // Ensure the old h1 text is gone
  expect(screen.queryByText("TinyBI", { selector: "header h1" })).not.toBeInTheDocument()

  // The global nav should contain the nav links (Builder, Query, Monitoring) inside the header
  const header = logo.closest("header")
  expect(header).toBeInTheDocument()
  
  // The nav links should be in the header, not an aside
  expect(screen.getByRole("button", { name: /Builder/i })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: /Query/i })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: /Monitoring/i })).toBeInTheDocument()
  
  // No aside (sidebar) should exist
  expect(screen.queryByRole("complementary")).not.toBeInTheDocument() // <aside> is 'complementary' role
  
  // Should have the engine badges loaded dynamically
  expect(await screen.findByText(/LLM: Mock-LLM/i)).toBeInTheDocument()
  expect(await screen.findByText(/Vector: Mock-Vector/i)).toBeInTheDocument()
})
