import { useQuery } from '@tanstack/react-query';
import { reportsService } from '../services/reportsService';

export function useDashboardReport(enabled = true) {
  return useQuery({
    enabled,
    queryKey: ['reports-dashboard'],
    queryFn: () => reportsService.getDashboard().then((r) => r.data),
  });
}

export function useAttendanceMonthlyReport(enabled = true) {
  return useQuery({
    enabled,
    queryKey: ['reports-attendance-monthly'],
    queryFn: () => reportsService.getAttendanceMonthly().then((r) => r.data),
  });
}


export function useDonationsMonthlyReport(enabled = true) {
  return useQuery({
    enabled,
    queryKey: ['reports-donations-monthly'],
    queryFn: () => reportsService.getDonationsMonthly().then((r) => r.data),
  });
}

export function useExpensesMonthlyReport(enabled = true) {
  return useQuery({
    enabled,
    queryKey: ['reports-expenses-monthly'],
    queryFn: () => reportsService.getExpensesMonthly().then((r) => r.data),
  });
}


export function useMembersGrowthReport(enabled = true) {
  return useQuery({
    enabled,
    queryKey: ['reports-members-growth'],
    queryFn: () => reportsService.getMembersGrowth().then((r) => r.data),
  });
}
