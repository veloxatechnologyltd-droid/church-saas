import { useAuthStore } from '../store/authStore';
import { applyBrandTheme } from './theme';

// Where a freshly signed-in user should land, given the login-shaped payload.
export function landingPath(data) {
  if (data.active_church) return '/dashboard';
  if ((data.churches ?? []).length > 1) return '/select-church';
  if (data.user?.is_platform_admin) return '/platform';
  return '/login';
}

export function startSession(data) {
  useAuthStore.getState().setSession(data);
  applyBrandTheme(data.active_church);
  return landingPath(data);
}
