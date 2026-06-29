import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'
import { STATUS_LABELS, PRIORITY_LABELS } from '../types'
import type { ServiceRequest, RequestStatus, RequestPriority } from '../types'

import * as api from '../api'

export default function RequestsList() {
    const navigate = useNavigate()

    const { user, token, logout } = useAuth()

    const [items, setItems] = useState<ServiceRequest[]>([])
    const [loading, setLoading] = useState(true)
    const [statusFilter, setStatusFilter] = useState<RequestStatus | ''>('')
    const [priorityFilter, setPriorityFilter] = useState<RequestPriority | ''>('')

    const [pendingCancel, setPendingCancel] = useState<ServiceRequest | null>(null)
    const [cancelling, setCancelling] = useState(false)
    const [cancelError, setCancelError] = useState<string | null>(null)

    const reload = useCallback(() => {
        if (!token) return
        setLoading(true)
        api.listRequests(token, statusFilter || undefined, priorityFilter || undefined)
            .then(res => setItems(res.items))
            .catch(() => {})
            .finally(() => setLoading(false))
    }, [token, statusFilter, priorityFilter])

  useEffect(() => { reload() }, [reload])

    function handleLogout() {
        logout()
        navigate('/login')
    }

    function isCancellable(r: ServiceRequest) {
        return r.status === 'aberta' || r.status === 'em_analise'
    }

    function askCancel(r: ServiceRequest) {
        setCancelError(null)
        setPendingCancel(r)
    }

    function dismissCancel() {
        setPendingCancel(null)
        setCancelError(null)
    }

  function confirmCancel() {
        if (!pendingCancel || !token) return
        setCancelling(true)
        api.cancelRequest(token, pendingCancel.id)
            .then(() => {
                setCancelling(false)
                setPendingCancel(null)
                reload()
            })
            .catch((err: unknown) => {
                setCancelling(false)
                setCancelError(err instanceof api.ApiError ? err.message : 'Não foi possível cancelar a solicitação.')
            })
    }

  return (
    <>
      <header className="app-header">
        <h1>Solicitações</h1>
        <div>
          <span className="user">{user?.name}</span>
          <button className="secondary" onClick={handleLogout} data-testid="requests-logout">
            Sair
          </button>
        </div>
      </header>

      <main className="container">
        <div className="toolbar">
          <div className="field">
            <label htmlFor="status">Status</label>
            <select
              id="status"
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value as RequestStatus | '')}
              data-testid="filter-status"
            >
              <option value="">Todos</option>
              <option value="aberta">aberta</option>
              <option value="em_analise">em análise</option>
              <option value="cancelada">cancelada</option>
              <option value="finalizada">finalizada</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="priority">Prioridade</label>
            <select
              id="priority"
              value={priorityFilter}
              onChange={e => setPriorityFilter(e.target.value as RequestPriority | '')}
              data-testid="filter-priority"
            >
              <option value="">Todas</option>
              <option value="baixa">baixa</option>
              <option value="media">média</option>
              <option value="alta">alta</option>
            </select>
          </div>

          <div className="spacer" />

          <button onClick={() => navigate('/requests/new')} data-testid="requests-new">
            + Nova solicitação
          </button>
        </div>

        {loading ? (
          <div className="empty">Carregando…</div>
        ) : items.length === 0 ? (
          <div className="empty" data-testid="requests-empty">
            Nenhuma solicitação encontrada.
          </div>
        ) : (
          <table data-testid="requests-table">
            <thead>
              <tr>
                <th>Título</th>
                <th>Status</th>
                <th>Prioridade</th>
                <th>Criada em</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map(r => (
                <tr key={r.id} data-testid="request-row" data-request-id={r.id}>
                  <td data-testid="request-row-title">{r.title}</td>
                  <td data-testid="request-row-status">
                    <span className={`status-badge status-${r.status}`}>
                      {STATUS_LABELS[r.status]}
                    </span>
                  </td>
                  <td data-testid="request-row-priority">{PRIORITY_LABELS[r.priority]}</td>
                  <td>{new Date(r.created_at).toLocaleString('pt-BR')}</td>
                  <td>
                    {isCancellable(r) && (
                      <button className="danger" onClick={() => askCancel(r)} data-testid="request-row-cancel">
                        Cancelar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>

      {pendingCancel && (
        <div className="modal-backdrop" data-testid="cancel-dialog">
          <div className="modal">
            <h2 data-testid="cancel-dialog-title">Cancelar "{pendingCancel.title}"?</h2>
            <p className="muted">Esta ação não pode ser desfeita.</p>
            {cancelError && <div className="error">{cancelError}</div>}
            <div className="actions">
              <button className="secondary" onClick={dismissCancel} data-testid="cancel-back">
                Voltar
              </button>
              <button className="danger" disabled={cancelling} onClick={confirmCancel} data-testid="cancel-confirm">
                {cancelling ? 'Cancelando…' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
