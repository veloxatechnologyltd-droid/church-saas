import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Session shape follows the multi-church login API (docs/API_SAAS.md):
//   token, user, churches[], activeChurch (null until a church is chosen).
// `impersonation` keeps the platform admin's own session while they act as a church admin.
// `billingNotice` / `suspension` are set by the API client on 402 / 403-suspended responses.
const EMPTY = {
  token: null,
  user: null,
  churches: [],
  activeChurch: null,
  impersonation: null,
  billingNotice: null,
  suspension: null,
};

export const useAuthStore = create(
  persist(
    (set, get) => ({
      ...EMPTY,
      setSession: (data) =>
        set({
          token: data.access_token,
          user: data.user,
          churches: data.churches ?? [],
          activeChurch: 'active_church' in data ? data.active_church : get().activeChurch,
          billingNotice: null,
          suspension: null,
        }),
      setMe: (data) =>
        set({
          user: data.user ?? get().user,
          churches: data.churches ?? get().churches,
          activeChurch: 'active_church' in data ? data.active_church : get().activeChurch,
        }),
      updateActiveChurch: (partial) => {
        const active = get().activeChurch;
        if (!active) return;
        const next = { ...active, ...partial };
        set({
          activeChurch: next,
          churches: get().churches.map((church) => (church.id === next.id ? { ...church, ...partial } : church)),
        });
      },
      setBillingNotice: (notice) => set({ billingNotice: notice }),
      setSuspension: (suspension) => set({ suspension }),
      startImpersonation: (data) => {
        const { token, user, churches, activeChurch } = get();
        set({
          impersonation: { token, user, churches, activeChurch },
          token: data.access_token,
          user: data.user,
          churches: data.churches ?? [],
          activeChurch: 'active_church' in data ? data.active_church : get().activeChurch,
          billingNotice: null,
          suspension: null,
        });
      },
      stopImpersonation: () => {
        const saved = get().impersonation;
        if (!saved) return;
        set({ ...saved, impersonation: null, billingNotice: null, suspension: null });
      },
      logout: () => set({ ...EMPTY }),
    }),
    {
      name: 'asafo-auth',
      partialize: ({ token, user, churches, activeChurch, impersonation }) => ({ token, user, churches, activeChurch, impersonation }),
    }
  )
);

export const useRole = () => useAuthStore((state) => state.activeChurch?.role ?? state.user?.role ?? null);

export function hasRole(role, allowed) {
  return !allowed || allowed.includes(role);
}
