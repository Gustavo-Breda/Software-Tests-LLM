import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import * as api from '../api'

const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).+$/

export default function Register() {
    const navigate = useNavigate()

    const [name, setName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)
    const [submitting, setSubmitting] = useState(false)

    function validate(): string | null {
        if (name.trim().length < 3 || name.trim().length > 80)
            return 'Nome deve ter entre 3 e 80 caracteres.'
        if (password.length < 8 || !PASSWORD_RE.test(password))
            return 'Mínimo 8 caracteres, com ao menos uma letra e um número.'
        return null
    }

    async function handleSubmit(e: FormEvent) {
        e.preventDefault()
        const msg = validate()
        if (msg) { 
            setError(msg)
            return 
        }
        setError(null)
        setSubmitting(true)
        try {
            await api.register(name.trim(), email, password)
            setSuccess(true)
            setTimeout(() => navigate('/login'), 1200)
        } catch (err) {
            if (err instanceof api.ApiError && err.status === 409) setError('E-mail já cadastrado.')
            else if (err instanceof api.ApiError && err.status === 422) setError('Dados inválidos. Verifique os campos.')
            else setError('Não foi possível cadastrar. Tente novamente.')
        } finally {
            setSubmitting(false)
        }
    }

  return (
    <div className="auth-shell">
      <div className="card">
        <h1>Criar conta</h1>

        {error && <div className="error" data-testid="register-error">{error}</div>}
        {success && (
          <div className="success" data-testid="register-success">
            Conta criada com sucesso. Redirecionando para o login…
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="name">Nome</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              autoComplete="name"
              data-testid="register-name"
              required
            />
            <small className="muted">Nome deve ter entre 3 e 80 caracteres.</small>
          </div>

          <div className="field">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              data-testid="register-email"
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
              autoComplete="new-password"
              data-testid="register-password"
              required
            />
            <small className="muted">Mínimo 8 caracteres, com ao menos uma letra e um número.</small>
          </div>

          <button type="submit" disabled={submitting || success} data-testid="register-submit">
            {submitting ? 'Cadastrando…' : 'Cadastrar'}
          </button>
        </form>

        <p className="muted" style={{ marginTop: '1rem' }}>
          Já tem conta?{' '}
          <Link to="/login" data-testid="register-go-login">Entrar</Link>
        </p>
      </div>
    </div>
  )
}
