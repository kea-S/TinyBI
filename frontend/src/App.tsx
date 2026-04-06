import { useEffect, useState } from "react"

import {
  DashboardHome,
  type ConnectionState,
} from "@/pages/DashboardHome"
import { VectorIndexBuilderPage } from "@/pages/VectorIndexBuilderPage"

type AppRoute = "/" | "/vector-index"

function resolveRoute(pathname: string): AppRoute {
  return pathname === "/vector-index" ? "/vector-index" : "/"
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

  return (
    <DashboardHome
      connectionState={connectionState}
      connectionMessage={connectionMessage}
      setConnectionState={setConnectionState}
      setConnectionMessage={setConnectionMessage}
      onOpenVectorIndexBuilder={() => navigate("/vector-index")}
    />
  )
}

export default App
