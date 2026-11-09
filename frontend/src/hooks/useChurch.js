import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { churchService } from '../services/churchService';
import { useAuthStore } from '../store/authStore';
import { applyBrandTheme } from '../utils/theme';

// The active church's full profile (GET /church). Keeps the theme and the cached
// active church in the auth store in sync with what the server says.
export function useChurch() {
  const activeChurchId = useAuthStore((state) => state.activeChurch?.id);
  const updateActiveChurch = useAuthStore((state) => state.updateActiveChurch);
  const query = useQuery({
    queryKey: ['church', activeChurchId],
    queryFn: () => churchService.get().then((r) => r.data.data),
    enabled: Boolean(activeChurchId),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!query.data) return;
    applyBrandTheme(query.data);
    const { name, logo_url, primary_color, secondary_color, status, plan, currency } = query.data;
    updateActiveChurch({ name, logo_url, primary_color, secondary_color, status, plan, currency });
  }, [query.data, updateActiveChurch]);

  return query;
}

export function useCurrency() {
  return useAuthStore((state) => state.activeChurch?.currency) || 'GHS';
}
