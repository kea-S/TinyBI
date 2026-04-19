import type { Dispatch, SetStateAction } from "react"
import {
  Activity,
  ArrowRight,
  Database,
  LayoutDashboard,
  RefreshCw,
  Search,
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

export type ConnectionState = "idle" | "loading" | "success" | "error"

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
    title: "Vector authoring",
    value: "Table-first editor",
    detail: "Build table groups, add linked columns, then submit a single batch to FastAPI.",
    icon: Database,
  },
] as const

const endpointRows = [
  {
    route: "POST /vector/index-entries/batch",
    purpose: "Create the active vector index with the default nomic embedding model.",
    target: "The new index builder page posts a flattened batch here.",
  },
  {
    route: "POST /vector/index-entries/batch/by-model/{key}",
    purpose: "Override the default embedder later from settings or advanced flows.",
    target: "Keeps model choice out of the request body.",
  },
  {
    route: "GET /docs",
    purpose: "Inspect the evolving API while wiring frontend and backend together.",
    target: "Useful when the vector builder schema changes.",
  },
] as const

type DashboardHomeProps = {
  connectionState: ConnectionState
  connectionMessage: string
  setConnectionState: Dispatch<SetStateAction<ConnectionState>>
  setConnectionMessage: Dispatch<SetStateAction<string>>
  onOpenVectorIndexBuilder: () => void
  onOpenQueryPage: () => void
}

export function DashboardHome({
  connectionState,
  connectionMessage,
  setConnectionMessage,
  setConnectionState,
  onOpenVectorIndexBuilder,
  onOpenQueryPage,
}: DashboardHomeProps) {
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
                The dashboard now has a dedicated vector index authoring flow.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
                Create tables, attach column metadata, and ship a single batch to the
                backend once the index draft is ready.
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
              <Button variant="outline" className="min-w-52" onClick={onOpenVectorIndexBuilder}>
                Open index builder
                <ArrowRight />
              </Button>
              <Button variant="outline" className="min-w-52" onClick={onOpenQueryPage}>
                <Search />
                Query
              </Button>
            </div>
          </div>

          <Card className="border-border/70 bg-background/85">
            <CardHeader>
              <CardTitle>Proxy and API base</CardTitle>
              <CardDescription>
                Development defaults are still set up so the browser can call FastAPI
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
                  Vite proxies <code>/api/*</code> to <code>http://127.0.0.1:8000</code>.
                  The vector authoring screen uses the default index endpoint, which in turn
                  uses the backend default embedding model.
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
            <CardTitle>Current backend routes in play</CardTitle>
            <CardDescription>
              The frontend now has a real destination for vector index authoring instead
              of just a placeholder route list.
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
              Use this before testing index submission from the new authoring page.
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
