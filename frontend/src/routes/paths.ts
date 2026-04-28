export const ROUTE_PATHS = {
    root: '/',
    landing: '/landing',
    login: '/login',
    register: '/register',
    forget: '/forget-password',

    // serene
    home: '/serene',
    chat: '/serene/chat',
    reflect: '/serene/reflect',
    resources: '/serene/resources',
    nutrition: '/serene/nutrition',
    connect: '/serene/connect',
    setting: '/serene/setting',

    // onboarding & flows
    onboardingPolicy: '/onboarding/policy',
    onboarding: '/serene/onboarding',
    bamboo: '/serene/bamboo',
    safetyCheck: '/serene/safety-check',
    checkin: '/serene/checkin',
    screening: '/serene/screening',
    results: '/serene/results',
    exercises: '/serene/exercises',

    //admin
    admin: '/admin',
    adminLogin: '/admin/login',
    adminDashboard: '/admin/dashboard',
} as const
