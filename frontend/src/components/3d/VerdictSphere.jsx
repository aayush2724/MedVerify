import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { useSpring, animated } from '@react-spring/three';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

const VERDICT_COLORS = {
  GENUINE: { color: '#f0fdfb', emissive: '#0d9488' },
  SUSPICIOUS: { color: '#fffbeb', emissive: '#d97706' },
  FAKE: { color: '#fef2f2', emissive: '#dc2626' }
};

export default function VerdictSphere({ verdict = 'GENUINE' }) {
  const meshRef = useRef();
  const materialRef = useRef();

  const colors = VERDICT_COLORS[verdict] || VERDICT_COLORS.GENUINE;

  const { scale } = useSpring({
    from: { scale: 0 },
    to: { scale: 1 },
    config: { stiffness: 80, damping: 12 }
  });

  useFrame(({ clock }) => {
    if (meshRef.current && materialRef.current) {
      const t = clock.elapsedTime;
      // Breathe effect on scale
      const breathe = 1.0 + Math.sin(t * 1.5) * 0.02;
      meshRef.current.scale.set(breathe, breathe, breathe);
      
      // Pulse emissive
      materialRef.current.emissiveIntensity = 0.15 + Math.sin(t * 2.0) * 0.05;
    }
  });

  // Simple fresnel shader material can be added here, but MeshPhysicalMaterial works beautifully with clearcoat
  return (
    <>
      <OrbitControls autoRotate enableZoom={false} autoRotateSpeed={2} />
      <animated.mesh ref={meshRef} scale={scale}>
        <sphereGeometry args={[1.8, 64, 64]} />
        <meshPhysicalMaterial 
          ref={materialRef}
          color={colors.color}
          emissive={colors.emissive}
          emissiveIntensity={0.15}
          roughness={0.1}
          metalness={0.05}
          clearcoat={1.0}
        />
      </animated.mesh>
    </>
  );
}
