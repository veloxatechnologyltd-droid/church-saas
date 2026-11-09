import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { donationsService } from '../services/donationsService';


export function useDonations(params) {
  return useQuery({
    queryKey: ['donations', params],
    queryFn: () => donationsService.getAll(params).then((r) => r.data),
  });
}


export function useDonationFunds() {
  return useQuery({
    queryKey: ['donation-funds'],
    queryFn: () => donationsService.getFunds().then((r) => r.data),
  });
}


export function useFinanceBatches(params = { include_closed: true }) {
  return useQuery({
    queryKey: ['finance-batches', params],
    queryFn: () => donationsService.getBatches(params).then((r) => r.data),
  });
}

export function useExpenses(params) {
  return useQuery({
    queryKey: ['expenses', params],
    queryFn: () => donationsService.getExpenses(params).then((r) => r.data),
  });
}


export function useExpenseCategories() {
  return useQuery({
    queryKey: ['expense-categories'],
    queryFn: () => donationsService.getExpenseCategories().then((r) => r.data),
  });
}


export function useFinanceSummary(params) {
  return useQuery({
    queryKey: ['finance-summary', params],
    queryFn: () => donationsService.getSummary(params).then((r) => r.data),
  });
}


export function useDonationMonthlyReport(params) {
  return useQuery({
    queryKey: ['donation-monthly-report', params],
    queryFn: () => donationsService.getMonthlyReport(params).then((r) => r.data),
  });
}


export function useExpenseMonthlyReport(params) {
  return useQuery({
    queryKey: ['expense-monthly-report', params],
    queryFn: () => donationsService.getMonthlyExpenseReport(params).then((r) => r.data),
  });
}


export function useDonationAnnualReport(year, filters = {}) {
  return useQuery({
    queryKey: ['donation-annual-report', year, filters],
    queryFn: () => donationsService.getAnnualReport({ year, ...filters }).then((r) => r.data),
  });
}


export function useCreateDonation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => donationsService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['donations'] });
      queryClient.invalidateQueries({ queryKey: ['donation-annual-report'] });
      queryClient.invalidateQueries({ queryKey: ['finance-batches'] });
      queryClient.invalidateQueries({ queryKey: ['finance-summary'] });
      queryClient.invalidateQueries({ queryKey: ['reports-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['reports-donations-monthly'] });
    },
  });
}


export function useCreateDonationFund() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => donationsService.createFund(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['donation-funds'] });
    },
  });
}


export function useBootstrapDonationFunds() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => donationsService.bootstrapFunds(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['donation-funds'] });
    },
  });
}

export function useBootstrapExpenseCategories() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => donationsService.bootstrapExpenseCategories(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expense-categories'] });
    },
  });
}


export function useCreateFinanceBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => donationsService.createBatch(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-batches'] });
    },
  });
}


export function useCloseFinanceBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (batchId) => donationsService.closeBatch(batchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-batches'] });
      queryClient.invalidateQueries({ queryKey: ['donations'] });
    },
  });
}


export function useCreateExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => donationsService.createExpense(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      queryClient.invalidateQueries({ queryKey: ['finance-summary'] });
      queryClient.invalidateQueries({ queryKey: ['reports-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['reports-expenses-monthly'] });
    },
  });
}


export function useCreateExpenseCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => donationsService.createExpenseCategory(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expense-categories'] });
    },
  });
}
