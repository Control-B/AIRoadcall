"use client"

import { Canvas, useFrame } from "@react-three/fiber"
import { useMemo, useRef, useState, useEffect } from "react"
import { ShaderMaterial, AdditiveBlending, BackSide, NormalBlending } from "three"

/* ─────────────────────────────────────────────
   Load the land-mask texture and sample it to
   build an ImageData lookup for land vs ocean
   ───────────────────────────────────────────── */
function useLandMask() {
  const [imageData, setImageData] = useState<ImageData | null>(null)

  useEffect(() => {
    const img = new Image()
    img.crossOrigin = "anonymous"
    img.onload = () => {
      const canvas = document.createElement("canvas")
      canvas.width = img.width
      canvas.height = img.height
      const ctx = canvas.getContext("2d")!
      ctx.drawImage(img, 0, 0)
      setImageData(ctx.getImageData(0, 0, img.width, img.height))
    }
    img.src = "/earth-land.png"
  }, [])

  return imageData
}

/** Sample the land-mask: returns true if lat/lon is on land */
function isLandFromTexture(
  lat: number,
  lon: number,
  data: ImageData
): boolean {
  const u = (lon + 180) / 360
  const v = (90 - lat) / 180

  const x = Math.floor(u * data.width) % data.width
  const y = Math.floor(v * data.height) % data.height

  const idx = (y * data.width + x) * 4
  return data.data[idx] > 128
}

/* ─────────────────────────────────────────────
   Grid-based dotted globe using lat/lon grid
   for even spacing (no spiral artifacts)
   ───────────────────────────────────────────── */
function DottedGlobe() {
  const groupRef = useRef<any>(null)
  const atmosphereRef = useRef<any>(null)
  const ringRef = useRef<any>(null)

  const RADIUS = 2.5
  const landMask = useLandMask()

  // Use a lat/lon grid instead of Fibonacci to avoid spiral artifacts
  const geometry = useMemo(() => {
    const pos: number[] = []
    const col: number[] = []
    const sz: number[] = []

    // ~200 latitude rows, longitude count adjusted by cos(lat) for even spacing
    const latSteps = 200
    for (let i = 0; i <= latSteps; i++) {
      const lat = -90 + (180 * i) / latSteps
      const latRad = (lat * Math.PI) / 180

      // More dots near equator, fewer near poles — keeps spacing uniform
      const lonSteps = Math.max(8, Math.round(latSteps * Math.cos(latRad)))

      for (let j = 0; j < lonSteps; j++) {
        const lon = -180 + (360 * j) / lonSteps
        const lonRad = (lon * Math.PI) / 180

        const y = Math.sin(latRad)
        const xz = Math.cos(latRad)
        const x = xz * Math.cos(lonRad)
        const z = xz * Math.sin(lonRad)

        const onLand = landMask ? isLandFromTexture(lat, lon, landMask) : false

        pos.push(x * RADIUS, y * RADIUS, z * RADIUS)

        if (onLand) {
          // Bright white-blue land dots
          col.push(0.92, 0.96, 1.0)
          sz.push(1.0)
        } else {
          // Dim ocean dots
          col.push(0.18, 0.22, 0.32)
          sz.push(0.7)
        }
      }
    }

    return {
      positions: new Float32Array(pos),
      colors: new Float32Array(col),
      sizes: new Float32Array(sz),
    }
  }, [landMask])

  // Shader with uniform dot size — depth-attenuated, circular, soft edge
  const shaderMaterial = useMemo(
    () =>
      new ShaderMaterial({
        transparent: true,
        depthWrite: false,
        depthTest: true,
        blending: NormalBlending,
        vertexShader: `
          attribute float size;
          varying vec3 vColor;
          varying float vAlpha;
          void main() {
            vColor = color;
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            // Small uniform dots — scale with distance
            gl_PointSize = size * (120.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
            // Fade dots near edges (normal facing away from camera)
            vec3 vNormal = normalize(normalMatrix * normalize(position));
            float facing = dot(vNormal, vec3(0.0, 0.0, 1.0));
            vAlpha = smoothstep(-0.05, 0.4, facing);
          }
        `,
        fragmentShader: `
          varying vec3 vColor;
          varying float vAlpha;
          void main() {
            float d = length(gl_PointCoord - vec2(0.5));
            if (d > 0.5) discard;
            float circle = 1.0 - smoothstep(0.25, 0.5, d);
            gl_FragColor = vec4(vColor, circle * vAlpha * 0.85);
          }
        `,
        vertexColors: true,
      }),
    []
  )

  useFrame((_state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.1
    }
    if (atmosphereRef.current) {
      atmosphereRef.current.rotation.y -= delta * 0.015
    }
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * 0.025
    }
  })

  return (
    <group ref={groupRef}>
      {/* Dark core sphere — hides back-face dots cleanly */}
      <mesh>
        <sphereGeometry args={[RADIUS * 0.97, 64, 64]} />
        <meshBasicMaterial color="#080c18" />
      </mesh>

      {/* All dots — grid-based, no spiral artifacts */}
      <points material={shaderMaterial}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[geometry.positions, 3]} />
          <bufferAttribute attach="attributes-color" args={[geometry.colors, 3]} />
          <bufferAttribute attach="attributes-size" args={[geometry.sizes, 1]} />
        </bufferGeometry>
      </points>

      {/* Atmospheric glow — inner edge */}
      <mesh ref={atmosphereRef} scale={1.02}>
        <sphereGeometry args={[RADIUS, 64, 64]} />
        <meshBasicMaterial
          color="#60a5fa"
          transparent
          opacity={0.12}
          side={BackSide}
          blending={AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Outer glow halo */}
      <mesh scale={1.1}>
        <sphereGeometry args={[RADIUS, 48, 48]} />
        <meshBasicMaterial
          color="#93c5fd"
          transparent
          opacity={0.08}
          side={BackSide}
          blending={AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Subtle bloom ring */}
      <mesh scale={1.2}>
        <sphereGeometry args={[RADIUS, 32, 32]} />
        <meshBasicMaterial
          color="#bfdbfe"
          transparent
          opacity={0.04}
          side={BackSide}
          blending={AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Orbital ring — solid thin line */}
      <mesh ref={ringRef} rotation={[1.35, 0.12, 0.2]}>
        <torusGeometry args={[RADIUS * 1.3, 0.007, 16, 256]} />
        <meshBasicMaterial color="#dbeafe" transparent opacity={0.4} depthWrite={false} />
      </mesh>
      {/* Orbital ring glow */}
      <mesh rotation={[1.35, 0.12, 0.2]}>
        <torusGeometry args={[RADIUS * 1.3, 0.06, 16, 256]} />
        <meshBasicMaterial
          color="#3b82f6"
          transparent
          opacity={0.08}
          blending={AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  )
}

