import { useState, useRef, useCallback, useEffect } from "react"
import { Send, Sparkles, Bot } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  submitQuery,
} from "@/lib/api"
import { DataModal } from "@/components/builder/DataModal"
import { ChatMessage, type ChatMessageData } from "@/components/builder/ChatMessage"

type QueryState = "idle" | "loading" | "error"

const QUICK_START_EXAMPLES = [
  "How many accounts who choose issuance after transaction are staying in East Bohemia region?",
  "What is the percentage of loan amount that has been fully paid with no issue.",
  "For loan amount less than USD100,000, what is the percentage of accounts that is still running with no issue.",
]

export function QueryPage() {
  const [messages, setMessages] = useState<ChatMessageData[]>([])
  const [input, setInput] = useState("")
  const [queryState, setQueryState] = useState<QueryState>("idle")
  const [errorMessage, setErrorMessage] = useState("")
  
  // For the modal
  const [modalOpen, setModalOpen] = useState(false)
  const [activeModalData, setActiveModalData] = useState<{ sql?: string | null, data?: Record<string, unknown>[] | null } | null>(null)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = Math.min(el.scrollHeight, 120) + "px"
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, queryState])

  const handleExampleClick = (example: string) => {
    setInput(example)
    // Small delay to ensure state update before focus, though usually sync in React 18
    setTimeout(() => {
      textareaRef.current?.focus()
      autoResize()
    }, 0)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmedInput = input.trim()
    if (!trimmedInput || queryState === "loading") return

    const userMsg: ChatMessageData = { role: "user", content: trimmedInput }
    const currentMessages = [...messages, userMsg]
    setMessages(currentMessages)
    setInput("")
    setQueryState("loading")
    setErrorMessage("")

    try {
      const response = await submitQuery({ 
        messages: currentMessages.map(({ role, content }) => ({ role, content })),
        local: true
      })
      
      if (typeof response === "string") throw new Error("Invalid response")

      const assistantMsg: ChatMessageData = {
        role: "assistant",
        content: response.message,
        sql: response.sql,
        data: response.data,
      }
      
      setMessages((prev) => [...prev, assistantMsg])
      setQueryState("idle")
    } catch (error) {
      setQueryState("error")
      setErrorMessage(error instanceof Error ? error.message : "Query failed")
    }
  }

  function handleInspect(msg: ChatMessageData) {
    setActiveModalData({ sql: msg.sql, data: msg.data })
    setModalOpen(true)
  }

  return (
    <div className="flex flex-col h-full bg-background relative">
      {/* Message History */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth pb-60">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-8">
            <div className="space-y-4 opacity-50">
              <div className="mx-auto size-16 rounded-3xl bg-muted flex items-center justify-center">
                <Bot className="size-8" />
              </div>
              <div className="space-y-1">
                <h2 className="text-xl font-semibold">Welcome to TinyBI</h2>
                <p className="text-sm max-w-xs text-muted-foreground">
                  Ask questions about your data in natural language.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl w-full">
              {QUICK_START_EXAMPLES.map((example, i) => (
                <button
                  key={i}
                  onClick={() => handleExampleClick(example)}
                  className="p-4 rounded-2xl border border-border bg-card hover:bg-accent/50 hover:border-primary/50 transition-all text-left text-sm group"
                >
                  <p className="text-muted-foreground group-hover:text-foreground transition-colors">
                    {example}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} onInspect={handleInspect} />
          ))}
        </AnimatePresence>

        {queryState === "loading" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
            <div className="flex size-10 items-center justify-center rounded-full border bg-card text-foreground border-border">
              <Bot className="size-5" />
            </div>
            <div className="flex gap-1 mt-4">
              {[0, 1, 2].map((n) => (
                <motion.div
                  key={n}
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ repeat: Infinity, duration: 1, delay: n * 0.2 }}
                  className="size-2 rounded-full bg-primary"
                />
              ))}
            </div>
          </motion.div>
        )}

        {queryState === "error" && (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive text-center">
            {errorMessage}
          </div>
        )}
      </div>

      {/* Input Section */}
      <footer className="absolute bottom-0 left-0 right-0 p-8 bg-gradient-to-t from-background via-background to-transparent z-10">
        <form onSubmit={handleSubmit} className="mx-auto max-w-4xl relative group">
          <div className="absolute inset-0 -m-1 rounded-[2rem] bg-gradient-to-r from-primary/20 to-primary/10 opacity-0 blur-xl transition-opacity group-focus-within:opacity-100" />
          <div className="relative flex items-end gap-3 rounded-[1.5rem] border border-border bg-card p-2 shadow-lg transition-all focus-within:ring-2 focus-within:ring-primary/20">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                autoResize()
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit(e)
                }
              }}
              placeholder="Ask your data anything..."
              rows={1}
              className="flex-1 min-h-[40px] max-h-[120px] border-none bg-transparent text-lg shadow-none focus-visible:ring-0 resize-none overflow-y-auto py-3 px-4"
              disabled={queryState === "loading"}
            />
            <Button 
              type="submit" 
              size="lg"
              aria-label="Submit"
              disabled={queryState === "loading" || !input.trim()}
              className="rounded-xl size-12 p-0 shrink-0"
            >
              <Send className="size-5" />
            </Button>
          </div>
        </form>
      </footer>

      {/* Data Modal */}
      <DataModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        sql={activeModalData?.sql}
        data={activeModalData?.data}
      />
    </div>
  )
}









