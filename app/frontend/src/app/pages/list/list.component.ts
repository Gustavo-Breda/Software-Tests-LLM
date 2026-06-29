import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { RequestsService } from '../../core/requests.service';
import {
  ServiceRequest, RequestPriority, RequestStatus,
  STATUS_LABELS, PRIORITY_LABELS,
} from '../../models';

@Component({
  selector: 'app-list',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  template: `
    <header class="app-header">
      <h1>Solicitações</h1>
      <div>
        <span class="user">{{ auth.user()?.name }}</span>
        <button
          class="secondary"
          (click)="logout()"
          data-testid="requests-logout"
        >Sair</button>
      </div>
    </header>

    <main class="container">
      <div class="toolbar">
        <div class="field">
          <label for="status">Status</label>
          <select
            id="status"
            [(ngModel)]="statusFilter"
            (ngModelChange)="reload()"
            data-testid="filter-status"
          >
            <option value="">Todos</option>
            <option value="aberta">aberta</option>
            <option value="em_analise">em análise</option>
            <option value="cancelada">cancelada</option>
            <option value="finalizada">finalizada</option>
          </select>
        </div>

        <div class="field">
          <label for="priority">Prioridade</label>
          <select
            id="priority"
            [(ngModel)]="priorityFilter"
            (ngModelChange)="reload()"
            data-testid="filter-priority"
          >
            <option value="">Todas</option>
            <option value="baixa">baixa</option>
            <option value="media">média</option>
            <option value="alta">alta</option>
          </select>
        </div>

        <div class="spacer"></div>

        <button (click)="goNew()" data-testid="requests-new">+ Nova solicitação</button>
      </div>

      @if (loading()) {
        <div class="empty">Carregando…</div>
      } @else if (items().length === 0) {
        <div class="empty" data-testid="requests-empty">
          Nenhuma solicitação encontrada.
        </div>
      } @else {
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
            @for (r of items(); track r.id) {
              <tr data-testid="request-row" [attr.data-request-id]="r.id">
                <td data-testid="request-row-title">{{ r.title }}</td>
                <td data-testid="request-row-status">
                  <span class="status-badge" [class]="'status-' + r.status">
                    {{ statusLabel(r.status) }}
                  </span>
                </td>
                <td data-testid="request-row-priority">{{ priorityLabel(r.priority) }}</td>
                <td>{{ r.created_at | date:'short' }}</td>
                <td>
                  @if (isCancellable(r)) {
                    <button
                      class="danger"
                      (click)="askCancel(r)"
                      data-testid="request-row-cancel"
                    >Cancelar</button>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      }
    </main>

    @if (pendingCancel(); as p) {
      <div class="modal-backdrop" data-testid="cancel-dialog">
        <div class="modal">
          <h2 data-testid="cancel-dialog-title">Cancelar "{{ p.title }}"?</h2>
          <p class="muted">Esta ação não pode ser desfeita.</p>
          @if (cancelError()) {
            <div class="error">{{ cancelError() }}</div>
          }
          <div class="actions">
            <button
              class="secondary"
              (click)="dismissCancel()"
              data-testid="cancel-back"
            >Voltar</button>
            <button
              class="danger"
              [disabled]="cancelling()"
              (click)="confirmCancel()"
              data-testid="cancel-confirm"
            >{{ cancelling() ? 'Cancelando…' : 'Confirmar' }}</button>
          </div>
        </div>
      </div>
    }
  `,
})
export class ListComponent implements OnInit {
  auth = inject(AuthService);
  private svc = inject(RequestsService);
  private router = inject(Router);

  items = signal<ServiceRequest[]>([]);
  loading = signal(true);

  statusFilter: RequestStatus | '' = '';
  priorityFilter: RequestPriority | '' = '';

  pendingCancel = signal<ServiceRequest | null>(null);
  cancelling = signal(false);
  cancelError = signal<string | null>(null);

  ngOnInit(): void { this.reload(); }

  reload(): void {
    this.loading.set(true);
    this.svc
      .list({ status: this.statusFilter, priority: this.priorityFilter })
      .subscribe({
        next: (res) => {
          this.items.set(res.items);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  goNew(): void { this.router.navigate(['/requests/new']); }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }

  statusLabel(s: RequestStatus): string { return STATUS_LABELS[s]; }
  priorityLabel(p: RequestPriority): string { return PRIORITY_LABELS[p]; }

  isCancellable(r: ServiceRequest): boolean {
    return r.status === 'aberta' || r.status === 'em_analise';
  }

  askCancel(r: ServiceRequest): void {
    this.cancelError.set(null);
    this.pendingCancel.set(r);
  }
  dismissCancel(): void {
    this.pendingCancel.set(null);
    this.cancelError.set(null);
  }
  confirmCancel(): void {
    const r = this.pendingCancel();
    if (!r) return;
    this.cancelling.set(true);
    this.svc.cancel(r.id).subscribe({
      next: () => {
        this.cancelling.set(false);
        this.pendingCancel.set(null);
        this.reload();
      },
      error: (err) => {
        this.cancelling.set(false);
        this.cancelError.set(
          err?.error?.detail ?? 'Não foi possível cancelar a solicitação.',
        );
      },
    });
  }
}
