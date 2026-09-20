"use client";

import { useMemo, useRef, useEffect } from "react";
import { useThree, useFrame } from "@react-three/fiber";
import { Vector3, Group } from "three";
import { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { ConceptAssessment } from "@/types/gapReport";
import ConceptNode from "./ConceptNode";
import ConceptConnections from "./ConceptConnections";

interface KnowledgeMapSceneProps {
  concepts: ConceptAssessment[];
  selectedConceptId: string | null;
  onSelectConcept: (conceptId: string) => void;
  controlsRef: React.RefObject<OrbitControlsImpl>;
}

export default function KnowledgeMapScene({
  concepts,
  selectedConceptId,
  onSelectConcept,
  controlsRef,
}: KnowledgeMapSceneProps) {
  const { camera } = useThree();
  const groupRef = useRef<Group>(null);

  // Target camera positions for smooth transitions
  const targetCamPos = useRef<Vector3 | null>(null);
  const targetLookAt = useRef<Vector3 | null>(null);
  const isAnimating = useRef<boolean>(false);

  // Layout positions: Arrange concepts in a 3D circle with vertical oscillation
  const positions = useMemo(() => {
    const posMap = new Map<string, Vector3>();
    const count = concepts.length;
    if (count === 0) return posMap;

    const radius = 28;

    concepts.forEach((concept, index) => {
      const angle = (index / count) * Math.PI * 2;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = Math.sin(index * 1.5) * 8;
      posMap.set(concept.id, new Vector3(x, y, z));
    });

    return posMap;
  }, [concepts]);

  // When selectedConceptId changes, trigger camera animation towards node
  useEffect(() => {
    if (selectedConceptId && positions.has(selectedConceptId)) {
      const nodePos = positions.get(selectedConceptId)!;
      targetLookAt.current = nodePos.clone();

      // Position camera slightly offset from the node towards the origin/above
      const offset = nodePos.clone().normalize().multiplyScalar(24);
      offset.y += 12;
      targetCamPos.current = nodePos.clone().add(offset);
      isAnimating.current = true;
    }
  }, [selectedConceptId, positions]);

  // Smooth camera lerp in frame loop
  useFrame((_, delta) => {
    if (isAnimating.current && targetCamPos.current && targetLookAt.current) {
      const step = Math.min(delta * 4, 1);
      camera.position.lerp(targetCamPos.current, step);

      if (controlsRef.current) {
        controlsRef.current.target.lerp(targetLookAt.current, step);
        controlsRef.current.update();
      } else {
        camera.lookAt(targetLookAt.current);
      }

      if (camera.position.distanceTo(targetCamPos.current) < 0.2) {
        isAnimating.current = false;
      }
    }
  });

  return (
    <group ref={groupRef}>
      {/* Edges / Connections */}
      <ConceptConnections
        concepts={concepts}
        positions={positions}
        selectedConceptId={selectedConceptId}
      />

      {/* Nodes */}
      {concepts.map((concept) => {
        const pos = positions.get(concept.id);
        if (!pos) return null;

        return (
          <ConceptNode
            key={concept.id}
            concept={concept}
            position={[pos.x, pos.y, pos.z]}
            isSelected={selectedConceptId === concept.id}
            onClick={() => onSelectConcept(concept.id)}
          />
        );
      })}
    </group>
  );
}
