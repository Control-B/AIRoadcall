import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";

const templatePreviewUrl = "https://preview-1779364005181565636.vibepreview.com";

export default function TemplatePage() {
  return (
    <div className="min-h-screen bg-roadcall-void text-roadcall-silver">
      <section className="border-b border-roadcall-cyan/10 bg-roadcall-panel/70 px-4 py-4 backdrop-blur-xl sm:px-6">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-semibold text-white transition-colors hover:text-roadcall-cyan"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Roadcall.ai
          </Link>
          <a
            href={templatePreviewUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 text-sm font-semibold text-roadcall-muted transition-colors hover:text-white"
          >
            Open preview in new tab
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </section>

      <iframe
        src={templatePreviewUrl}
        title="Roadcall template preview"
        className="h-[calc(100vh-153px)] w-full border-0 bg-white sm:h-[calc(100vh-129px)]"
      />
    </div>
  );
}