import { Suspense } from "react";
import { GapReportPage } from "../(components)/GapReportPage";

export const metadata = {
  title: "Gap Report | Curio AI",
  description: "Explore your knowledge gaps and learning progress with an interactive 3D map.",
};

export default function SessionGapReportPage({
  params,
}: {
  params: { sessionId: string };
}) {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen bg-background text-foreground">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary" />
        </div>
      }
    >
      <GapReportPage initialSessionId={params.sessionId} />
    </Suspense>
  );
}
