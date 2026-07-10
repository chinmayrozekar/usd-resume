"use client";

import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { CHAPTERS } from "@/lib/resume-data";

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

/** Reads the scroll-progress ref every frame and smoothly dollies the
 * camera along the street to match, instead of snapping to each chapter. */
export default function CameraRig({ progressRef }: { progressRef: React.RefObject<number> }) {
  const { camera } = useThree();
  const targetPos = useRef(new THREE.Vector3());
  const targetLook = useRef(new THREE.Vector3());
  const currentLook = useRef(new THREE.Vector3(0, 3, 0));

  useFrame(() => {
    const progress = progressRef.current ?? 0;
    const chapterFloat = progress * (CHAPTERS.length - 1);
    const i = Math.max(0, Math.min(CHAPTERS.length - 2, Math.floor(chapterFloat)));
    const t = chapterFloat - i;
    const x = lerp(CHAPTERS[i].cameraX, CHAPTERS[i + 1].cameraX, t);

    targetPos.current.set(x - 14, 11, 19);
    targetLook.current.set(x, 6, 0);

    camera.position.lerp(targetPos.current, 0.14);
    currentLook.current.lerp(targetLook.current, 0.14);
    camera.lookAt(currentLook.current);
  });

  return null;
}
