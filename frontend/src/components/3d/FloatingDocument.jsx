import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGesture } from '@use-gesture/react';
import { MathUtils, CanvasTexture } from 'three';
import { useSpring, animated } from '@react-spring/three';

export default function FloatingDocument() {
  const meshRef = useRef();

  // Create document texture
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');
    
    // Background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 512, 1024);
    
    // Faint lines
    ctx.fillStyle = '#f0f0f0';
    for (let i = 0; i < 20; i++) {
      ctx.fillRect(40, 100 + i * 40, 432, 4);
    }
    
    // Subtle cross
    ctx.fillStyle = '#fff0f0';
    ctx.fillRect(430, 40, 40, 12);
    ctx.fillRect(444, 26, 12, 40);
    
    const tex = new CanvasTexture(canvas);
    return tex;
  }, []);

  const [springs, api] = useSpring(() => ({
    scale: [1, 1, 1],
    rotation: [0, 0, 0],
    config: { mass: 1, tension: 170, friction: 26 }
  }));

  const bind = useGesture({
    onDrag: ({ offset: [x, y] }) => {
      api.start({ rotation: [y / 100, x / 100, 0] });
    },
    onHover: ({ hovering }) => {
      api.start({ 
        scale: hovering ? [1.02, 1.02, 1.02] : [1, 1, 1],
        rotation: hovering ? [0, 0, 0] : undefined
      });
    }
  });

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    // We only apply idle animation if not being dragged/hovered
    const isHovered = springs.scale.animation.to[0] > 1.0;
    if (!isHovered) {
      meshRef.current.position.y = Math.sin(clock.elapsedTime * 0.6) * 0.08;
      meshRef.current.rotation.y = Math.sin(clock.elapsedTime * 0.3) * 0.12;
    }
  });

  return (
    <animated.mesh
      ref={meshRef}
      {...bind()}
      scale={springs.scale}
      rotation={springs.rotation}
      castShadow
      receiveShadow
    >
      <boxGeometry args={[2.4, 3.2, 0.04]} />
      <meshPhysicalMaterial 
        color="#ffffff"
        roughness={0.1}
        metalness={0.0}
        clearcoat={1.0}
        clearcoatRoughness={0.05}
        reflectivity={0.8}
        map={texture}
      />
    </animated.mesh>
  );
}
