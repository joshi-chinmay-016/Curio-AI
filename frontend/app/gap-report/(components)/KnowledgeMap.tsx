"use client";

import { useRef, Suspense, forwardRef, useImperativeHandle } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { Vector3 } from "three";
import { GapReport } from "@/types/gapReport";
import KnowledgeMapScene from "./KnowledgeMapScene";

export interface KnowledgeMapHandle {
  resetView: () => void;
}

interface KnowledgeMapProps {
  report: GapReport;
  selectedConceptId: string | null;
  onSelectConcept: (conceptId: string) => void;
  filterMode: "all" | "gaps";
}

const KnowledgeMap = forwardRef<KnowledgeMapHandle, KnowledgeMapProps>(
  ({ report, selectedConceptId, onSelectConcept, filterMode }, ref) => {
    const controlsRef = useRef<OrbitControlsImpl>(null);

    useImperativeHandle(ref, () => ({
      resetView: () => {
        if (controlsRef.current) {
          controlsRef.current.reset();
          controlsRef.current.target.set(0, 0, 0);
          controlsRef.current.object.position.set(0, 20, 60);
          controlsRef.current.update();
        }
      },
    }));

    const conceptsToShow =
      filterMode === "gaps"
        ? report.concepts.filter(
            (c) =>
              c.status === "GAP" ||
              c.status === "MISCONCEPTION" ||
              report.gaps.some((g) => g.conceptId === c.id)
          )
        : report.concepts;

    return (
      <div className="w-full h-full bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 relative overflow-hidden select-none">
        <Canvas
          camera={{
            position: [0, 20, 60],
            fov: 55,
          }}
          gl={{ antialias: true }}
          onPointerMissed={() => {
            // Click on empty space deselects
          }}
        >
          {/* Background color */}
          <color attach="background" args={["#090d16"]} />

          {/* Lighting */}
          <ambientLight intensity={0.7} />
          <pointLight position={[60, 60, 60]} intensity={1.2} />
          <pointLight position={[-60, -40, 50]} intensity={0.6} color="#60a5fa" />
          <pointLight position={[0, -50, -40]} intensity={0.4} color="#818cf8" />

          {/* Stars background */}
          <Stars
            radius={180}
            depth={60}
            count={4000}
            factor={4}
            saturation={0.5}
            fade
            speed={0.3}
          />

          {/* 3D Scene */}
          <Suspense fallback={null}>
            <KnowledgeMapScene
              concepts={conceptsToShow}
              selectedConceptId={selectedConceptId}
              onSelectConcept={onSelectConcept}
              controlsRef={controlsRef}
            />
          </Suspense>

          {/* Interactive Camera Controls */}
          <OrbitControls
            ref={controlsRef}
            enableZoom={true}
            enablePan={true}
            enableRotate={true}
            enableDamping={true}
            dampingFactor={0.08}
            autoRotate={false}
            minDistance={15}
            maxDistance={220}
          />
        </Canvas>

        {/* User Interaction Guide */}
        <div className="absolute bottom-4 left-4 text-xs text-muted-foreground/70 pointer-events-none bg-background/40 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-border/40">
          Drag to rotate • Scroll to zoom • Click node to inspect
        </div>
      </div>
    );
  }
);

KnowledgeMap.displayName = "KnowledgeMap";

export default KnowledgeMap;
