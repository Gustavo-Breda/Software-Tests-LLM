import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  RequestListResponse, ServiceRequest, RequestPriority, RequestStatus,
} from '../models';

const BASE = `${environment.apiBaseUrl}/api/requests`;

export interface ListFilters {
  status?: RequestStatus | '';
  priority?: RequestPriority | '';
}

@Injectable({ providedIn: 'root' })
export class RequestsService {
  private http = inject(HttpClient);

  list(filters: ListFilters = {}): Observable<RequestListResponse> {
    let params = new HttpParams();
    if (filters.status)   params = params.set('status', filters.status);
    if (filters.priority) params = params.set('priority', filters.priority);
    return this.http.get<RequestListResponse>(BASE, { params });
  }

  get(id: number): Observable<ServiceRequest> {
    return this.http.get<ServiceRequest>(`${BASE}/${id}`);
  }

  create(payload: {
    title: string;
    description: string;
    priority: RequestPriority;
  }): Observable<ServiceRequest> {
    return this.http.post<ServiceRequest>(BASE, payload);
  }

  cancel(id: number): Observable<ServiceRequest> {
    return this.http.post<ServiceRequest>(`${BASE}/${id}/cancel`, {});
  }
}
