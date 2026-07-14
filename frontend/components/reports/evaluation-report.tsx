import { SessionReport } from "@/types";
import { CheckCircle2, AlertTriangle, BookOpen, Target, ArrowRight } from "lucide-react";

export function EvaluationReport({ report }: { report: SessionReport }) {
  return (
    <div className="flex-1 overflow-y-auto bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-8 pb-12">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-foreground tracking-tight">Session Evaluation Report</h1>
          <p className="text-lg text-muted-foreground">Here is the analysis of your teaching session.</p>
        </div>

        {/* Score Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-card border border-border/50 rounded-2xl p-6 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Understanding Score</p>
              <h2 className="text-5xl font-bold text-blue-500">{report.understanding_score}%</h2>
            </div>
            <div className="w-20 h-20 rounded-full border-8 border-blue-500/20 border-t-blue-500 flex items-center justify-center shrink-0">
              <Target className="text-blue-500" />
            </div>
          </div>
          
          <div className="bg-card border border-border/50 rounded-2xl p-6 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Mastery Level</p>
              <h2 className="text-3xl font-bold text-emerald-400">{report.mastery_level}</h2>
              <p className="text-sm text-muted-foreground mt-2">Achieved Level {report.difficulty_achieved}</p>
            </div>
            <div className="w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-10 h-10 text-emerald-500" />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Strengths & Mastered */}
          <div className="space-y-6">
            <div className="bg-card border border-border/50 rounded-2xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <CheckCircle2 className="text-emerald-500" size={20} />
                Mastered Concepts
              </h3>
              <ul className="space-y-3">
                {report.concepts_mastered.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-muted-foreground">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="bg-card border border-border/50 rounded-2xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <SparklesIcon className="text-blue-400" />
                Key Strengths
              </h3>
              <ul className="space-y-3">
                {report.strengths.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-muted-foreground">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Gaps & Misconceptions */}
          <div className="space-y-6">
            {(report.misconceptions_detected.length > 0 || report.high_priority_learning_gaps.length > 0) && (
              <div className="bg-card border border-border/50 rounded-2xl p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                  <AlertTriangle className="text-amber-500" size={20} />
                  Areas to Clarify
                </h3>
                <ul className="space-y-3">
                  {[...report.misconceptions_detected, ...report.high_priority_learning_gaps].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-muted-foreground">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-2 shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Roadmap */}
            <div className="bg-card border border-border/50 rounded-2xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <BookOpen className="text-purple-400" size={20} />
                Recommended Roadmap
              </h3>
              <div className="space-y-4">
                {report.personalized_roadmap.map((item, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center text-xs font-bold shrink-0">
                      {i + 1}
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed mt-0.5">{item}</p>
                  </div>
                ))}
              </div>
              
              {report.recommended_exercises.length > 0 && (
                <div className="mt-6 pt-6 border-t border-border/50">
                  <h4 className="text-sm font-semibold text-foreground mb-3">Suggested Exercises</h4>
                  <ul className="space-y-2">
                    {report.recommended_exercises.map((item, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer group">
                        <ArrowRight className="w-4 h-4 text-purple-400 group-hover:translate-x-1 transition-transform" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
    </svg>
  );
}
