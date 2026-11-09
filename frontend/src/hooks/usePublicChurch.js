import { useQuery } from '@tanstack/react-query';
import { publicService } from '../services/churchService';

export function usePublicChurch(slug) {
  return useQuery({
    queryKey: ['public-church', slug],
    queryFn: () => publicService.church(slug).then((r) => r.data.data),
    enabled: Boolean(slug),
    retry: false,
  });
}
