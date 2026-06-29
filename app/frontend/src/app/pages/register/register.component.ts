import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';

// Password must contain at least one letter AND one digit (matches backend).
const passwordComplexity = Validators.pattern(/^(?=.*[A-Za-z])(?=.*\d).+$/);

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="auth-shell">
      <div class="card">
        <h1>Criar conta</h1>

        @if (error()) {
          <div class="error" data-testid="register-error">{{ error() }}</div>
        }
        @if (success()) {
          <div class="success" data-testid="register-success">
            Conta criada com sucesso. Redirecionando para o login…
          </div>
        }

        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <div class="field">
            <label for="name">Nome</label>
            <input
              id="name"
              type="text"
              formControlName="name"
              autocomplete="name"
              data-testid="register-name"
            />
            @if (showError('name', 'minlength') || showError('name', 'maxlength')) {
              <small class="muted">Nome deve ter entre 3 e 80 caracteres.</small>
            }
          </div>

          <div class="field">
            <label for="email">E-mail</label>
            <input
              id="email"
              type="email"
              formControlName="email"
              autocomplete="email"
              data-testid="register-email"
            />
            @if (showError('email', 'email')) {
              <small class="muted">Informe um e-mail válido.</small>
            }
          </div>

          <div class="field">
            <label for="password">Senha</label>
            <input
              id="password"
              type="password"
              formControlName="password"
              autocomplete="new-password"
              data-testid="register-password"
            />
            @if (showError('password', 'minlength') || showError('password', 'pattern')) {
              <small class="muted">
                Mínimo 8 caracteres, com ao menos uma letra e um número.
              </small>
            }
          </div>

          <button
            type="submit"
            [disabled]="form.invalid || submitting()"
            data-testid="register-submit"
          >
            {{ submitting() ? 'Cadastrando…' : 'Cadastrar' }}
          </button>
        </form>

        <p class="muted" style="margin-top: 1rem;">
          Já tem conta?
          <a routerLink="/login" data-testid="register-go-login">Entrar</a>
        </p>
      </div>
    </div>
  `,
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(80)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8), passwordComplexity]],
  });

  error = signal<string | null>(null);
  success = signal(false);
  submitting = signal(false);

  showError(field: string, kind: string): boolean {
    const c = this.form.get(field);
    return !!c && c.touched && c.hasError(kind);
  }

  submit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    this.error.set(null);
    this.success.set(false);
    this.submitting.set(true);

    const { name, email, password } = this.form.getRawValue();
    this.auth.register(name, email, password).subscribe({
      next: () => {
        this.submitting.set(false);
        this.success.set(true);
        setTimeout(() => this.router.navigate(['/login']), 1200);
      },
      error: (err: HttpErrorResponse) => {
        this.submitting.set(false);
        if (err.status === 409) {
          this.error.set('E-mail já cadastrado.');
        } else if (err.status === 422) {
          this.error.set('Dados inválidos. Verifique os campos.');
        } else {
          this.error.set('Não foi possível cadastrar. Tente novamente.');
        }
      },
    });
  }
}
