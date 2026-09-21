"use client";

import React, { useRef, useMemo, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Billboard, Text, OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";

interface NodeData {
  id: string;
  name: string;
  position: [number, number, number];
  color: string;
  glowColor: string;
  size: number;
  isGap?: boolean;
  statusText: string;
}

function KnowledgeNetwork() {
  const groupRef = useRef<THREE.Group>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const nodes: NodeData[] = useMemo(
    () => [
      {
        id: "center",
        name: "CONCEPT CORE",
        position: [0, 0, 0],
        color: "#0F2B4A",
        glowColor: "#3A63FF",
        size: 1.5,
        statusText: "ROOT",
      },
      {
        id: "def",
        name: "DEFINITION",
        position: [-3.2, 1.8, 1.2],
        color: "#0F2B4A",
        glowColor: "#0F2B4A",
        size: 1.1,
        statusText: "MASTERED",
      },
      {
        id: "mech",
        name: "MECHANISM",
        position: [3.4, 1.2, -1.0],
        color: "#3A63FF",
        glowColor: "#3A63FF",
        size: 1.2,
        statusText: "DEVELOPING",
      },
      {
        id: "gap",
        name: "EDGE CASES",
        position: [1.8, -2.4, 2.0],
        color: "#FF6B1A",
        glowColor: "#FF6B1A",
        size: 1.3,
        isGap: true,
        statusText: "GAP DETECTED",
      },
      {
        id: "app",
        name: "APPLICATION",
        position: [-2.8, -1.8, -1.5],
        color: "#3A63FF",
        glowColor: "#3A63FF",
        size: 1.1,
        statusText: "DEVELOPING",
      },
      {
        id: "inv",
        name: "INVARIANTS",
        position: [0.5, 3.2, -1.2],
        color: "#3A63FF",
        glowColor: "#3A63FF",
        size: 1.0,
        statusText: "RESOLVED ✓",
      },
    ],
    []
  );

  // Rotate entire network gently
  useFrame((state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.15;
      groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.08;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Dynamic Connection Lines from center to orbital nodes */}
      {nodes.slice(1).map((node) => (
        <ConnectionLine
          key={`line-${node.id}`}
          start={[0, 0, 0]}
          end={node.position}
          color={node.isGap ? "#FF6B1A" : "#3A63FF"}
          isGap={node.isGap}
        />
      ))}

      {/* Cross connections between adjacent nodes */}
      <ConnectionLine start={nodes[1].position} end={nodes[5].position} color="#C4CDD6" />
      <ConnectionLine start={nodes[2].position} end={nodes[3].position} color="#FF6B1A" isGap />
      <ConnectionLine start={nodes[4].position} end={nodes[3].position} color="#FF6B1A" isGap />

      {/* Nodes */}
      {nodes.map((node) => (
        <InteractiveNode
          key={node.id}
          node={node}
          isHovered={hoveredId === node.id}
          onHover={() => setHoveredId(node.id)}
          onUnhover={() => setHoveredId(null)}
        />
      ))}

      {/* Ambient Floating Particles */}
      <FloatingParticles count={60} />
    </group>
  );
}

function InteractiveNode({
  node,
  isHovered,
  onHover,
  onUnhover,
}: {
  node: NodeData;
  isHovered: boolean;
  onHover: () => void;
  onUnhover: () => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!meshRef.current) return;
    if (node.isGap) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2.5) * 0.08;
      meshRef.current.scale.set(
        node.size * pulse * (isHovered ? 1.25 : 1),
        node.size * pulse * (isHovered ? 1.25 : 1),
        node.size * pulse * (isHovered ? 1.25 : 1)
      );
    } else {
      const scale = node.size * (isHovered ? 1.25 : 1);
      meshRef.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <group position={node.position}>
      {/* Node Sphere */}
      <mesh
        ref={meshRef}
        onPointerEnter={(e) => {
          e.stopPropagation();
          onHover();
        }}
        onPointerLeave={() => onUnhover()}
      >
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial
          color={node.color}
          emissive={node.glowColor}
          emissiveIntensity={isHovered ? 0.9 : node.isGap ? 0.7 : 0.4}
          roughness={0.2}
          metalness={0.6}
        />
      </mesh>

      {/* Pulsing Torus Ring for Gap */}
      {node.isGap && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.85, 0.04, 16, 64]} />
          <meshBasicMaterial color="#FF6B1A" transparent opacity={0.8} />
        </mesh>
      )}

      {/* Billboard Text Label */}
      <Billboard follow={true}>
        <Text
          position={[0, 0.95, 0]}
          fontSize={0.36}
          color="#0F2B4A"
          fontWeight="bold"
          anchorX="center"
          anchorY="bottom"
          outlineWidth={0.03}
          outlineColor="#FFFFFF"
        >
          {node.name}
        </Text>
        <Text
          position={[0, 0.65, 0]}
          fontSize={0.24}
          color={node.isGap ? "#FF6B1A" : "#3A63FF"}
          fontWeight="600"
          anchorX="center"
          anchorY="bottom"
          outlineWidth={0.02}
          outlineColor="#FFFFFF"
        >
          {node.statusText}
        </Text>
      </Billboard>
    </group>
  );
}

function ConnectionLine({
  start,
  end,
  color = "#3A63FF",
  isGap = false,
}: {
  start: [number, number, number];
  end: [number, number, number];
  color?: string;
  isGap?: boolean;
}) {
  return (
    <Line
      points={[start, end]}
      color={color}
      lineWidth={isGap ? 2 : 1}
      transparent
      opacity={isGap ? 0.85 : 0.4}
    />
  );
}


function FloatingParticles({ count = 50 }: { count?: number }) {
  const points = useMemo(() => {
    const coords = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      coords[i * 3] = (Math.random() - 0.5) * 16;
      coords[i * 3 + 1] = (Math.random() - 0.5) * 16;
      coords[i * 3 + 2] = (Math.random() - 0.5) * 16;
    }
    return coords;
  }, [count]);

  const geom = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(points, 3));
    return g;
  }, [points]);

  return (
    <points geometry={geom}>
      <pointsMaterial
        size={0.12}
        color="#3A63FF"
        transparent
        opacity={0.5}
        sizeAttenuation
      />
    </points>
  );
}

export function Hero3DScene() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="w-full h-full min-h-[380px] flex items-center justify-center bg-ice/40 rounded-[6px]">
        <span className="font-mono text-xs uppercase tracking-widest text-navy/40 animate-pulse">
          INITIALIZING KNOWLEDGE NETWORK...
        </span>
      </div>
    );
  }

  return (
    <div className="relative w-full h-[420px] md:h-[520px] rounded-[8px] overflow-hidden select-none">
      <Canvas
        camera={{ position: [0, 1.5, 9], fov: 48 }}
        className="w-full h-full"
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.8} />
        <directionalLight position={[10, 15, 10]} intensity={1.2} />
        <pointLight position={[-10, -10, -10]} color="#3A63FF" intensity={0.6} />

        <KnowledgeNetwork />

        <OrbitControls
          enableZoom={false}
          enablePan={false}
          autoRotate={false}
          maxPolarAngle={Math.PI / 1.7}
          minPolarAngle={Math.PI / 3}
        />
      </Canvas>

      {/* Interactive Hint */}
      <div className="absolute bottom-3 right-4 font-mono text-[10px] uppercase tracking-wider text-navy/50 bg-white/80 px-2.5 py-1 rounded-[3px] border border-fog/80 pointer-events-none">
        DRAG TO ROTATE · HOVER TO INSPECT
      </div>
    </div>
  );
}
