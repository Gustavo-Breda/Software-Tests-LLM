export type RequestStatus = 'aberta' | 'em_analise' | 'cancelada' | 'finalizada'
export type RequestPriority = 'baixa' | 'media' | 'alta'

export interface User {
  id: number
  name: string
  email: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface ServiceRequest {
  id: number
  title: string
  description: string
  priority: RequestPriority
  status: RequestStatus
  created_at: string
  cancelled_at: string | null
  owner_id: number
}

export interface RequestListResponse {
  items: ServiceRequest[]
  total: number
}

export const STATUS_LABELS: Record<RequestStatus, string> = {
  aberta: 'aberta',
  em_analise: 'em análise',
  cancelada: 'cancelada',
  finalizada: 'finalizada',
}

export const PRIORITY_LABELS: Record<RequestPriority, string> = {
  baixa: 'baixa',
  media: 'média',
  alta: 'alta',
}
