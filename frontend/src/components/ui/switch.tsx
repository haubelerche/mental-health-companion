import * as SwitchPrimitives from '@radix-ui/react-switch'
import { type ComponentPropsWithoutRef, type ElementRef, forwardRef } from 'react'

type SwitchProps = ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>

const Switch = forwardRef<ElementRef<typeof SwitchPrimitives.Root>, SwitchProps>(
    function Switch({ className = '', ...props }, ref) {
        return (
            <SwitchPrimitives.Root
                ref={ref}
                className={[
                    'peer inline-flex h-7 w-14 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-serene-primary focus-visible:ring-offset-2 focus-visible:ring-offset-transparent',
                    'disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-serene-primary data-[state=unchecked]:bg-serene-outline/30',
                    className,
                ].join(' ')}
                {...props}
            >
                <SwitchPrimitives.Thumb
                    className={[
                        'pointer-events-none block h-6 w-6 rounded-full bg-white shadow-sm ring-0 transition-transform data-[state=checked]:translate-x-7 data-[state=unchecked]:translate-x-1',
                    ].join(' ')}
                />
            </SwitchPrimitives.Root>
        )
    },
)

Switch.displayName = SwitchPrimitives.Root.displayName

export { Switch }
