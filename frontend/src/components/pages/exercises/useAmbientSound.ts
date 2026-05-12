import { useEffect, useRef, useState } from 'react'

export function useAmbientSound(src: string) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [hasLoaded, setHasLoaded] = useState(false)
  const [autoplayBlocked, setAutoplayBlocked] = useState(false)

  useEffect(() => {
    const audio = new Audio(src)
    audio.loop = true
    audio.preload = 'auto'
    audio.volume = 0.35

    audio.addEventListener('canplaythrough', () => setHasLoaded(true), { once: true })
    audio.addEventListener('play', () => setIsPlaying(true))
    audio.addEventListener('pause', () => setIsPlaying(false))
    audio.addEventListener('error', () => setAutoplayBlocked(true))

    audioRef.current = audio

    const startAmbient = async () => {
      try {
        await audio.play()
        setAutoplayBlocked(false)
      } catch {
        setAutoplayBlocked(true)
      }
    }

    void startAmbient()

    return () => {
      audio.pause()
      audioRef.current = null
    }
  }, [src])

  const toggle = async () => {
    const audio = audioRef.current
    if (!audio) return

    if (audio.paused) {
      try {
        await audio.play()
        setAutoplayBlocked(false)
      } catch {
        setAutoplayBlocked(true)
      }
      return
    }

    audio.pause()
  }

  const setMuted = (nextMuted: boolean) => {
    const audio = audioRef.current
    if (audio) audio.muted = nextMuted
    setIsMuted(nextMuted)
  }

  return { isPlaying, isMuted, hasLoaded, autoplayBlocked, toggle, setMuted }
}
