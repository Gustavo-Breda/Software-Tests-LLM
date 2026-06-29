import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';

import { RequestsService } from '../../core/requests.service';

@Component({
  selector: 'app-create',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <header class="app-header">
      <h1>Nova solicitação</h1>
    </header>

    <main class="container">
      <div class="card">
        @if (error()) {
          <div class="error" data-testid="request-error">{{ error() }}</div>
        }

        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <div class="field">
            <label for="title">Título</label>
            <input
              id="title"
              type="text"
              formControlName="title"
              maxlength="100"
              data-testid="request-title"
            />
            @if (showError('title', 'minlength') || showError('title', 'maxlength')) {
              <small class="muted">Título deve ter entre 5 e 100 caracteres.</small>
            }
          </div>

          <div class="field">
            <label for="description">Descrição</label>
            <textarea
              id="description"
              rows="5"
              formControlName="description"
              maxlength="500"
              data-testid="request-description"
            ></textarea>
            @if (showError('description', 'minlength') || showError('description', 'maxlength')) {
              <small class="muted">Descrição deve ter entre 10 e 500 caracteres.</small>
            }
          </div>

          <div class="field">
            <label for="priority">Prioridade</label>
            <select
              id="priority"
              formControlName="priority"
              data-testid="request-priority"
            >
              <option value="" disabled>Selecione…</option>
              <option value="baixa">baixa</option>
              <option value="media">média</option>
              <option value="alta">alta</option>
            </select>
          </div>

          <div style="display: flex; gap: 0.75rem; margin-top: 1rem;">
            <button
              type="submit"
              [disabled]="form.invalid || submitting()"
              data-testid="request-submit"
            >{{ submitting() ? 'Criando…' : 'Criar solicitação' }}</button>
            <button
              type="button"
              class="secondary"
              (click)="cancel()"
              data-testid="request-cancel"
            >Cancelar</button>
          </div>
        </form>
      </div>
    </main>
  `,
})
export class CreateComponent {
  private fb = inject(FormBuilder);
  private svc = inject(RequestsService);
  private router = inject(Router);

  form = this.fb.nonNullable.group({
    title: ['', [Validators.required, Validators.minLength(5), Validators.maxLength(100)]],
    description: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(500)]],
    priority: ['', [Validators.required]],
  });

  error = signal<string | null>(null);
  submitting = signal(false);

  showError(field: string, kind: string): boolean {
    const c = this.form.get(field);
    return !!c && c.touched && c.hasError(kind);
  }

  submit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    this.error.set(null);
    this.submitting.set(true);

    const { title, description, priority } = this.form.getRawValue();
    this.svc.create({
      title,
      description,
      priority: priority as 'baixa' | 'media' | 'alta',
    }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.router.navigate(['/requests']);
      },
      error: (err: HttpErrorResponse) => {
        this.submitting.set(false);
        if (err.status === 422) {
          this.error.set('Dados inválidos. Verifique os campos.');
        } else if (err.status === 401) {
          this.error.set('Sessão expirada. Faça login novamente.');
        } else {
          this.error.set('Não foi possível criar a solicitação.');
        }
      },
    });
  }

  cancel(): void { this.router.navigate(['/requests']); }
}
