import { render, screen, waitFor } from "@testing-library/react"
/* eslint-disable @typescript-eslint/no-explicit-any */
import { vi, describe, it, expect, beforeEach } from "vitest"
import { MonitoringPage } from "./MonitoringPage"

// Mock the API calls we haven't written yet
vi.mock("@/lib/api", () => ({
  fetchOverviewStats: vi.fn(),
  fetchDifficultySegregated: vi.fn(),
  fetchProviderComparison: vi.fn()
}))

import { fetchOverviewStats, fetchDifficultySegregated, fetchProviderComparison } from "@/lib/api"

// Mock Recharts because it relies on ResizeObserver which isn't natively supported in jsdom
vi.mock("recharts", () => {
  const Original = vi.importActual("recharts")
  return {
    ...Original,
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
    BarChart: ({ children }: any) => <div data-testid="mock-bar-chart">{children}</div>,
    ComposedChart: ({ children }: any) => <div data-testid="mock-composed-chart">{children}</div>,
    CartesianGrid: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
    Legend: () => null,
    Bar: ({ dataKey }: any) => <div data-testid={`mock-bar-${dataKey}`} />,
    Line: ({ dataKey }: any) => <div data-testid={`mock-line-${dataKey}`} />,
  }
})

describe("MonitoringPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders only Accuracy and Latency KPIs (removes Tokens)", async () => {
    // Setup mock returns
    vi.mocked(fetchOverviewStats).mockResolvedValue({
      overallAccuracy: 0.85,
      meanLatencyMs: 14500,
      meanTokens: 8500,
      totalTokens: 272000
    })
    vi.mocked(fetchDifficultySegregated).mockResolvedValue([
      { provider: "TinyBI", difficulty: "simple", accuracy: 0.95, latencyMs: 12000, tokens: 6000 },
      { provider: "Schema Dump", difficulty: "simple", accuracy: 0.45, latencyMs: 8000, tokens: 12000 }
    ])
    vi.mocked(fetchProviderComparison).mockResolvedValue([
      { provider: "TinyBI", accuracy: 0.85, tokens: 8500, correct: 1, fail: 0, error: 0 }
    ])

    render(<MonitoringPage />)

    // Wait for the data to load and stats to be displayed
    await waitFor(() => {
      expect(screen.getByText(/System Health & Evaluation/i)).toBeInTheDocument()
      // 0.85 -> 85%
      expect(screen.getByText("85.00%")).toBeInTheDocument()
      // 14500 -> 14.50s
      expect(screen.getByText("14.50s")).toBeInTheDocument()
    })

    // Assert that the Token cards are NO LONGER rendered
    expect(screen.queryByText(/Mean Tokens \/ Query/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Total Tokens/i)).not.toBeInTheDocument()
    expect(screen.queryByText("8.50k")).not.toBeInTheDocument()
    expect(screen.queryByText("272.00k")).not.toBeInTheDocument()
  })

  it("renders the combined ComposedChart with both TinyBI and Schema Dump bars/lines", async () => {
    // Setup mock returns
    vi.mocked(fetchOverviewStats).mockResolvedValue({
      overallAccuracy: 0.85,
      meanLatencyMs: 14500,
      meanTokens: 8500,
      totalTokens: 272000
    })
    vi.mocked(fetchDifficultySegregated).mockResolvedValue([
      { provider: "TinyBI", difficulty: "simple", accuracy: 0.95, latencyMs: 12000, tokens: 6000 },
      { provider: "Schema Dump", difficulty: "simple", accuracy: 0.45, latencyMs: 8000, tokens: 12000 }
    ])
    vi.mocked(fetchProviderComparison).mockResolvedValue([])

    render(<MonitoringPage />)

    await waitFor(() => {
      expect(screen.getByTestId("mock-composed-chart")).toBeInTheDocument()
    })

    // Assert the exact dataKeys are passed to the bars/lines
    expect(screen.getByTestId("mock-bar-tinyBITokens")).toBeInTheDocument()
    expect(screen.getByTestId("mock-bar-schemaDumpTokens")).toBeInTheDocument()
    expect(screen.getByTestId("mock-line-tinyBIAccuracy")).toBeInTheDocument()
    expect(screen.getByTestId("mock-line-schemaDumpAccuracy")).toBeInTheDocument()
  })
})
