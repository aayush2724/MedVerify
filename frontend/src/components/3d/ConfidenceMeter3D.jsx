import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { useSpring, animated } from '@react-spring/three';
import { Text } from '@react-three/drei';
import * as THREE from 'three';

const VERDICT_COLORS = {
  GENUINE: '#0d9488',
  SUSPICIOUS: '#d97706',
  FAKE: '#dc2626'
};

export default function ConfidenceMeter3D({ confidence = 87, verdict = 'GENUINE' }) {
  const arcRef = useRef();

  // Background arc path (270 degrees)
  const bgCurve = useMemo(() => {
    const curve = new THREE.EllipseCurve(
      0, 0,            // ax, aY
      1.5, 1.5,        // xRadius, yRadius
      Math.PI * 0.75, Math.PI * 2.25,  // aStartAngle, aEndAngle
      false,            // aClockwise
      0                 // aRotation
    );
    return curve;
  }, []);

  const { progress } = useSpring({
    from: { progress: 0 },
    to: { progress: confidence / 100 },
    config: { duration: 1200, easing: t => 1 - Math.pow(1 - t, 4) }
  });

  const color = VERDICT_COLORS[verdict] || VERDICT_COLORS.GENUINE;

  useFrame(() => {
    if (!arcRef.current) return;
    // Animate the filled arc drawing by adjusting draw range
    const maxPoints = arcRef.current.geometry.index ? arcRef.current.geometry.index.count : arcRef.current.geometry.attributes.position.count;
    arcRef.current.geometry.setDrawRange(0, Math.floor(maxPoints * progress.get()));
  });

  return (
    <group>
      {/* Background Arc */}
      <mesh>
        <tubeGeometry args={[bgCurve, 64, 0.05, 8, false]} />
        <meshBasicMaterial color="#a0a0a0" transparent opacity={0.2} />
      </mesh>
      
      {/* Filled Arc */}
      <mesh ref={arcRef}>
        <tubeGeometry args={[bgCurve, 64, 0.055, 8, false]} />
        <meshBasicMaterial color={color} />
      </mesh>
      
      {/* End marker */}
      <animated.mesh
        position={progress.to(p => {
          const angle = Math.PI * 0.75 + (Math.PI * 1.5) * p;
          return [Math.cos(angle) * 1.5, Math.sin(angle) * 1.5, 0];
        })}
      >
        <sphereGeometry args={[0.12, 16, 16]} />
        <meshBasicMaterial color={color} />
      </animated.mesh>
      
      {/* Text Label */}
      <Text
        position={[0, -0.4, 0]}
        font="https://fonts.gstatic.com/s/dmsans/v14/rP2Fp2ywxg089UriI5-g4vlH9VoD8Cmcqbu0-K4.woff"
        fontSize={0.4}
        color="var(--text-primary)"
        anchorX="center"
        anchorY="middle"
      >
        {`${confidence}%`}
      </Text>
      <Text
        position={[0, -0.8, 0]}
        font="https://fonts.gstatic.com/s/dmsans/v14/rP2Fp2ywxg089UriI5-g4vlH9VoD8Cmcqbu0-K4.woff"
        fontSize={0.16}
        color="var(--text-secondary)"
        anchorX="center"
        anchorY="middle"
      >
        CONFIDENCE
      </Text>
    </group>
  );
}
