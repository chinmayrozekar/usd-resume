"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment } from "@react-three/drei";

function Village() {
  const { scene } = useGLTF("/models/career_street.glb");
  return <primitive object={scene} />;
}

export default function HouseViewer() {
  return (
    <div className="h-screen w-full bg-sky-200">
      <Canvas camera={{ position: [30, 40, 55], fov: 45 }} shadows>
        <Suspense fallback={null}>
          <Village />
          <Environment preset="park" />
        </Suspense>
        <ambientLight intensity={0.7} />
        <directionalLight position={[10, 14, 8]} intensity={1.3} castShadow />
        <OrbitControls target={[0, 2, 0]} />
      </Canvas>
    </div>
  );
}
