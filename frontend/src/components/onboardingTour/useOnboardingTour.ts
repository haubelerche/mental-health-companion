import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'
import {
    onboardingTourService,
    type OnboardingTourState,
    type OnboardingTourStep,
} from '../../services/onboardingTourService'
import { queryTourAnchor } from './tourAnchors'

function normalizePath(path: string): string {
    return path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path
}

function nextStepId(steps: OnboardingTourStep[], current: OnboardingTourStep): string | null {
    const index = steps.findIndex((step) => step.step_id === current.step_id)
    if (index < 0 || index + 1 >= steps.length) return null
    return steps[index + 1].step_id
}

export function useOnboardingTour() {
    const navigate = useNavigate()
    const location = useLocation()
    const [searchParams] = useSearchParams()
    const [state, setState] = useState<OnboardingTourState | null>(null)
    const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null)
    const [dockOnly, setDockOnly] = useState(false)
    const [loading, setLoading] = useState(true)
    const [farewellVisible, setFarewellVisible] = useState(false)

    const currentStep = useMemo(() => {
        if (!state?.current_step_id) return null
        return state.steps.find((step) => step.step_id === state.current_step_id) ?? null
    }, [state])

    const activeIndex = useMemo(() => {
        if (!state || !currentStep) return 0
        return Math.max(0, state.steps.findIndex((step) => step.step_id === currentStep.step_id))
    }, [currentStep, state])

    const isSafetyRoute = normalizePath(location.pathname) === ROUTE_PATHS.safetyCheck

    const shouldRender = Boolean(
        state &&
        currentStep &&
        !isSafetyRoute &&
        state.status !== 'paused_for_safety' &&
        (state.status === 'in_progress' ||
            (state.status === 'available' && searchParams.get('tour') === 'first_run')),
    )

    const refresh = useCallback(async () => {
        setLoading(true)
        try {
            const data = await onboardingTourService.getState()
            setState(data)
        } catch {
            setState(null)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        void refresh()
    }, [refresh])

    useEffect(() => {
        if (searchParams.get('tour') !== 'replay') return
        let cancelled = false
        onboardingTourService.start('first_run')
            .then((data) => {
                if (!cancelled) setState(data)
            })
            .catch(() => undefined)
        return () => {
            cancelled = true
        }
    }, [searchParams])

    useEffect(() => {
        if (!shouldRender || !currentStep) {
            setAnchorRect(null)
            setDockOnly(false)
            return
        }

        if (currentStep.requires_navigation && normalizePath(location.pathname) !== normalizePath(currentStep.route)) {
            navigate(currentStep.route, { replace: false })
            setDockOnly(true)
            return
        }

        const updateRect = () => {
            if (!currentStep.target_anchor_id) {
                setAnchorRect(null)
                setDockOnly(true)
                return
            }
            const anchor = queryTourAnchor(currentStep.target_anchor_id)
            if (!anchor) {
                setAnchorRect(null)
                setDockOnly(true)
                return
            }
            setAnchorRect(anchor.getBoundingClientRect())
            setDockOnly(window.innerWidth < 768)
        }

        window.requestAnimationFrame(updateRect)
        const id = window.setTimeout(updateRect, 260)
        window.addEventListener('resize', updateRect)
        window.addEventListener('scroll', updateRect, true)
        return () => {
            window.clearTimeout(id)
            window.removeEventListener('resize', updateRect)
            window.removeEventListener('scroll', updateRect, true)
        }
    }, [currentStep, location.pathname, navigate, shouldRender])

    const dismiss = useCallback(() => {
        setState((prev) => prev ? { ...prev, status: 'dismissed' } : prev)
        void onboardingTourService.dismiss().catch(() => undefined)
    }, [])

    const skip = useCallback(() => {
        setFarewellVisible(true)
        void onboardingTourService.skip().catch(() => undefined)
    }, [])

    useEffect(() => {
        if (!farewellVisible) return
        const id = window.setTimeout(() => {
            setState((prev) => prev ? { ...prev, status: 'skipped' } : prev)
            setFarewellVisible(false)
        }, 1600)
        return () => window.clearTimeout(id)
    }, [farewellVisible])

    const complete = useCallback(() => {
        setState((prev) => prev ? { ...prev, status: 'completed', current_step_id: 'finish' } : prev)
        void onboardingTourService.complete().catch(() => undefined)
    }, [])

    const progress = useCallback((skipped = false) => {
        if (!state || !currentStep) return
        if (currentStep.step_id === 'finish') {
            complete()
            return
        }
        const next = nextStepId(state.steps, currentStep)
        setState((prev) => {
            if (!prev) return prev
            const completed = prev.completed_step_ids.includes(currentStep.step_id)
                ? prev.completed_step_ids
                : [...prev.completed_step_ids, currentStep.step_id]
            const skippedIds = skipped && !prev.skipped_step_ids.includes(currentStep.step_id)
                ? [...prev.skipped_step_ids, currentStep.step_id]
                : prev.skipped_step_ids
            return {
                ...prev,
                status: 'in_progress',
                current_step_id: next ?? 'finish',
                completed_step_ids: skipped ? prev.completed_step_ids : completed,
                skipped_step_ids: skippedIds,
            }
        })
        void onboardingTourService.progress({
            step_id: currentStep.step_id,
            skipped,
            next_step_id: next,
        }).catch(() => undefined)
    }, [complete, currentStep, state])

    const primary = useCallback(() => {
        if (!currentStep) return
        if (state?.status === 'available' && currentStep.step_id === 'welcome') {
            const next = state ? nextStepId(state.steps, currentStep) : null
            setState((prev) => prev ? { ...prev, status: 'in_progress', current_step_id: next ?? currentStep.step_id } : prev)
            void onboardingTourService.start('first_run')
                .then(() => onboardingTourService.progress({
                    step_id: currentStep.step_id,
                    next_step_id: next,
                }))
                .catch(() => undefined)
            return
        }
        if (currentStep.step_id === 'mood_checkin') {
            progress(false)
            navigate(ROUTE_PATHS.checkin)
            return
        }
        if (currentStep.step_id === 'finish') {
            complete()
            navigate(ROUTE_PATHS.checkin)
            return
        }
        progress(false)
    }, [complete, currentStep, navigate, progress, state])

    const secondary = useCallback(() => {
        if (!currentStep) return
        if (currentStep.step_id === 'welcome') {
            skip()
            return
        }
        if (currentStep.step_id === 'finish') {
            complete()
            navigate(ROUTE_PATHS.home)
            return
        }
        progress(true)
    }, [complete, currentStep, navigate, progress, skip])

    return {
        loading,
        state,
        currentStep,
        activeIndex,
        anchorRect,
        dockOnly,
        shouldRender,
        farewellVisible,
        primary,
        secondary,
        dismiss,
        skip,
    }
}