/* ─────────────────────────────────────────────
   Custom starfield — replaces @react-three/drei Stars
   to avoid module factory errors
   ───────────────────────────────────────────── */
function RotatingStars() {
  const ref = useRef<any>(null)

  const starPositions = useMemo(() => {
    const positions = new Float32Array(10000 * 3)
    for (let i = 0; i < 10000; i++) {
      const r = 50 + Math.random() * 100
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = r * Math.cos(phi)
    }
    return positions
  }, [])

  useFrame((_state, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.015
      ref.current.rotation.x += delta * 0.005
    }
  })

  return (
    <group ref={ref}>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[starPositions, 3]} />
        </bufferGeometry>
        <pointsMaterial color="#ffffff" size={0.4} transparent opacity={0.8} sizeAttenuation />
      </points>
    </group>
  )
}

/* ─────────────────────────────────────────────
   Full scene export — fills entire section,
   globe offset to the left half
   ───────────────────────────────────────────── */
export default function StarsCanvas() {
  return (
    <Canvas
      camera={{ position: [0, 0, 8], fov: 50 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
      style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}
    >
      {/* Dense starfield — slowly drifting */}
      <RotatingStars />

      {/* Ambient fill */}
      <ambientLight intensity={0.4} />

      {/* Key light — bright white for moon glow */}
      <directionalLight position={[-4, 3, 5]} intensity={2.5} color="#e0f0ff" />

      {/* Rim light for the atmosphere edge */}
      <directionalLight position={[5, -2, 3]} intensity={1.2} color="#93c5fd" />

      {/* Point light near globe for extra bloom */}
      <pointLight position={[0, 0, 4]} intensity={3} color="#bfdbfe" distance={12} decay={2} />

      {/* Globe centered in viewport */}
      <DottedGlobe />
    </Canvas>
  )
}
