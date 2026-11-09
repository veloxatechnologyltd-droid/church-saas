import { QueryClient } from '@tanstack/react-query';
import { useAuthStore } from './store/authStore';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
});

// A new token means a different church, role or user: never show (or refetch)
// data cached for the previous session.
useAuthStore.subscribe((state, previous) => {
  if (state.token !== previous.token) queryClient.clear();
});
