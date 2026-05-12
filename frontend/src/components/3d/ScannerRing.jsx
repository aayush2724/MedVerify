import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { MathUtils } from 'three';
import { useSpring, animated } from '@react-spring/three';

export default function ScannerRing() {
  const groupRef = useRef();
  const ring1 = useRef();
  const ring2 = useRef();
  const ring3 = useRef();

  const { scale } = useSpring({
    from: { scale: 0 },
    to: { scale: 1 },
    config: { duration: 800, easing: t => t * (2 - t) } // easeOut
  });

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    if (ring1.current) ring1.current.rotation.x += 0.008;
    if (ring2.current) ring2.current.rotation.y += 0.012;
    if (ring3.current) {
        ring3.current.rotation.z += 0.006;
        ring3.current.material.opacity = Math.sin(t * 2) * 0.3 + 0.7;
    }
  });

  return (
    <animated.group ref={groupRef} scale={scale}>
      <spotLight position={[0, 5, 0]} angle={0.3} penumbra={1} intensity={1.5} color="#0d9488" />
      
      <mesh ref={ring1}>
        <torusGeometry args={[1.2, 0.015, 16, 100]} />
        <meshBasicMaterial color="#0d9488" />
      </mesh>
      
      <mesh ref={ring2} rotation={[Math.PI / 3, 0, 0]}>
        <torusGeometry args={[1.6, 0.015, 16, 100]} />
        <meshBasicMaterial color="#1a1a1a" />
      </mesh>
      
      <mesh ref={ring3} rotation={[0, Math.PI / 4, 0]}>
        <torusGeometry args={[2.0, 0.015, 16, 100]} />
        <meshBasicMaterial color="#0d9488" transparent opacity={0.8} />
      </mesh>
    </animated.group>
  );
}
