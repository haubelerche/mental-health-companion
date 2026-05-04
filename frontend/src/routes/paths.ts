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
    profile: '/serene/profile',
    setting: '/serene/setting',
    notifications: '/serene/notifications',

    // onboarding & flows
    onboardingPolicy: '/onboarding/policy',
    onboarding: '/serene/onboarding',
    bamboo: '/serene/bamboo',
    safetyCheck: '/serene/safety-check',
    checkin: '/serene/checkin',
    screening: '/serene/screening',
    results: '/serene/results',
    exercises: '/serene/exercises',
    rewards: '/serene/rewards',

    //admin
    admin: '/admin',
    adminLogin: '/admin/login',
    adminDashboard: '/admin/dashboard',
    adminCrisisLogs: '/admin/crisis-logs',
    adminResources: '/admin/resources',
} as const
