"use client";

import { Suspense, useEffect, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF, Environment } from "@react-three/drei";
import Image from "next/image";
import * as THREE from "three";
import CameraRig from "./CameraRig";
import { CHAPTERS } from "@/lib/resume-data";

function Street() {
  const { scene } = useGLTF("/models/career_street.glb");
  const waterMaps = useRef<THREE.Texture[]>([]);

  useEffect(() => {
    const maps: THREE.Texture[] = [];
    scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const mat of materials) {
        const standard = mat as THREE.MeshStandardMaterial;
        if (standard.name === "Water" && standard.map) {
          standard.map.wrapS = THREE.RepeatWrapping;
          standard.map.wrapT = THREE.RepeatWrapping;
          maps.push(standard.map);
        }
      }
    });
    waterMaps.current = maps;
  }, [scene]);

  useFrame((_, delta) => {
    for (const map of waterMaps.current) {
      map.offset.x = (map.offset.x + delta * 0.04) % 1;
      map.offset.y = (map.offset.y + delta * 0.025) % 1;
    }
  });

  return <primitive object={scene} />;
}

const LOGO_STYLE: Record<string, { label: string; color: string }> = {
  rit: { label: "RIT", color: "#F76900" },
  amd: { label: "AMD", color: "#000000" },
  siemens: { label: "SIEMENS", color: "#008A93" },
};

function ChapterCard({ chapter }: { chapter: (typeof CHAPTERS)[number] }) {
  const align = chapter.kind === "hero" ? "items-start" : "items-start";
  const logo = chapter.logo ? LOGO_STYLE[chapter.logo] : undefined;
  return (
    <section
      id={chapter.id}
      className={`relative flex h-screen w-full flex-col justify-center px-8 md:px-20 ${align}`}
    >
      <div className="max-w-md rounded-2xl bg-black/55 p-6 text-white backdrop-blur-sm md:p-8">
        {chapter.dates && (
          <div className="mb-2 text-sm font-medium tracking-wide text-emerald-300">
            {chapter.dates}
          </div>
        )}
        {logo && (
          <div
            className="mb-3 inline-block rounded-md bg-white px-3 py-1 text-sm font-extrabold tracking-wide"
            style={{ color: logo.color }}
          >
            {logo.label}
          </div>
        )}
        {chapter.kind === "hero" ? (
          <>
            <div className="flex items-center gap-4">
              <div className="text-5xl font-black leading-none text-emerald-300 md:text-6xl">
                Hej!
              </div>
              <Image
                src="/images/portrait.png"
                alt="Chinmay Rozekar"
                width={96}
                height={96}
                priority
                className="h-16 w-16 rounded-full object-cover ring-2 ring-emerald-300/70 md:h-20 md:w-20"
              />
            </div>
            <p className="mt-3 text-xl font-medium text-white md:text-2xl">
              Can&apos;t wait to meet you.
            </p>
            <p className="mt-1 text-xl font-medium text-white md:text-2xl">
              I am {chapter.title}
            </p>
          </>
        ) : (
          <h2 className="text-3xl font-bold md:text-4xl">{chapter.title}</h2>
        )}
        {chapter.subtitle && (
          <p className="mt-2 text-base text-zinc-300 md:text-lg">{chapter.subtitle}</p>
        )}
        {chapter.bullets && (
          <ul className="mt-4 space-y-2 text-sm text-zinc-200 md:text-base">
            {chapter.bullets.map((bullet) => (
              <li key={bullet} className="flex gap-2">
                <span className="text-emerald-300">▸</span>
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
        )}
        {chapter.links && (
          <div className="mt-5 flex flex-wrap gap-4">
            {chapter.links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-emerald-300 underline underline-offset-4 hover:text-emerald-200"
              >
                {link.label}
              </a>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default function CareerWorld() {
  const progressRef = useRef(0);

  useEffect(() => {
    function onScroll() {
      const doc = document.documentElement;
      const max = doc.scrollHeight - window.innerHeight;
      progressRef.current = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="relative">
      <div className="fixed inset-0 -z-10 bg-sky-200">
        <Canvas camera={{ position: [-24, 11, 19], fov: 45 }} shadows>
          <color attach="background" args={["#bfe3f5"]} />
          <fog attach="fog" args={["#bfe3f5", 40, 100]} />
          <Suspense fallback={null}>
            <Street />
            <Environment preset="park" />
          </Suspense>
          <ambientLight intensity={0.75} />
          <directionalLight position={[20, 25, 15]} intensity={1.3} />
          <CameraRig progressRef={progressRef} />
        </Canvas>
      </div>
      {CHAPTERS.map((chapter) => (
        <ChapterCard key={chapter.id} chapter={chapter} />
      ))}
    </div>
  );
}
