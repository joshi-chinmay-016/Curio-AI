"use client";

import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

export interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className = "" }: MarkdownContentProps) {
  // Split content by code blocks: ```lang ... ```
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className={`space-y-3 font-sans text-sm md:text-base leading-relaxed ${className}`}>
      {parts.map((part, index) => {
        if (part.startsWith("```") && part.endsWith("```")) {
          // Extract language and code
          const firstLineBreak = part.indexOf("\n");
          let language = "code";
          let codeContent = "";

          if (firstLineBreak !== -1) {
            language = part.substring(3, firstLineBreak).trim() || "code";
            codeContent = part.substring(firstLineBreak + 1, part.length - 3).trim();
          } else {
            codeContent = part.substring(3, part.length - 3).trim();
          }

          return (
            <CodeBlock
              key={index}
              language={language}
              code={codeContent}
            />
          );
        }

        return <TextBlock key={index} text={part} />;
      })}
    </div>
  );
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard fallback
    }
  };

  return (
    <div className="my-3 rounded-[6px] overflow-hidden border border-navy/30 bg-[#0A1A2E] text-white shadow-sm font-mono text-xs">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#0F2B4A] border-b border-navy/40">
        <span className="text-[11px] font-bold uppercase tracking-wider text-fog">
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[11px] text-fog hover:text-white transition-colors px-2 py-0.5 rounded-[3px] hover:bg-white/10"
          aria-label="Copy code to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-cobalt" />
              <span className="text-cobalt font-semibold">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function TextBlock({ text }: { text: string }) {
  if (!text.trim()) return null;

  // Split into paragraphs by double newlines
  const paragraphs = text.split(/\n\s*\n/);

  return (
    <>
      {paragraphs.map((para, pIdx) => {
        const trimmed = para.trim();
        if (!trimmed) return null;

        // Check if paragraph is a list
        const lines = trimmed.split("\n");
        const isBulletList = lines.every((l) => l.trim().startsWith("- ") || l.trim().startsWith("* "));
        const isNumberedList = lines.every((l) => /^\d+\.\s/.test(l.trim()));

        if (isBulletList) {
          return (
            <ul key={pIdx} className="list-disc pl-5 space-y-1.5">
              {lines.map((l, lIdx) => (
                <li key={lIdx}>{formatInline(l.replace(/^[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }

        if (isNumberedList) {
          return (
            <ol key={pIdx} className="list-decimal pl-5 space-y-1.5">
              {lines.map((l, lIdx) => (
                <li key={lIdx}>{formatInline(l.replace(/^\d+\.\s+/, ""))}</li>
              ))}
            </ol>
          );
        }

        // Standard paragraph
        return (
          <p key={pIdx}>
            {lines.map((line, lIdx) => (
              <React.Fragment key={lIdx}>
                {formatInline(line)}
                {lIdx < lines.length - 1 && <br />}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}

function formatInline(text: string): React.ReactNode[] {
  // Parse inline bold (**bold**), inline code (`code`), and italics (*italic*)
  const tokens = text.split(/(\*\*.*?\*\*|`.*?`|\*.*?\*)/g);

  return tokens.map((tok, i) => {
    if (tok.startsWith("**") && tok.endsWith("**")) {
      return (
        <strong key={i} className="font-bold text-navy">
          {tok.substring(2, tok.length - 2)}
        </strong>
      );
    }
    if (tok.startsWith("`") && tok.endsWith("`")) {
      return (
        <code
          key={i}
          className="font-mono text-[13px] px-1.5 py-0.5 rounded-[3px] bg-ice text-navy border border-fog/80"
        >
          {tok.substring(1, tok.length - 1)}
        </code>
      );
    }
    if (tok.startsWith("*") && tok.endsWith("*")) {
      return (
        <em key={i} className="italic">
          {tok.substring(1, tok.length - 1)}
        </em>
      );
    }
    return tok;
  });
}
