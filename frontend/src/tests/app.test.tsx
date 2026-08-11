import { render, screen, act } from "@testing-library/react"
import { expect, test, vi } from "vitest"
import App from "../App"
import { fetchCurrentVectorIndexEntries, fetchEngineConfig } from "../lib/api"


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
  saveEngineConfig: vi.fn().mockResolvedValue({ success: true }),
  fetchEngineConfig: vi.fn().mockResolvedValue({ 
    configured: true, 
    config: { 
      active_llm: "local", 
      local_llm: { model: "Mock-LLM" }, 
      remote_llm: { model: "Mock-LLM" }, 
      embedding: { model: "Mock-Vector" } 
    } 
  })
}))

test("renders top navigation instead of sidebar and includes engine status", async () => {
  render(<App />)
  
  // Wait for the global nav to appear once configuration loads
  const logo = await screen.findByAltText("TinyBI Logo")
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
  // Should have the engine badges loaded dynamically
  expect(await screen.findByText(/LLM: Mock-LLM/i, {}, { timeout: 2000 })).toBeInTheDocument()
  expect(await screen.findByText(/Vector: Mock-Vector/i, {}, { timeout: 2000 })).toBeInTheDocument()
})


test("re-fetches vector index entries after setup is completed", async () => {
  const fetchConfigMock = vi.mocked(fetchEngineConfig)
  fetchConfigMock.mockResolvedValueOnce({
    configured: false,
    config: null
  })
  
  const fetchEntriesMock = vi.mocked(fetchCurrentVectorIndexEntries)
  fetchEntriesMock.mockClear()
  
  render(<App />)
  
  expect(await screen.findByText(/Welcome to TinyBI/i)).toBeInTheDocument()
  expect(fetchEntriesMock).toHaveBeenCalledTimes(1)
  
  fetchEntriesMock.mockClear()
  
  fetchConfigMock.mockResolvedValueOnce({
    configured: true,
    config: {
      active_llm: "local",
      local_llm: { model: "Mock-LLM", base_url: "" },
      remote_llm: { model: "Mock-LLM", api_key: "" },
      embedding: { model: "Mock-Vector", base_url: "", api_key: "" }
    }
  })
  
  const saveButton = screen.getByRole("button", { name: /Save & Connect/i })
  act(() => {
    saveButton.click()
  })
  
  await vi.waitFor(() => {
    expect(fetchEntriesMock).toHaveBeenCalledTimes(1)
  })
})

test("populates SetupPage fields with saved backend configuration", async () => {
  const fetchConfigMock = vi.mocked(fetchEngineConfig)
  fetchConfigMock.mockResolvedValue({
    configured: true,
    config: {
      active_llm: "local",
      local_llm: { model: "custom-ollama-model", base_url: "http://custom-host:11434" },
      remote_llm: { model: "llama-3.1-8b-instant", api_key: "gsk_custom" },
      embedding: { model: "jina-embeddings-v5-text-small", base_url: "https://api.jina.ai/v1", api_key: "jina_custom_key" }
    }
  })

  render(<App />)

  // Switch to setup tab
  const vectorBadge = await screen.findByText(/Vector: jina-embeddings-v5-text-small/i)
  act(() => {
    vectorBadge.click()
  })

  expect(await screen.findByDisplayValue("custom-ollama-model")).toBeInTheDocument()
  expect(await screen.findByDisplayValue("jina-embeddings-v5-text-small")).toBeInTheDocument()
  expect(await screen.findByDisplayValue("jina_custom_key")).toBeInTheDocument()
})


