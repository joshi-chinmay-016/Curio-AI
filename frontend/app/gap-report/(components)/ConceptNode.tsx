"use client";

import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Mesh } from "three";
import { Text, Billboard } from "@react-three/drei";
import { ConceptAssessment } from "@/types/gapReport";

interface ConceptNodeProps {
  concept: ConceptAssessment;
  position: [number, number, number];
  isSelected: boolean;
  onClick: () => void;
}

export default function ConceptNode({
  concept,
  position,
  isSelected,
  onClick,
}: ConceptNodeProps) {
  const meshRef = useRef<Mesh>(null);
  const [isHovered, setIsHovered] = useState(false);

  // Determine node appearance based on status
  const getNodeConfig = () => {
    switch (concept.status) {
      case "STRONG":
        return {
          color: "#10b981", // green
          glowColor: "#10b981",
          baseSize: 1.3,
        };
      case "DEVELOPING":
        return {
          color: "#f59e0b", // amber
          glowColor: "#f59e0b",
          baseSize: 1.1,
        };
      case "GAP":
        return {
          color: "#ef4444", // red
          glowColor: "#ef4444",
          baseSize: 1.3,
        };
      case "RESOLVED":
        return {
          color: "#06b6d4", // cyan
          glowColor: "#06b6d4",
          baseSize: 1.1,
        };
      case "MISCONCEPTION":
        return {
          color: "#d946ef", // fuchsia
          glowColor: "#d946ef",
          baseSize: 1.3,
        };
      default:
        return {
          color: "#64748b",
          glowColor: "#64748b",
          baseSize: 1.1,
        };
    }
  };

  const config = getNodeConfig();
  const targetScale = isHovered || isSelected ? config.baseSize * 1.35 : config.baseSize;

  const baseScaleRef = useRef(config.baseSize);

  // Smooth animation loop for scale, rotation, and pulsing
  useFrame((state, delta) => {
    if (!meshRef.current) return;

    // Smoothly lerp base scale towards target (hover / selection)
    baseScaleRef.current += (targetScale - baseScaleRef.current) * Math.min(delta * 6, 1);
    let currentScale = baseScaleRef.current;

    // Gentle, subtle breathing effect for gaps & misconceptions (calm rhythm and minimal amplitude)
    if (concept.status === "GAP" || concept.status === "MISCONCEPTION") {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 1.2) * 0.025;
      currentScale *= pulse;
    }

    meshRef.current.scale.set(currentScale, currentScale, currentScale);

    // Subtle idle rotation for visual interest
    meshRef.current.rotation.y += delta * 0.2;
  });

  return (
    <group position={position}>
      {/* Interactive Core Sphere */}
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        onPointerEnter={(e) => {
          e.stopPropagation();
          document.body.style.cursor = "pointer";
          setIsHovered(true);
        }}
        onPointerLeave={() => {
          document.body.style.cursor = "auto";
          setIsHovered(false);
        }}
        castShadow
        receiveShadow
      >
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial
          color={config.color}
          emissive={config.color}
          emissiveIntensity={isSelected ? 0.9 : isHovered ? 0.7 : 0.4}
          metalness={0.5}
          roughness={0.25}
        />
      </mesh>

      {/* Glow Ring for GAP and MISCONCEPTION */}
      {(concept.status === "GAP" || concept.status === "MISCONCEPTION" || isSelected) && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[1.5, 0.08, 16, 64]} />
          <meshBasicMaterial
            color={config.glowColor}
            transparent
            opacity={isSelected ? 0.9 : isHovered ? 0.7 : 0.4}
          />
        </mesh>
      )}

      {/* Billboard label displaying concept name and score */}
      <Billboard follow={true} lockX={false} lockY={false} lockZ={false}>
        <Text
          position={[0, 2.5, 0]}
          fontSize={0.85}
          color={isHovered || isSelected ? "#ffffff" : "#e2e8f0"}
          maxWidth={12}
          textAlign="center"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.08}
          outlineColor="#0f172a"
        >
          {concept.name}
        </Text>

        <Text
          position={[0, 1.6, 0]}
          fontSize={0.6}
          color={
            concept.score >= 80
              ? "#34d399"
              : concept.score >= 60
              ? "#fbbf24"
              : "#f87171"
          }
          maxWidth={6}
          textAlign="center"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.06}
          outlineColor="#0f172a"
        >
          {`${concept.score}%`}
        </Text>
      </Billboard>
    </group>
  );
}
