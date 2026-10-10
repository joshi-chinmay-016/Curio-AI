import { Suspense } from "react";
import { GapReportPage } from "./(components)/GapReportPage";
import { ProtectedRoute } from "@/components/curio/auth/ProtectedRoute";

export const metadata = {
  title: "Gap Report | Curio AI",
  description: "Explore your knowledge gaps and learning progress with an interactive 3D map.",
};

export default function Page() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<GapReportLoading />}>
        <GapReportPage />
      </Suspense>
    </ProtectedRoute>
  );
}

function GapReportLoading() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background text-foreground">
      <div className="text-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary mx-auto" />
        <p className="text-sm text-muted-foreground">Building your knowledge map...</p>
      </div>
    </div>
  );
}
