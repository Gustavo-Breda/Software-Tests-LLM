import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'

import * as api from '../api'

export default function Login() {
    const navigate = useNavigate()
    
    const { persistAuth } = useAuth() 

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [lockoutSeconds, setLockoutSeconds] = useState<number | null>(null)
    const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
        e.preventDefault()
        setError(null)
        setLockoutSeconds(null)
        setSubmitting(true)
        try {
            const res = await api.login(email, password)
            persistAuth(res)
            navigate('/requests')
        } catch (err) {
            if (err instanceof api.ApiError && err.status === 423) {
                const retry = Number(err.headers.get('Retry-After'))
                setLockoutSeconds(Number.isFinite(retry) && retry > 0 ? retry : 60)
            } else {
                setError('E-mail ou senha inválidos.')
            }
        } finally {
            setSubmitting(false)
        }
    }

  return (
    <div className="auth-shell">
      <div className="card">
        <h1>Entrar</h1>

        {error && <div className="error" data-testid="login-error">{error}</div>}
        {lockoutSeconds !== null && (
          <div className="error" data-testid="login-lockout">
            Conta bloqueada. Tente novamente em {lockoutSeconds} segundos.
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              data-testid="login-email"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              data-testid="login-password"
              required
            />
          </div>

          <button type="submit" disabled={submitting} data-testid="login-submit">
            {submitting ? 'Entrando…' : 'Entrar'}
          </button>
        </form>

        <p className="muted" style={{ marginTop: '1rem' }}>
          Não tem conta?{' '}
          <Link to="/register" data-testid="login-go-register">Cadastre-se</Link>
        </p>
      </div>
    </div>
  )
}
