import { useState } from "react"
import {
  Activity,
  ArrowRight,
  Database,
  LayoutDashboard,
  RefreshCw,
  Server,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { apiBaseUrl, pingBackend } from "@/lib/api"

type ConnectionState = "idle" | "loading" | "success" | "error"

const stackCards = [
  {
    title: "Frontend stack",
    value: "React 19 + Vite 8",
    detail: "TypeScript, HMR, and a dedicated workspace under frontend/.",
    icon: LayoutDashboard,
  },
  {
    title: "UI baseline",
    value: "shadcn + Tailwind v4",
    detail: "Radix-based components with a neutral dashboard theme.",
    icon: Activity,
  },
  {
    title: "Backend bridge",
    value: "FastAPI-ready",
    detail: "Local requests can default to /api and proxy to port 8000.",
    icon: Server,
  },
] as const

const endpointRows = [
  {
    route: "GET /health",
    purpose: "Basic liveness check for the UI connection button.",
    target: "Use this first when the FastAPI app comes online.",
  },
  {
    route: "POST /query",
    purpose: "Main text-to-SQL request entrypoint for the dashboard.",
    target: "The current API helper is ready to wrap this next.",
  },
  {
    route: "GET /docs",
    purpose: "Interactive inspection while backend routes are evolving.",
    target: "Accessible through the same local proxy setup.",
  },
] as const

function App() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle")
  const [connectionMessage, setConnectionMessage] = useState(
    "No backend check yet. Start FastAPI and use the button below."
  )

  async function handlePing() {
    setConnectionState("loading")

    try {
      const payload = await pingBackend()
      const formattedPayload =
        typeof payload === "string" ? payload : JSON.stringify(payload, null, 2)

      setConnectionState("success")
      setConnectionMessage(formattedPayload)
    } catch (error) {
      setConnectionState("error")
      setConnectionMessage(
        error instanceof Error ? error.message : "Unable to reach the backend."
      )
    }
  }

  const statusLabel =
    connectionState === "success"
      ? "Connected"
      : connectionState === "error"
        ? "Unavailable"
        : connectionState === "loading"
          ? "Checking"
          : "Waiting"

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-8 px-4 py-6 sm:px-6 lg:px-8">
      <section className="overflow-hidden rounded-[2rem] border border-border/70 bg-card/85 shadow-sm backdrop-blur">
        <div className="grid gap-8 px-6 py-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.9fr)] lg:px-8">
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="outline" className="rounded-full px-3 py-1">
                FastAPI dashboard shell
              </Badge>
              <Badge variant="secondary" className="rounded-full px-3 py-1">
                {statusLabel}
              </Badge>
            </div>

            <div className="space-y-3">
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                React, Vite, TypeScript, and shadcn are set up for the frontend.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
                This workspace is ready to sit in front of your Python backend
                without pulling application logic into the UI prematurely.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                onClick={handlePing}
                disabled={connectionState === "loading"}
                className="min-w-36"
              >
                <RefreshCw
                  className={
                    connectionState === "loading" ? "animate-spin" : undefined
                  }
                />
                Ping backend
              </Button>
              <Button asChild variant="outline">
                <a href={`${apiBaseUrl}/docs`} rel="noreferrer" target="_blank">
                  Open API docs
                  <ArrowRight />
                </a>
              </Button>
            </div>
          </div>

          <Card className="border-border/80 bg-background/90">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="size-4" />
                Connection profile
              </CardTitle>
              <CardDescription>
                The frontend defaults to a local proxy so you can call FastAPI
                without CORS work during development.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                  Browser request base
                </p>
                <Input readOnly value={apiBaseUrl} />
              </div>
              <div className="rounded-2xl border border-dashed border-border/80 bg-muted/50 p-4">
                <p className="text-sm leading-6 text-muted-foreground">
                  Vite dev server proxies <code>/api/*</code> to{" "}
                  <code>http://127.0.0.1:8000</code> by default. Override with{" "}
                  <code>VITE_BACKEND_URL</code> or set{" "}
                  <code>VITE_API_BASE_URL</code> if you want the browser to call
                  a fully qualified backend URL directly.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {stackCards.map(({ detail, icon: Icon, title, value }) => (
          <Card key={title} className="border-border/70 bg-card/80">
            <CardHeader className="gap-3">
              <div className="flex size-10 items-center justify-center rounded-2xl bg-muted">
                <Icon className="size-4" />
              </div>
              <div className="space-y-1">
                <CardDescription>{title}</CardDescription>
                <CardTitle className="text-xl">{value}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-6 text-muted-foreground">{detail}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.9fr)]">
        <Card className="border-border/70 bg-card/80">
          <CardHeader>
            <CardTitle>Suggested initial backend routes</CardTitle>
            <CardDescription>
              Enough structure to start integrating the dashboard without
              overcommitting the frontend yet.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Route</TableHead>
                  <TableHead>Purpose</TableHead>
                  <TableHead className="hidden xl:table-cell">Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {endpointRows.map((endpoint) => (
                  <TableRow key={endpoint.route}>
                    <TableCell className="font-medium">{endpoint.route}</TableCell>
                    <TableCell className="whitespace-normal text-muted-foreground">
                      {endpoint.purpose}
                    </TableCell>
                    <TableCell className="hidden whitespace-normal text-muted-foreground xl:table-cell">
                      {endpoint.target}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/80">
          <CardHeader>
            <CardTitle>Backend handshake</CardTitle>
            <CardDescription>
              Once FastAPI exposes a health endpoint, this panel becomes your
              first integration check.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-2xl border border-border/80 bg-muted/50 px-4 py-3">
              <span className="text-sm font-medium">Status</span>
              <Badge variant={connectionState === "success" ? "default" : "outline"}>
                {statusLabel}
              </Badge>
            </div>
            <Separator />
            <pre className="max-h-64 overflow-auto rounded-2xl bg-muted px-4 py-3 text-sm leading-6 whitespace-pre-wrap text-muted-foreground">
              {connectionMessage}
            </pre>
          </CardContent>
        </Card>
      </section>
    </main>
  )
}

export default App
