import { render, screen, fireEvent } from "@testing-library/react"
import { expect, test, vi } from "vitest"
import { MonitoringPage } from "../pages/MonitoringPage"

vi.mock("../lib/api", () => ({
  fetchMonitoringOverview: vi.fn().mockResolvedValue({
    lastRun: "2026-06-22T14:13:27.586Z",
    metrics: {
      score: 5.25,
      testPassCount: 6,
      testFailCount: 9,
      testErrorCount: 13,
      assertPassCount: 6,
      assertFailCount: 9,
      totalLatencyMs: 489843,
      tokenUsage: {
        total: 1000,
        prompt: 800,
        completion: 200
      }
    }
  })
}))

test("clicking Promptfoo Dashboard opens instructional Dialog", async () => {
  render(<MonitoringPage />)
  
  const dashboardBtn = await screen.findByRole("button", { name: /Promptfoo Dashboard/i })
  expect(dashboardBtn).toBeInTheDocument()

  fireEvent.click(dashboardBtn)

  // Expect dialog title to appear
  const dialogTitle = await screen.findByText(/Advanced Evaluation Viewer/i)
  expect(dialogTitle).toBeInTheDocument()

  // Expect docker command to be present
  expect(screen.getByText(/docker compose up promptfoo-view -d/i)).toBeInTheDocument()
})
