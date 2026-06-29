import type { AuthResponse, User, ServiceRequest, RequestListResponse, RequestPriority } from './types'

const BASE: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

export class ApiError extends Error {
    constructor(
        message: string,
        public readonly status: number,
        public readonly headers: Headers,
    ) {
        super(message)
        this.name = 'ApiError'
    }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string | null): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${BASE}${path}`, { ...init, headers })

    if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new ApiError(body.detail ?? `HTTP ${res.status}`, res.status, res.headers)
    }
    return res.json() as Promise<T>
}

export function login(email: string, password: string) {
    return request<AuthResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
    })
}

export function register(name: string, email: string, password: string) {
    return request<User>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, email, password }),
    })
}

export function listRequests(token: string, status?: string, priority?: string) {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (priority) params.set('priority', priority)
    const qs = params.toString()
    return request<RequestListResponse>(`/api/requests${qs ? '?' + qs : ''}`, {}, token)
}

export function createRequest(
    token: string,
    payload: { title: string; description: string; priority: RequestPriority },
) {
    return request<ServiceRequest>('/api/requests', {
        method: 'POST',
        body: JSON.stringify(payload),
    }, token)
}

export function cancelRequest(token: string, id: number) {
    return request<ServiceRequest>(`/api/requests/${id}/cancel`, { method: 'POST' }, token)
}
