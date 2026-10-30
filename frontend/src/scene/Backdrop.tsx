import { useEffect, useRef } from 'react'
import { SurfaceBackdrop } from './SurfaceBackdrop'

export default function Backdrop({ energy, theme }: { energy: number; theme: 'light' | 'dark' }) {
  const host = useRef<HTMLDivElement>(null)
  const eng = useRef<SurfaceBackdrop | null>(null)
  useEffect(() => {
    const e = new SurfaceBackdrop(host.current!)
    eng.current = e
    return () => { e.dispose(); eng.current = null }
  }, [])
  useEffect(() => { eng.current?.setEnergy(energy) }, [energy])
  useEffect(() => { eng.current?.setInk(theme === 'dark' ? '#8A909A' : '#1A1C21') }, [theme])
  return <div ref={host} className="backdrop-host" />
}
