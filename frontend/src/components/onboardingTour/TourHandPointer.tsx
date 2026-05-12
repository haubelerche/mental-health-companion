import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import handGesture from '../../assets/assistants/hand-gesture.gif'
import { queryTourAnchor } from './tourAnchors'

type Placement = 'left' | 'right' | 'top' | 'bottom' | 'auto'

type TourHandPointerProps = {
    targetAnchorId: string | null
    placement?: Placement
    visible: boolean
}

function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value))
}

function resolvePlacement(rect: DOMRect, placement: Placement): Placement {
    if (placement !== 'auto') return placement
    const spaces = {
        right: window.innerWidth - rect.right,
        left: rect.left,
        bottom: window.innerHeight - rect.bottom,
        top: rect.top,
    }
    return Object.entries(spaces).sort((a, b) => b[1] - a[1])[0][0] as Placement
}

export default function TourHandPointer({
    targetAnchorId,
    placement = 'auto',
    visible,
}: TourHandPointerProps) {
    const [style, setStyle] = useState<CSSProperties | null>(null)

    useEffect(() => {
        if (!visible || !targetAnchorId) {
            return
        }

        const update = () => {
            const target = queryTourAnchor(targetAnchorId)
            if (!target) {
                setStyle(null)
                return
            }
            const rect = target.getBoundingClientRect()
            const size = window.innerWidth < 768 ? 42 : 56
            const gap = 8
            const side = resolvePlacement(rect, placement)
            let top = rect.top + rect.height / 2 - size / 2
            let left = rect.left + rect.width / 2 - size / 2
            let rotate = 0

            if (side === 'left') {
                left = rect.left - size - gap
                rotate = 0
            } else if (side === 'right') {
                left = rect.right + gap
                rotate = 180
            } else if (side === 'top') {
                top = rect.top - size - gap
                rotate = 90
            } else {
                top = rect.bottom + gap
                rotate = -90
            }

            setStyle({
                top: clamp(top, 8, window.innerHeight - size - 8),
                left: clamp(left, 8, window.innerWidth - size - 8),
                width: size,
                height: size,
                transform: `rotate(${rotate}deg)`,
            })
        }

        update()
        const id = window.setTimeout(update, 120)
        window.addEventListener('resize', update)
        window.addEventListener('scroll', update, true)
        return () => {
            window.clearTimeout(id)
            window.removeEventListener('resize', update)
            window.removeEventListener('scroll', update, true)
        }
    }, [placement, targetAnchorId, visible])

    if (!visible || !targetAnchorId || !style) return null

    return (
        <img
            src={handGesture}
            alt=""
            aria-hidden="true"
            className="tour-hand-pointer pointer-events-none fixed z-[10000] object-contain"
            style={{ ...style, imageRendering: 'pixelated' }}
        />
    )
}
