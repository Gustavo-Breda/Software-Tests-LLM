import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import * as api from '../api'
import type { RequestPriority } from '../types'

export default function CreateRequest() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<RequestPriority | ''>('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function validate(): string | null {
    if (title.trim().length < 5 || title.trim().length > 100)
      return 'Título deve ter entre 5 e 100 caracteres.'
    if (description.trim().length < 10 || description.trim().length > 500)
      return 'Descrição deve ter entre 10 e 500 caracteres.'
    if (!priority)
      return 'Selecione uma prioridade.'
    return null
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const msg = validate()
    if (msg) { setError(msg); return }
    if (!token || !priority) return
    setError(null)
    setSubmitting(true)
    try {
      await api.createRequest(token, { title: title.trim(), description: description.trim(), priority })
      navigate('/requests')
    } catch (err) {
      if (err instanceof api.ApiError && err.status === 422) setError('Dados inválidos. Verifique os campos.')
      else if (err instanceof api.ApiError && err.status === 401) setError('Sessão expirada. Faça login novamente.')
      else setError('Não foi possível criar a solicitação.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <header className="app-header">
        <h1>Nova solicitação</h1>
      </header>

      <main className="container">
        <div className="card">
          {error && <div className="error" data-testid="request-error">{error}</div>}

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor="title">Título</label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                maxLength={100}
                data-testid="request-title"
                required
              />
              <small className="muted">Título deve ter entre 5 e 100 caracteres.</small>
            </div>

            <div className="field">
              <label htmlFor="description">Descrição</label>
              <textarea
                id="description"
                rows={5}
                value={description}
                onChange={e => setDescription(e.target.value)}
                maxLength={500}
                data-testid="request-description"
                required
              />
              <small className="muted">Descrição deve ter entre 10 e 500 caracteres.</small>
            </div>

            <div className="field">
              <label htmlFor="priority">Prioridade</label>
              <select
                id="priority"
                value={priority}
                onChange={e => setPriority(e.target.value as RequestPriority | '')}
                data-testid="request-priority"
                required
              >
                <option value="" disabled>Selecione…</option>
                <option value="baixa">baixa</option>
                <option value="media">média</option>
                <option value="alta">alta</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
              <button type="submit" disabled={submitting} data-testid="request-submit">
                {submitting ? 'Criando…' : 'Criar solicitação'}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => navigate('/requests')}
                data-testid="request-cancel"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      </main>
    </>
  )
}
