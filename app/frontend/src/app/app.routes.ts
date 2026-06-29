import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'register',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./pages/register/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: 'requests',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/list/list.component').then((m) => m.ListComponent),
  },
  {
    path: 'requests/new',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/create/create.component').then((m) => m.CreateComponent),
  },
  { path: '', pathMatch: 'full', redirectTo: '/requests' },
  { path: '**', redirectTo: '/requests' },
];
