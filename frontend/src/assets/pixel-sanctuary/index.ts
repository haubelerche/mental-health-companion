import mascotMain from './mascot-main.gif'
import mascotIdle from './mascot.gif'
import mascotQuiet from './mascot2.gif'
import mascotEat from './mascot-eat.png'
import mascotSunflower from './reflect-mascot-sunflower.png'

export const pixelAssets = {
    mascotMain,
    mascotIdle,
    mascotQuiet,
    mascotEat,
    mascotSunflower,
    mascotRock: mascotQuiet,
    mascotBucket: mascotIdle,
} as const

export type PixelAssetKey = keyof typeof pixelAssets
