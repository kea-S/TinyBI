import { motion } from "framer-motion"
import { User, Bot, Table as TableIcon } from "lucide-react"
import ReactMarkdown from "react-markdown"
import { type Message as ApiMessage } from "@/lib/api"

export type ChatMessageData = ApiMessage & {
  sql?: string | null
  data?: Record<string, unknown>[] | null
}

interface ChatMessageProps {
  message: ChatMessageData
  onInspect: (message: ChatMessageData) => void
}

export function ChatMessage({ message, onInspect }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      <div
        className={`flex size-10 shrink-0 items-center justify-center rounded-full border ${
          isUser
            ? "bg-primary text-primary-foreground border-primary"
            : "bg-card text-foreground border-border"
        }`}
      >
        {isUser ? <User className="size-5" /> : <Bot className="size-5" />}
      </div>

      <div
        className={`flex flex-col gap-2 max-w-[80%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <div
          className={`rounded-2xl px-6 py-4 shadow-sm text-sm leading-relaxed break-words prose prose-sm max-w-none ${
            isUser
              ? "bg-primary text-primary-foreground prose-invert"
              : "bg-card border border-border prose-neutral dark:prose-invert"
          } [&_ul]:list-disc [&_ol]:list-decimal [&_ul]:ml-4 [&_ol]:ml-4 [&_li]:mt-1 [&_strong]:font-bold [&_code]:bg-muted/50 [&_code]:px-1 [&_code]:rounded`}
        >
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Data Badge */}
        {!isUser && (message.sql || message.data) && (
          <button
            onClick={() => onInspect(message)}
            className="flex items-center gap-2 rounded-xl border border-primary/20 bg-primary/5 px-4 py-2 text-xs font-medium text-primary transition-all hover:bg-primary/10 hover:shadow-md"
          >
            <TableIcon className="size-4" />
            Inspect Data Results
          </button>
        )}
      </div>
    </motion.div>
  )
}
