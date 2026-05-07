// Simple singleton for admin data caching
const cache = {
    letters: {
        normal: [] as any[],
        reported: [] as any[],
        totalReported: 0,
        currentPage: 1
    },
    users: {
        users: [] as any[],
        total: 0,
        query: ''
    }
}

export const adminCache = {
    getLetters: () => cache.letters,
    setLetters: (data: Partial<typeof cache.letters>) => {
        cache.letters = { ...cache.letters, ...data }
    },
    getUsers: () => cache.users,
    setUsers: (data: Partial<typeof cache.users>) => {
        cache.users = { ...cache.users, ...data }
    },
    clear: () => {
        cache.letters.normal = []
        cache.letters.reported = []
        cache.users.users = []
    }
}
