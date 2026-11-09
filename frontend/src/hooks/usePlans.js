import { useQuery } from '@tanstack/react-query';
import { billingService } from '../services/churchService';

export function usePlans() {
  return useQuery({
    queryKey: ['plans'],
    queryFn: () => billingService.plans().then((r) => r.data.data),
    staleTime: 5 * 60_000,
  });
}
