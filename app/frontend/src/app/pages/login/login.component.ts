import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="auth-shell">
      <div class="card">
        <h1>Entrar</h1>

        @if (error()) {
          <div class="error" data-testid="login-error">{{ error() }}</div>
        }
        @if (lockoutSeconds() !== null) {
          <div class="error" data-testid="login-lockout">
            Conta bloqueada. Tente novamente em {{ lockoutSeconds() }} segundos.
          </div>
        }

        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <div class="field">
            <label for="email">E-mail</label>
            <input
              id="email"
              type="email"
              formControlName="email"
              autocomplete="email"
              data-testid="login-email"
            />
          </div>

          <div class="field">
            <label for="password">Senha</label>
            <input
              id="password"
              type="password"
              formControlName="password"
              autocomplete="current-password"
              data-testid="login-password"
            />
          </div>

          <button
            type="submit"
            [disabled]="form.invalid || submitting()"
            data-testid="login-submit"
          >
            {{ submitting() ? 'Entrando…' : 'Entrar' }}
          </button>
        </form>

        <p class="muted" style="margin-top: 1rem;">
          Não tem conta?
          <a routerLink="/register" data-testid="login-go-register">Cadastre-se</a>
        </p>
      </div>
    </div>
  `,
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  error = signal<string | null>(null);
  lockoutSeconds = signal<number | null>(null);
  submitting = signal(false);

  submit(): void {
    if (this.form.invalid) return;
    this.error.set(null);
    this.lockoutSeconds.set(null);
    this.submitting.set(true);

    const { email, password } = this.form.getRawValue();
    this.auth.login(email, password).subscribe({
      next: () => {
        this.submitting.set(false);
        this.router.navigate(['/requests']);
      },
      error: (err: HttpErrorResponse) => {
        this.submitting.set(false);
        if (err.status === 423) {
          const retry = Number(err.headers.get('Retry-After'));
          this.lockoutSeconds.set(Number.isFinite(retry) ? retry : 60);
        } else {
          // Always show the generic message for credential failures (US-01)
          this.error.set('E-mail ou senha inválidos.');
        }
      },
    });
  }
}
