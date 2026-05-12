"use client"

import dynamic from "next/dynamic"

const GalaxyGlobeCanvas = dynamic(() => import("./stars-canvas"), { ssr: false })

type RotatingGlobeBackgroundProps = {
  className?: string
}

export function RotatingGlobeBackground({ className }: RotatingGlobeBackgroundProps) {
  return (
    <div className={`absolute inset-0 ${className ?? ""}`} style={{ width: "100%", height: "100%" }}>
      <GalaxyGlobeCanvas />
    </div>
  )
}
