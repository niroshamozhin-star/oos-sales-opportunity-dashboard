import { useState, useRef, useEffect } from "react";
import { Bot, Send, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { askAssistant, resetAssistant } from "../api/client";
import { PageHeader, ErrorBanner } from "../components/shared";

const SUGGESTED_PROMPTS = [
  "Show me recent OOS opportunities in Texas.",
  "Give me details for Global Carrier Logistics LLC.",
  "Create an outreach message for Global Carrier Logistics LLC.",
];

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  error?: boolean;
}

export default function AiAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Every visit to this page starts a genuinely fresh Foundry conversation -
  // otherwise leftover context from an earlier, unrelated session (or from
  // backend testing traffic) can silently bleed into new answers, since the
  // backend threads consecutive questions via previous_response_id to
  // support real follow-ups like "next" within one sitting.
  useEffect(() => {
    resetAssistant().catch(() => {});
  }, []);

  const send = async (question: string) => {
    if (!question.trim() || loading) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await askAssistant(question);
      if (!res.available) {
        setMessages((m) => [...m, {
          role: "assistant",
          text: res.error ?? "AI Assistant is temporarily unavailable. Dashboard functionality is still available.",
          error: true,
        }]);
      } else {
        setMessages((m) => [...m, { role: "assistant", text: res.answer ?? "" }]);
      }
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "AI Assistant is temporarily unavailable. Dashboard functionality is still available.", error: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <PageHeader title="AI Sales Assistant" subtitle="Ask about FMCSA Out-of-Service carrier opportunities. Powered by the Azure AI Foundry Agent." />

      <div className="flex-1 bg-white border border-slate-200 rounded-xl p-5 overflow-y-auto mb-4">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-4">
            <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center">
              <Bot className="w-7 h-7 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-700">Ask about OOS opportunities, carrier details, or outreach messages.</p>
              <p className="text-xs text-slate-400 mt-1">This assistant only answers questions within the FMCSA OOS sales scope.</p>
            </div>
            <div className="grid grid-cols-3 gap-2 max-w-3xl">
              {SUGGESTED_PROMPTS.map((p) => (
                <button key={p} onClick={() => send(p)}
                  className="flex items-start gap-2 text-left text-xs text-slate-600 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg px-3 py-2">
                  <Sparkles className="w-3.5 h-3.5 text-blue-500 shrink-0 mt-0.5" />
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              {m.error ? (
                <div className="max-w-lg"><ErrorBanner message={m.text} /></div>
              ) : m.role === "user" ? (
                <div className="max-w-lg rounded-2xl px-4 py-2.5 text-base bg-blue-600 text-white whitespace-pre-wrap">
                  {m.text}
                </div>
              ) : (
                <div className="max-w-2xl rounded-2xl px-4 py-2.5 text-base bg-slate-100 text-slate-900 font-medium markdown-chat">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 text-slate-700 rounded-2xl px-4 py-2.5 text-base">Thinking...</div>
            </div>
          )}
        </div>
        <div ref={bottomRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about an OOS opportunity, carrier, or outreach message..."
          className="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 text-base text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button type="submit" disabled={loading || !input.trim()}
          className="flex items-center gap-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg px-4 py-2.5 disabled:opacity-50 hover:bg-blue-700">
          <Send className="w-4 h-4" /> Send
        </button>
      </form>
    </div>
  );
}
