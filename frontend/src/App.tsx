import { useEffect, useState } from "react"

import {
  DashboardHome,
  type ConnectionState,
} from "@/pages/DashboardHome"
import { VectorIndexBuilderPage } from "@/pages/VectorIndexBuilderPage"
import { QueryPage } from "@/pages/QueryPage"

type AppRoute = "/" | "/vector-index" | "/query"

function resolveRoute(pathname: string): AppRoute {
  if (pathname === "/vector-index") return "/vector-index"
  if (pathname === "/query") return "/query"
  return "/"
}

function App() {
  const [route, setRoute] = useState<AppRoute>(() => resolveRoute(window.location.pathname))
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle")
  const [connectionMessage, setConnectionMessage] = useState(
    "No backend check yet. Start FastAPI and use the button below."
  )

  useEffect(() => {
    function handlePopState() {
      setRoute(resolveRoute(window.location.pathname))
    }

    window.addEventListener("popstate", handlePopState)
    return () => window.removeEventListener("popstate", handlePopState)
  }, [])

  function navigate(nextRoute: AppRoute) {
    if (nextRoute === route) {
      return
    }

    window.history.pushState({}, "", nextRoute)
    setRoute(nextRoute)
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  if (route === "/vector-index") {
    return <VectorIndexBuilderPage onBackToDashboard={() => navigate("/")} />
  }

  if (route === "/query") {
    return <QueryPage onBackToDashboard={() => navigate("/")} />
  }

  return (
    <DashboardHome
      connectionState={connectionState}
      connectionMessage={connectionMessage}
      setConnectionState={setConnectionState}
      setConnectionMessage={setConnectionMessage}
      onOpenVectorIndexBuilder={() => navigate("/vector-index")}
      onOpenQueryPage={() => navigate("/query")}
    />
  )
}

export default App
