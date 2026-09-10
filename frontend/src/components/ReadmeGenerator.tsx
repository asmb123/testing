import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Check,
  Code,
  Copy,
  FileText,
  GitPullRequest,
  Link2,
  Loader2,
  ExternalLink,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type ReadmeResponse = {
  status: "awaiting_review" | "completed";
  session_id: string;
  readme: string;
  message?: string;
};

type ReadmeGeneratorProps = {
  onGenerate: (repoUrl: string) => Promise<ReadmeResponse>;
  onReview: (sessionId: string, satisfied: boolean, feedback: string) => Promise<ReadmeResponse>;
  onCreatePullRequest: (repoUrl: string, readme: string) => Promise<PullRequestResponse>;
};

export type PullRequestResponse = {
  url: string;
  branch: string;
};

const markdownComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => <h1 className="text-2xl font-semibold mb-4">{children}</h1>,
  h2: ({ children }: { children?: React.ReactNode }) => <h2 className="text-xl font-semibold mt-6 mb-3">{children}</h2>,
  h3: ({ children }: { children?: React.ReactNode }) => <h3 className="text-lg font-semibold mt-5 mb-2">{children}</h3>,
  p: ({ children }: { children?: React.ReactNode }) => <p className="leading-7 mb-3">{children}</p>,
  ul: ({ children }: { children?: React.ReactNode }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
  ol: ({ children }: { children?: React.ReactNode }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
  code: ({ children }: { children?: React.ReactNode }) => <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{children}</code>,
};

export function ReadmeGenerator({ onGenerate, onReview, onCreatePullRequest }: ReadmeGeneratorProps) {
  const [linkInput, setLinkInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");
  const [tab, setTab] = useState<"preview" | "raw">("preview");
  const [copied, setCopied] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [feedback, setFeedback] = useState("");
  const [awaitingReview, setAwaitingReview] = useState(false);
  const [status, setStatus] = useState("");
  const [pullRequest, setPullRequest] = useState<PullRequestResponse | null>(null);

  async function handleSubmit() {
    if (!linkInput.trim() || loading) return;
    setLoading(true);
    setResult("");
    setFeedback("");
    setStatus("");
    setSessionId("");
    setAwaitingReview(false);
    setPullRequest(null);
    try {
      const data = await onGenerate(linkInput.trim());
      setResult(data.readme);
      setSessionId(data.session_id);
      setAwaitingReview(data.status === "awaiting_review");
      setStatus(data.message || "README ready for review.");
      setTab("preview");
    } catch (error) {
      setResult(error instanceof Error ? error.message : "Failed to generate README.");
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(satisfied: boolean) {
    if (loading || !sessionId || (!satisfied && !feedback.trim())) return;
    setLoading(true);
    setStatus(satisfied ? "Finalizing your README..." : "Updating your README with feedback...");
    try {
      const data = await onReview(sessionId, satisfied, feedback.trim());
      setResult(data.readme);
      setSessionId(data.session_id);
      setAwaitingReview(data.status === "awaiting_review");
      setFeedback("");
      setStatus(data.status === "completed" ? "README approved and ready to use." : data.message || "Updated README ready for review.");
      setTab("preview");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not update the README.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(result);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  async function handleOpenPR() {
    if (loading) return;
    setLoading(true);
    setStatus("Creating a branch and pull request...");
    try {
      const pullRequest = await onCreatePullRequest(linkInput.trim(), result);
      setPullRequest(pullRequest);
      window.open(pullRequest.url, "_blank", "noopener,noreferrer");
      setStatus(`Pull request opened from ${pullRequest.branch}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not open the pull request.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full space-y-4">
      <div className="relative group">
        <div className="absolute -inset-0.5 bg-linear-to-r from-primary/20 to-primary/5 rounded-lg blur opacity-50 group-hover:opacity-100 transition duration-500" />
        <div className="relative flex items-center gap-2 bg-card border border-border/50 rounded-lg p-2">
          <Link2 className="w-5 h-5 text-muted-foreground ml-2 shrink-0" />
          <Input type="url" placeholder="https://github.com/username/repository" value={linkInput} onChange={(event) => setLinkInput(event.target.value)} onKeyDown={(event) => event.key === "Enter" && handleSubmit()} className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none" />
          <Button onClick={handleSubmit} disabled={loading || !linkInput.trim()} size="sm" className="mr-1 shrink-0">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate"}
          </Button>
        </div>
      </div>

      {result && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/40 bg-muted/30">
              <div className="flex items-center gap-2.5">
                <div className="flex gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-border/60" /><span className="w-2.5 h-2.5 rounded-full bg-border/60" /><span className="w-2.5 h-2.5 rounded-full bg-border/60" /></div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground gap-1.5">{copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}{copied ? "Copied!" : "Copy"}</Button>
                <Button size="sm" onClick={handleOpenPR} disabled={loading || Boolean(pullRequest)} className="h-7 px-2.5 text-xs gap-1.5 bg-green-600 hover:bg-green-700 text-white border-0"><GitPullRequest className="w-3.5 h-3.5" />{pullRequest ? "PR opened" : "Open PR"}</Button>
              </div>
            </div>
            <div className="flex border-b border-border/40 bg-muted/20 px-4">
              {(["preview", "raw"] as const).map((view) => <button key={view} onClick={() => setTab(view)} className={cn("flex items-center gap-1.5 text-xs py-2 px-3 border-b-2 transition-colors capitalize", tab === view ? "border-foreground text-foreground font-medium" : "border-transparent text-muted-foreground hover:text-foreground")}>{view === "preview" ? <FileText className="w-3 h-3" /> : <Code className="w-3 h-3" />}{view}</button>)}
            </div>
            {tab === "preview" && <div className="px-6 py-5 max-h-[560px] overflow-y-auto prose-sm"><ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{result}</ReactMarkdown></div>}
            {tab === "raw" && <pre className="px-6 py-5 text-xs font-mono leading-relaxed text-muted-foreground max-h-[560px] overflow-auto whitespace-pre-wrap break-words bg-muted/10">{result}</pre>}
          </div>

          {pullRequest && <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm"><span className="text-green-700 dark:text-green-300">Pull request created successfully.</span><a href={pullRequest.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 font-medium text-green-700 hover:underline dark:text-green-300">View PR <ExternalLink className="h-3.5 w-3.5" /></a></div>}

          {sessionId && <div className="mt-4 rounded-lg border border-border/50 bg-card p-4 space-y-3">
            <div><p className="text-sm font-medium">{awaitingReview ? "Is this README satisfactory?" : "README approved"}</p><p className="text-xs text-muted-foreground mt-1">{status || "Review the generated documentation before you use it."}</p></div>
            {awaitingReview && <><textarea value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="What should be improved?" className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50" disabled={loading} /><div className="flex flex-wrap justify-end gap-2"><Button variant="outline" onClick={() => handleReview(false)} disabled={loading || !feedback.trim()}>{loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Revise README"}</Button><Button onClick={() => handleReview(true)} disabled={loading}>Looks good</Button></div></>}
          </div>}
        </div>
      )}
    </div>
  );
}
