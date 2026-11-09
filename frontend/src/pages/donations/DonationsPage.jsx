import { Banknote, CheckCircle2, FolderOpen, Receipt, TrendingDown, TrendingUp } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import DataTable from '../../components/shared/DataTable';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import StatCard from '../../components/shared/StatCard';
import TrendBars from '../../components/shared/TrendBars';
import {
  useBootstrapDonationFunds,
  useBootstrapExpenseCategories,
  useCreateDonation,
  useCreateDonationFund,
  useCreateExpense,
  useCreateExpenseCategory,
  useCreateFinanceBatch,
  useCloseFinanceBatch,
  useDonationAnnualReport,
  useDonationMonthlyReport,
  useDonationFunds,
  useDonations,
  useExpenseMonthlyReport,
  useExpenseCategories,
  useExpenses,
  useFinanceBatches,
  useFinanceSummary,
} from '../../hooks/useDonations';
import { useDashboardReport } from '../../hooks/useReports';
import { useMembers } from '../../hooks/useMembers';
import { donationsService } from '../../services/donationsService';
import { CHURCH_SERVICE_TYPES, DONATION_METHODS, STANDARD_FINANCE_FUNDS } from '../../utils/constants';
import { formatCurrency, formatDate } from '../../utils/formatters';

const currentYear = new Date().getFullYear();
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const ACTION_CARDS = [
  {
    id: 'collection',
    label: 'Church Collection',
    description: 'Record offertory, harvest, thanksgiving, and other general collections.',
    color: 'bg-success-50 ring-success-100 text-success-700',
    activeColor: 'bg-success-700 text-white',
    icon: Banknote,
  },
  {
    id: 'tithe',
    label: 'Member Tithe',
    description: 'Record tithe linked to a specific member for accurate statements.',
    color: 'bg-brand-50 ring-brand-100 text-brand-700',
    activeColor: 'bg-brand-700 text-white',
    icon: TrendingUp,
  },
  {
    id: 'expense',
    label: 'Record Expense',
    description: 'Record welfare, utilities, maintenance, or any church spending.',
    color: 'bg-accent-50 ring-accent-100 text-accent-700',
    activeColor: 'bg-accent-700 text-white',
    icon: Receipt,
  },
];

function localISO(date) {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
}
function todayISO() { return localISO(new Date()); }
function firstDayOfMonthISO() {
  const now = new Date();
  return localISO(new Date(now.getFullYear(), now.getMonth(), 1));
}
function lastDayOfMonthISO() {
  const now = new Date();
  return localISO(new Date(now.getFullYear(), now.getMonth() + 1, 0));
}
function firstDayOfYearISO() {
  return localISO(new Date(new Date().getFullYear(), 0, 1));
}
function lastDayOfYearISO() {
  return localISO(new Date(new Date().getFullYear(), 11, 31));
}
function defaultDonationForm() {
  return { member_id: '', batch_id: '', fund_id: '', amount: '', currency: 'GHS', payment_method: 'cash', reference: '', donation_date: todayISO(), notes: '' };
}
function defaultExpenseForm() {
  return { category_id: '', amount: '', expense_date: todayISO(), currency: 'GHS', payment_method: 'cash', vendor_name: '', reference: '', notes: '' };
}
function defaultBatchForm() {
  const today = todayISO();
  return { title: `Sunday Service Collection — ${today}`, service_date: today, service_type: 'sunday_service', notes: '' };
}

function SectionLabel({ children }) {
  return <p className="label-caps mb-3">{children}</p>;
}

function BreakdownList({ items, loading, emptyLabel }) {
  if (loading) return <LoadingSpinner label="Loading…" />;
  if (!items?.length) return <p className="text-sm text-slate-500">{emptyLabel}</p>;
  return (
    <div className="space-y-1.5">
      {items.map((item) => (
        <div key={item.name || item.fund} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm">
          <span className="text-slate-600">{item.name || item.fund}</span>
          <span className="font-bold text-slate-900">{formatCurrency(item.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function DonationsPage({ view = 'overview' }) {
  const [searchParams] = useSearchParams();
  const [activeAction, setActiveAction] = useState('collection');
  const [selectedBatchId, setSelectedBatchId] = useState(() => searchParams.get('batch_id') || '');
  const [message, setMessage] = useState('');
  const [exporting, setExporting] = useState(false);
  const [filters, setFilters] = useState({ start_date: '', end_date: '', fund_id: '', category_id: '' });
  const [donationForm, setDonationForm] = useState(defaultDonationForm());
  const [batchForm, setBatchForm] = useState(defaultBatchForm());
  const [fundForm, setFundForm] = useState({ name: '', description: '' });
  const [expenseForm, setExpenseForm] = useState(defaultExpenseForm());
  const [expenseCategoryForm, setExpenseCategoryForm] = useState({ name: '', description: '' });

  const reportFilters = useMemo(() => ({
    start_date: filters.start_date || undefined,
    end_date: filters.end_date || undefined,
    fund_id: filters.fund_id || undefined,
    category_id: filters.category_id || undefined,
    batch_id: selectedBatchId || undefined,
  }), [filters, selectedBatchId]);

  const donationsQuery = useDonations({ skip: 0, limit: 20, batch_id: selectedBatchId || undefined, fund_id: filters.fund_id || undefined, start_date: filters.start_date || undefined, end_date: filters.end_date || undefined });
  const expensesQuery = useExpenses({ skip: 0, limit: 20, category_id: filters.category_id || undefined, start_date: filters.start_date || undefined, end_date: filters.end_date || undefined });
  const fundsQuery = useDonationFunds();
  const batchesQuery = useFinanceBatches({ include_closed: true });
  const expenseCategoriesQuery = useExpenseCategories();
  const membersQuery = useMembers({ skip: 0, limit: 100 });
  const annualReportQuery = useDonationAnnualReport(currentYear, reportFilters);
  const dashboardQuery = useDashboardReport();
  const incomeTrendQuery = useDonationMonthlyReport({ year: currentYear, ...reportFilters });
  const expenseTrendQuery = useExpenseMonthlyReport({ year: currentYear, ...reportFilters });
  const summaryQuery = useFinanceSummary({ start_date: filters.start_date || undefined, end_date: filters.end_date || undefined, batch_id: selectedBatchId || undefined, fund_id: filters.fund_id || undefined, category_id: filters.category_id || undefined });

  const createDonationMutation = useCreateDonation();
  const createBatchMutation = useCreateFinanceBatch();
  const closeBatchMutation = useCloseFinanceBatch();
  const createExpenseMutation = useCreateExpense();
  const createFundMutation = useCreateDonationFund();
  const createExpenseCategoryMutation = useCreateExpenseCategory();
  const bootstrapFundsMutation = useBootstrapDonationFunds();
  const bootstrapExpenseCategoriesMutation = useBootstrapExpenseCategories();

  const funds = fundsQuery.data?.data ?? [];
  const batches = batchesQuery.data?.data ?? [];
  const openBatches = batches.filter((batch) => !batch.is_closed);
  const members = membersQuery.data?.data ?? [];
  const donationRows = donationsQuery.data?.data ?? [];
  const expenseRows = expensesQuery.data?.data ?? [];
  const expenseCategories = expenseCategoriesQuery.data?.data ?? [];
  const annual = annualReportQuery.data?.data;
  const dashboard = dashboardQuery.data?.data ?? {};
  const summary = summaryQuery.data?.data ?? {};
  const incomeTrend = (incomeTrendQuery.data?.data ?? []).map((item) => ({ ...item, month: MONTH_NAMES[(item.month ?? 1) - 1] ?? item.month }));
  const expenseTrend = (expenseTrendQuery.data?.data ?? []).map((item) => ({ ...item, month: MONTH_NAMES[(item.month ?? 1) - 1] ?? item.month }));
  const openBatchCount = batches.filter((batch) => !batch.is_closed).length;
  const closedBatchCount = batches.filter((batch) => batch.is_closed).length;
  const annualTotal = annual?.total ?? 0;

  const isOverview = view === 'overview';
  const isGiving = view === 'giving';
  const isExpenses = view === 'expenses';
  const isBatches = view === 'batches';
  const isFunds = view === 'funds';
  const isReports = view === 'reports';
  const selectedAction = isExpenses ? 'expense' : activeAction === 'expense' ? 'collection' : activeAction;

  const activeBatch = batches.find((b) => b.id === (donationForm.batch_id || selectedBatchId)) ?? null;
  const titheFund = funds.find((f) => String(f.code).toLowerCase() === 'tithe') ?? null;
  const selectedCollectionFund = funds.find((f) => f.id === donationForm.fund_id);
  const selectedExpenseCategory = expenseCategories.find((c) => c.id === expenseForm.category_id);

  const setupReady = useMemo(() => ({
    fundsLoaded: funds.length > 0,
    categoriesLoaded: expenseCategories.length > 0,
    batchOpen: batches.length > 0,
  }), [funds.length, expenseCategories.length, batches.length]);

  const todayChecklist = [
    { label: 'Standard church funds loaded', done: setupReady.fundsLoaded, icon: Banknote },
    { label: 'Expense categories ready', done: setupReady.categoriesLoaded, icon: Receipt },
    { label: 'Service collection open', done: Boolean(activeBatch), icon: FolderOpen },
  ];

  const presetFilters = [
    { label: 'Today', start_date: todayISO(), end_date: todayISO(), apply: () => setFilters((p) => ({ ...p, start_date: todayISO(), end_date: todayISO() })) },
    { label: 'This Month', start_date: firstDayOfMonthISO(), end_date: lastDayOfMonthISO(), apply: () => setFilters((p) => ({ ...p, start_date: firstDayOfMonthISO(), end_date: lastDayOfMonthISO() })) },
    { label: 'This Year', start_date: firstDayOfYearISO(), end_date: lastDayOfYearISO(), apply: () => setFilters((p) => ({ ...p, start_date: firstDayOfYearISO(), end_date: lastDayOfYearISO() })) },
    { label: 'Clear Dates', start_date: '', end_date: '', apply: () => setFilters((p) => ({ ...p, start_date: '', end_date: '' })) },
  ];
  const activePreset = presetFilters.find((item) => item.start_date === filters.start_date && item.end_date === filters.end_date)?.label;

  function resetFilters() {
    setFilters({ start_date: '', end_date: '', fund_id: '', category_id: '' });
    setSelectedBatchId('');
  }

  async function onExportSummary() {
    setExporting(true);
    try {
      const response = await donationsService.exportSummary({ start_date: filters.start_date || undefined, end_date: filters.end_date || undefined, batch_id: selectedBatchId || undefined, fund_id: filters.fund_id || undefined, category_id: filters.category_id || undefined });
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'finance-summary.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setMessage('Finance summary exported.');
    } finally {
      setExporting(false);
    }
  }

  async function onCreateBatch(event) {
    event.preventDefault();
    setMessage('');
    const response = await createBatchMutation.mutateAsync(batchForm);
    const batchId = response.data.data.id;
    setSelectedBatchId(batchId);
    setDonationForm((prev) => ({ ...prev, batch_id: batchId, donation_date: batchForm.service_date }));
    setMessage('Service collection opened. Next, record the giving against it.');
  }

  async function onCloseBatch(batch) {
    const confirmed = window.confirm(`Close “${batch.title}”? Confirm that the recorded total has been counted and checked.`);
    if (!confirmed) return;
    await closeBatchMutation.mutateAsync(batch.id);
    setMessage(`“${batch.title}” is closed. New entries can no longer be added to it.`);
  }

  async function onCreateDonation(event) {
    event.preventDefault();
    setMessage('');
    await createDonationMutation.mutateAsync({ ...donationForm, member_id: donationForm.member_id || null, batch_id: donationForm.batch_id || selectedBatchId || null, amount: Number(donationForm.amount), payment_method: donationForm.payment_method || null, reference: donationForm.reference || null, notes: donationForm.notes || null });
    const label = selectedAction === 'tithe'
      ? `Saved ${formatCurrency(donationForm.amount || 0)} as tithe.`
      : `Saved ${formatCurrency(donationForm.amount || 0)} as ${selectedCollectionFund?.name || 'church collection'}.`;
    setDonationForm((prev) => ({ ...defaultDonationForm(), batch_id: prev.batch_id, donation_date: prev.donation_date, fund_id: selectedAction === 'tithe' && titheFund ? titheFund.id : '' }));
    setMessage(label);
  }

  async function onCreateExpense(event) {
    event.preventDefault();
    setMessage('');
    await createExpenseMutation.mutateAsync({ ...expenseForm, amount: Number(expenseForm.amount), payment_method: expenseForm.payment_method || null, vendor_name: expenseForm.vendor_name || null, reference: expenseForm.reference || null, notes: expenseForm.notes || null });
    setExpenseForm(defaultExpenseForm());
    setMessage(`Saved ${formatCurrency(expenseForm.amount || 0)} as ${selectedExpenseCategory?.name || 'expense'}.`);
  }

  async function onCreateFund(event) {
    event.preventDefault();
    setMessage('');
    await createFundMutation.mutateAsync({ name: fundForm.name, description: fundForm.description || null });
    setFundForm({ name: '', description: '' });
    setMessage('Fund created.');
  }

  async function onCreateExpenseCategory(event) {
    event.preventDefault();
    setMessage('');
    await createExpenseCategoryMutation.mutateAsync({ name: expenseCategoryForm.name, description: expenseCategoryForm.description || null });
    setExpenseCategoryForm({ name: '', description: '' });
    setMessage('Expense category created.');
  }

  async function onBootstrapFunds() {
    setMessage('');
    const response = await bootstrapFundsMutation.mutateAsync();
    const count = response.data.data.length;
    setMessage(count > 0 ? `Added ${count} standard funds.` : 'Standard funds already exist.');
  }

  async function onBootstrapExpenseCategories() {
    setMessage('');
    const response = await bootstrapExpenseCategoriesMutation.mutateAsync();
    const count = response.data.data.length;
    setMessage(count > 0 ? `Added ${count} expense categories.` : 'Expense categories already exist.');
  }

  function switchAction(next) {
    setActiveAction(next);
    if (next === 'tithe' && titheFund) setDonationForm((prev) => ({ ...prev, fund_id: titheFund.id }));
    if (next === 'collection' && titheFund && donationForm.fund_id === titheFund.id) setDonationForm((prev) => ({ ...prev, fund_id: '' }));
  }

  const incomeColumns = [
    { key: 'donation_date', label: 'Date', render: (row) => formatDate(row.donation_date) },
    { key: 'fund_name', label: 'Fund' },
    { key: 'member_name', label: 'Member', render: (row) => row.member_name || 'General collection' },
    { key: 'batch_title', label: 'Batch', render: (row) => row.batch_title || '—' },
    { key: 'amount', label: 'Amount', render: (row) => formatCurrency(row.amount, row.currency || 'GHS') },
  ];

  const expenseColumns = [
    { key: 'expense_date', label: 'Date', render: (row) => formatDate(row.expense_date) },
    { key: 'category_name', label: 'Category' },
    { key: 'vendor_name', label: 'Vendor / Payee', render: (row) => row.vendor_name || '—' },
    { key: 'amount', label: 'Amount', render: (row) => formatCurrency(row.amount, row.currency || 'GHS') },
    { key: 'payment_method', label: 'Method' },
  ];

  const batchColumns = [
    { key: 'title', label: 'Collection' },
    { key: 'service_date', label: 'Service Date', render: (row) => formatDate(row.service_date) },
    { key: 'service_type', label: 'Service Type' },
    { key: 'total_amount', label: 'Collected', render: (row) => formatCurrency(row.total_amount ?? 0) },
    { key: 'transaction_count', label: 'Entries' },
    { key: 'is_closed', label: 'Status', render: (row) => row.is_closed ? <span className="font-semibold text-slate-500">Closed</span> : <span className="font-semibold text-success-700">Open</span> },
    {
      key: 'actions',
      label: 'Next step',
      render: (row) => row.is_closed ? (
        <span className="text-xs text-slate-400">Reconciled</span>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Link to={`/finance/giving?batch_id=${row.id}`} className="text-xs font-bold text-brand-700 hover:text-brand-900">Record giving</Link>
          <button type="button" onClick={() => onCloseBatch(row)} disabled={closeBatchMutation.isPending} className="text-xs font-bold text-accent-700 hover:text-accent-900 disabled:opacity-50">Close</button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {message && (
        <p className="rounded-xl bg-success-50 px-4 py-3 text-sm font-medium text-success-700 ring-1 ring-success-100">
          {message}
        </p>
      )}

      {/* Overview keeps the high-level position and next actions together. */}
      {isOverview && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Income This Month" value={formatCurrency(dashboard.donations_this_month ?? 0)} tone="good" icon={TrendingUp} />
        <StatCard label="Expenses This Month" value={formatCurrency(dashboard.expenses_this_month ?? 0)} tone="warn" icon={TrendingDown} />
        <StatCard label="Net Flow" value={formatCurrency(dashboard.net_flow_this_month ?? 0)} tone={(dashboard.net_flow_this_month ?? 0) >= 0 ? 'good' : 'danger'} />
        <StatCard label="Annual Giving" value={formatCurrency(annual?.total ?? 0)} helper={`${currentYear} total`} />
      </div>}

      {/* Readiness checklist */}
      {isOverview && <div className="panel p-5">
        <SectionLabel>Today's Checklist</SectionLabel>
        <div className="grid gap-3 md:grid-cols-3">
          {todayChecklist.map(({ label, done, icon: Icon }) => (
            <div key={label} className={`flex items-start gap-3 rounded-2xl p-4 ring-1 ${done ? 'bg-success-50 ring-success-100' : 'bg-church-50 ring-church-100'}`}>
              <div className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl ${done ? 'bg-success-700' : 'bg-church-700'}`}>
                {done ? <CheckCircle2 size={16} className="text-white" /> : <Icon size={16} className="text-white" />}
              </div>
              <div>
                <p className={`text-xs font-bold uppercase tracking-wide ${done ? 'text-success-700' : 'text-church-700'}`}>{done ? 'Ready' : 'Needs attention'}</p>
                <p className="mt-0.5 text-sm font-medium text-slate-800">{label}</p>
              </div>
            </div>
          ))}
        </div>
      </div>}

      {/* Action selector */}
      {isOverview && <div className="panel p-5">
        <SectionLabel>What do you want to record?</SectionLabel>
        <div className="grid gap-4 lg:grid-cols-3">
          {ACTION_CARDS.map((card) => {
            const target = card.id === 'expense' ? '/finance/expenses' : '/finance/giving';
            return (
              <Link
                key={card.id}
                to={target}
                className="rounded-2xl border border-slate-200 bg-white p-5 text-left transition hover:border-brand-300 hover:bg-brand-50"
              >
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100">
                    <card.icon size={18} className="text-slate-500" />
                  </div>
                </div>
                <p className="font-bold text-slate-900">{card.label}</p>
                <p className="mt-1 text-xs text-slate-500">{card.description}</p>
                <p className="mt-4 text-xs font-bold text-brand-700">Open page →</p>
              </Link>
            );
          })}
        </div>
      </div>}

      {isOverview && (
        <div className="grid gap-4 md:grid-cols-2">
          <Link to="/finance/reports" className="panel p-5 transition hover:ring-2 hover:ring-brand-200">
            <p className="text-sm font-bold text-slate-900">Review financial reports</p>
            <p className="mt-1 text-sm text-slate-500">Filter income and expenses, compare categories, and export a CSV.</p>
            <p className="mt-4 text-xs font-bold text-brand-700">Open reports →</p>
          </Link>
          <Link to="/finance/batches" className="panel p-5 transition hover:ring-2 hover:ring-brand-200">
            <p className="text-sm font-bold text-slate-900">Manage service batches</p>
            <p className="mt-1 text-sm text-slate-500">Open a service batch, record the giving, and close it after the count is checked.</p>
            <p className="mt-4 text-xs font-bold text-brand-700">Open service batches →</p>
          </Link>
        </div>
      )}

      {isGiving && (
        <div className="panel p-5">
          <SectionLabel>Giving entry</SectionLabel>
          <div className="flex flex-wrap gap-2">
            {ACTION_CARDS.filter((card) => card.id !== 'expense').map((card) => {
              const isActive = selectedAction === card.id;
              return (
                <button
                  key={card.id}
                  type="button"
                  onClick={() => switchAction(card.id)}
                  className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${isActive ? 'bg-brand-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                >
                  <card.icon size={16} />
                  {card.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Main action form + sidebar */}
      {(isGiving || isExpenses) && <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        {/* Left — form */}
        <div className="panel p-6">
          {/* Collection form */}
          {selectedAction === 'collection' && (
            <>
              <SectionLabel>Record Church Collection</SectionLabel>
              <form onSubmit={onCreateDonation} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Service Batch (recommended)</label>
                    <select className="field" value={donationForm.batch_id || selectedBatchId} onChange={(e) => { const batchId = e.target.value; const batch = openBatches.find((b) => b.id === batchId); setSelectedBatchId(batchId); setDonationForm((prev) => ({ ...prev, batch_id: batchId, donation_date: batch?.service_date || prev.donation_date })); }}>
                      <option value="">No collection / Direct entry</option>
                      {openBatches.map((batch) => <option key={batch.id} value={batch.id}>{batch.title} — {formatDate(batch.service_date)}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Collection Type *</label>
                    <select className="field" value={donationForm.fund_id} onChange={(e) => setDonationForm((prev) => ({ ...prev, fund_id: e.target.value }))} required>
                      <option value="">Select what you are recording</option>
                      {funds.filter((f) => !f.requires_member).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Amount (GHS) *</label>
                    <input className="field" type="number" min="0.01" step="0.01" placeholder="0.00" value={donationForm.amount} onChange={(e) => setDonationForm((prev) => ({ ...prev, amount: e.target.value }))} required />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Payment Method</label>
                    <select className="field" value={donationForm.payment_method} onChange={(e) => setDonationForm((prev) => ({ ...prev, payment_method: e.target.value }))}>
                      {DONATION_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Date *</label>
                    <input className="field" type="date" value={donationForm.donation_date} onChange={(e) => setDonationForm((prev) => ({ ...prev, donation_date: e.target.value }))} required />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Reference (optional)</label>
                    <input className="field" placeholder="Cheque no., mobile ref, etc." value={donationForm.reference} onChange={(e) => setDonationForm((prev) => ({ ...prev, reference: e.target.value }))} />
                  </div>
                  <div className="md:col-span-2">
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Notes (optional)</label>
                    <input className="field" placeholder="Any additional notes" value={donationForm.notes} onChange={(e) => setDonationForm((prev) => ({ ...prev, notes: e.target.value }))} />
                  </div>
                </div>
                <button type="submit" className="btn-primary" disabled={createDonationMutation.isPending || Boolean(activeBatch?.is_closed)}>
                  <Banknote size={15} />
                  {createDonationMutation.isPending ? 'Saving…' : 'Save Collection Entry'}
                </button>
              </form>
            </>
          )}

          {/* Tithe form */}
          {selectedAction === 'tithe' && (
            <>
              <SectionLabel>Record Member Tithe</SectionLabel>
              <form onSubmit={onCreateDonation} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="md:col-span-2">
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Member *</label>
                    <select className="field" value={donationForm.member_id} onChange={(e) => setDonationForm((prev) => ({ ...prev, member_id: e.target.value, fund_id: titheFund?.id || prev.fund_id }))} required>
                      <option value="">Select member</option>
                      {members.map((m) => <option key={m.id} value={m.id}>{m.first_name} {m.last_name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Tithe Fund</label>
                    <input className="field bg-slate-50 text-slate-500" value={titheFund?.name || 'Tithe fund not loaded yet'} disabled />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Service Batch (optional)</label>
                    <select className="field" value={donationForm.batch_id || selectedBatchId} onChange={(e) => { const batchId = e.target.value; const batch = openBatches.find((b) => b.id === batchId); setSelectedBatchId(batchId); setDonationForm((prev) => ({ ...prev, batch_id: batchId, donation_date: batch?.service_date || prev.donation_date, fund_id: titheFund?.id || prev.fund_id })); }}>
                      <option value="">No collection</option>
                      {openBatches.map((b) => <option key={b.id} value={b.id}>{b.title}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Amount (GHS) *</label>
                    <input className="field" type="number" min="0.01" step="0.01" placeholder="0.00" value={donationForm.amount} onChange={(e) => setDonationForm((prev) => ({ ...prev, amount: e.target.value, fund_id: titheFund?.id || prev.fund_id }))} required />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Payment Method</label>
                    <select className="field" value={donationForm.payment_method} onChange={(e) => setDonationForm((prev) => ({ ...prev, payment_method: e.target.value, fund_id: titheFund?.id || prev.fund_id }))}>
                      {DONATION_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Date *</label>
                    <input className="field" type="date" value={donationForm.donation_date} onChange={(e) => setDonationForm((prev) => ({ ...prev, donation_date: e.target.value, fund_id: titheFund?.id || prev.fund_id }))} required />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Reference (optional)</label>
                    <input className="field" value={donationForm.reference} onChange={(e) => setDonationForm((prev) => ({ ...prev, reference: e.target.value, fund_id: titheFund?.id || prev.fund_id }))} />
                  </div>
                  <div className="md:col-span-2">
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Notes (optional)</label>
                    <input className="field" value={donationForm.notes} onChange={(e) => setDonationForm((prev) => ({ ...prev, notes: e.target.value, fund_id: titheFund?.id || prev.fund_id }))} />
                  </div>
                </div>
                <button type="submit" className="btn-primary" disabled={createDonationMutation.isPending || !titheFund || Boolean(activeBatch?.is_closed)}>
                  <TrendingUp size={15} />
                  {createDonationMutation.isPending ? 'Saving…' : 'Save Member Tithe'}
                </button>
              </form>
            </>
          )}

          {/* Expense form */}
          {selectedAction === 'expense' && (
            <>
              <SectionLabel>Record Church Expense</SectionLabel>
              <form onSubmit={onCreateExpense} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Expense Category *</label>
                    <select className="field" value={expenseForm.category_id} onChange={(e) => setExpenseForm((prev) => ({ ...prev, category_id: e.target.value }))} required>
                      <option value="">Select category</option>
                      {expenseCategories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Amount (GHS) *</label>
                    <input className="field" type="number" min="0.01" step="0.01" placeholder="0.00" value={expenseForm.amount} onChange={(e) => setExpenseForm((prev) => ({ ...prev, amount: e.target.value }))} required />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Expense Date *</label>
                    <input className="field" type="date" value={expenseForm.expense_date} onChange={(e) => setExpenseForm((prev) => ({ ...prev, expense_date: e.target.value }))} required />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Payment Method</label>
                    <select className="field" value={expenseForm.payment_method} onChange={(e) => setExpenseForm((prev) => ({ ...prev, payment_method: e.target.value }))}>
                      {DONATION_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Vendor / Payee</label>
                    <input className="field" placeholder="Who was paid?" value={expenseForm.vendor_name} onChange={(e) => setExpenseForm((prev) => ({ ...prev, vendor_name: e.target.value }))} />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Reference (optional)</label>
                    <input className="field" value={expenseForm.reference} onChange={(e) => setExpenseForm((prev) => ({ ...prev, reference: e.target.value }))} />
                  </div>
                  <div className="md:col-span-2">
                    <label className="mb-1.5 block text-sm font-semibold text-slate-700">Notes (optional)</label>
                    <input className="field" value={expenseForm.notes} onChange={(e) => setExpenseForm((prev) => ({ ...prev, notes: e.target.value }))} />
                  </div>
                </div>
                <button type="submit" className="btn-danger" disabled={createExpenseMutation.isPending}>
                  <Receipt size={15} />
                  {createExpenseMutation.isPending ? 'Saving…' : 'Save Expense'}
                </button>
              </form>
            </>
          )}

        </div>

        {/* Right — status sidebar */}
        {isGiving && <div className="space-y-4">
          {/* Selected service batch card */}
          <div className="panel p-5">
            <SectionLabel>Selected Service Batch</SectionLabel>
            <div className={`rounded-2xl p-4 ${activeBatch ? 'bg-brand-50 ring-1 ring-brand-100' : 'bg-slate-50'}`}>
              <p className="text-sm font-bold text-slate-900">{activeBatch ? activeBatch.title : 'No batch selected'}</p>
              <p className="mt-1 text-xs text-slate-500">
                {activeBatch ? `${formatDate(activeBatch.service_date)} · ${activeBatch.service_type}${activeBatch.is_closed ? ' · Closed' : ''}` : 'Choose an open service batch to group these entries.'}
              </p>
              {activeBatch?.is_closed && <p className="mt-2 text-xs font-semibold text-accent-700">This batch is closed. Select an open batch before saving a new entry.</p>}
            </div>
            {activeBatch && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Batch Total</p>
                  <p className="mt-1 text-xl font-bold text-slate-900">{formatCurrency(activeBatch?.total_amount ?? 0)}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Entries</p>
                  <p className="mt-1 text-xl font-bold text-slate-900">{activeBatch?.transaction_count ?? 0}</p>
                </div>
              </div>
            )}
          </div>

          <div className="panel p-5">
            <SectionLabel>Income Records</SectionLabel>
            {!activeBatch ? (
              <p className="text-sm text-slate-500">Select a Service Batch to see its income records.</p>
            ) : donationsQuery.isLoading ? (
              <LoadingSpinner label="Loading income records…" />
            ) : !donationRows.length ? (
              <p className="text-sm text-slate-500">No income recorded for this batch yet.</p>
            ) : (
              <div className="space-y-2">
                {donationRows.map((row) => (
                  <div key={row.id} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-800">{row.fund_name || 'Income'}</p>
                      <p className="truncate text-xs text-slate-500">
                        {row.member_name || 'General collection'} · {row.payment_method || 'Method not specified'}
                      </p>
                    </div>
                    <span className="shrink-0 text-sm font-bold text-slate-900">{formatCurrency(row.amount, row.currency || 'GHS')}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>}
      </div>}

      {/* Finance filter + summary */}
      {isReports && <div className="flex flex-col gap-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Income" value={formatCurrency(summary.income_total ?? 0)} tone="good" icon={TrendingUp} />
          <StatCard label="Expenses" value={formatCurrency(summary.expense_total ?? 0)} tone="warn" icon={TrendingDown} />
          <StatCard label="Net" value={formatCurrency(summary.net_total ?? 0)} tone={(summary.net_total ?? 0) >= 0 ? 'good' : 'danger'} />
          <StatCard label={`Annual Giving ${currentYear}`} value={formatCurrency(annualTotal)} helper="All funds combined" />
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          {incomeTrendQuery.isLoading ? <div className="panel p-5"><LoadingSpinner label="Loading income trend…" /></div> : <TrendBars title={`Monthly Giving ${currentYear}`} data={incomeTrend} color="bg-success-700" />}
          {expenseTrendQuery.isLoading ? <div className="panel p-5"><LoadingSpinner label="Loading expense trend…" /></div> : <TrendBars title={`Monthly Expenses ${currentYear}`} data={expenseTrend} color="bg-accent-700" />}
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <div className="panel p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="label-caps mb-1">Annual giving by fund</p>
                <p className="text-sm text-slate-500">Where giving has been directed this year.</p>
              </div>
              <p className="text-lg font-extrabold text-slate-900">{formatCurrency(annualTotal)}</p>
            </div>
            <BreakdownList items={annual?.funds} loading={annualReportQuery.isLoading} emptyLabel="No giving records yet." />
          </div>
          <div className="panel p-5">
            <p className="label-caps mb-1">Service batch position</p>
            <p className="mb-4 text-sm text-slate-500">Track whether service collections still need review.</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-brand-50 p-4">
                <p className="text-xs font-semibold text-brand-700">Open batches</p>
                <p className="mt-1 text-2xl font-extrabold text-brand-900">{openBatchCount}</p>
                <p className="mt-1 text-xs text-brand-700">Still accepting entries</p>
              </div>
              <div className="rounded-2xl bg-success-50 p-4">
                <p className="text-xs font-semibold text-success-700">Closed batches</p>
                <p className="mt-1 text-2xl font-extrabold text-success-900">{closedBatchCount}</p>
                <p className="mt-1 text-xs text-success-700">Reviewed and reconciled</p>
              </div>
            </div>
          </div>
        </div>

        <div className="order-first panel p-5">
        <SectionLabel>Filter & Summary</SectionLabel>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">From Date</label>
            <input className="field" type="date" value={filters.start_date} onChange={(e) => setFilters((p) => ({ ...p, start_date: e.target.value }))} />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">To Date</label>
            <input className="field" type="date" value={filters.end_date} onChange={(e) => setFilters((p) => ({ ...p, end_date: e.target.value }))} />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">Income Category</label>
            <select className="field" value={filters.fund_id} onChange={(e) => setFilters((p) => ({ ...p, fund_id: e.target.value }))}>
              <option value="">All categories</option>
              {funds.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">Expense Category</label>
            <select className="field" value={filters.category_id} onChange={(e) => setFilters((p) => ({ ...p, category_id: e.target.value }))}>
              <option value="">All categories</option>
              {expenseCategories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button type="button" onClick={resetFilters} className="btn-outline flex-1">Reset</button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {presetFilters.map((item) => (
            <button key={item.label} type="button" onClick={item.apply} className={`rounded-full border px-4 py-1.5 text-sm font-semibold transition ${activePreset === item.label ? 'border-brand-300 bg-brand-50 text-brand-700 ring-2 ring-brand-100' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>
              {item.label}
            </button>
          ))}
          <button type="button" onClick={onExportSummary} disabled={exporting} className="rounded-full bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60 transition">
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-100 p-4">
            <p className="label-caps mb-3">Income by Category</p>
            <BreakdownList items={summary.income_by_fund} loading={summaryQuery.isLoading} emptyLabel="No income data for this filter." />
          </div>
          <div className="rounded-2xl border border-slate-100 p-4">
            <p className="label-caps mb-3">Expenses by Category</p>
            <BreakdownList items={summary.expenses_by_category} loading={summaryQuery.isLoading} emptyLabel="No expense data for this filter." />
          </div>
        </div>
        </div>
      </div>}

      {/* Ledger */}
      {(isGiving || isExpenses) && <div className="panel p-5">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-base font-bold text-slate-900">{isGiving ? 'Giving ledger' : 'Expense ledger'}</p>
            <p className="mt-1 text-sm text-slate-500">Review recently recorded {isGiving ? 'giving entries' : 'expenses'}.</p>
          </div>
        </div>

        {isGiving ? (
          <>
            <div className="mb-4">
              <select className="field max-w-xs" value={selectedBatchId} onChange={(e) => { setSelectedBatchId(e.target.value); setDonationForm((prev) => ({ ...prev, batch_id: e.target.value })); }}>
                <option value="">All batches</option>
                {batches.map((b) => <option key={b.id} value={b.id}>{b.title}</option>)}
              </select>
            </div>
            {donationsQuery.isLoading ? <LoadingSpinner label="Loading income records…" /> : (
              <DataTable columns={incomeColumns} rows={donationRows} emptyLabel="No income records yet" />
            )}
          </>
        ) : expensesQuery.isLoading ? (
          <LoadingSpinner label="Loading expense records…" />
        ) : (
          <DataTable columns={expenseColumns} rows={expenseRows} emptyLabel="No expense records yet" />
        )}
      </div>}

      {/* Batches page */}
      {isBatches && (
        <div className="space-y-5">
          <div className="panel p-5">
            <SectionLabel>Step 1 — Open a service batch</SectionLabel>
            <p className="mb-4 text-sm text-slate-500">The Finance Officer opens one batch for each service or event. Giving entries are attached to it, then the batch is closed after the count is confirmed. Super Admin can also create one.</p>
            <form onSubmit={onCreateBatch} className="grid gap-3 md:grid-cols-2">
              <input className="field" value={batchForm.title} onChange={(e) => setBatchForm((p) => ({ ...p, title: e.target.value }))} placeholder="Service batch name" required />
              <input className="field" type="date" value={batchForm.service_date} onChange={(e) => setBatchForm((p) => ({ ...p, service_date: e.target.value }))} required />
              <select className="field" value={batchForm.service_type} onChange={(e) => setBatchForm((p) => ({ ...p, service_type: e.target.value }))}>
                {CHURCH_SERVICE_TYPES.map((service) => <option key={service.value} value={service.value}>{service.label}</option>)}
              </select>
              <input className="field" value={batchForm.notes} onChange={(e) => setBatchForm((p) => ({ ...p, notes: e.target.value }))} placeholder="Notes (optional)" />
              <button type="submit" className="btn-primary md:col-span-2 md:w-fit">{createBatchMutation.isPending ? 'Opening…' : 'Open Service Batch'}</button>
            </form>
            {selectedBatchId && (
              <Link to={`/finance/giving?batch_id=${selectedBatchId}`} className="mt-4 inline-flex text-sm font-bold text-brand-700 hover:text-brand-900">
                Record giving for this collection →
              </Link>
            )}
          </div>
          <div className="panel p-5">
            <div className="mb-4">
              <p className="text-base font-bold text-slate-900">Service batches</p>
              <p className="mt-1 text-sm text-slate-500">Step 2: record giving. Step 3: close each batch after the total is checked.</p>
            </div>
            {batchesQuery.isLoading ? <LoadingSpinner label="Loading service batches…" /> : <DataTable columns={batchColumns} rows={batches} emptyLabel="No service batches yet" />}
          </div>
        </div>
      )}

      {/* Funds and categories page */}
      {isFunds && (
        <div className="space-y-5">
          <div className="panel p-5">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-base font-bold text-slate-900">Church funds</p>
                <p className="mt-1 text-sm text-slate-500">These funds appear when the finance team records giving.</p>
              </div>
              <button type="button" onClick={onBootstrapFunds} className="btn-outline text-xs">{bootstrapFundsMutation.isPending ? 'Adding…' : 'Load Standard Funds'}</button>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {funds.map((fund) => (
                <div key={fund.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="font-bold text-slate-900">{fund.name}</p>
                  <p className="mt-1 text-xs text-slate-500">{fund.requires_member ? 'Member linked' : 'General collection'}</p>
                  {fund.description && <p className="mt-3 text-xs leading-5 text-slate-500">{fund.description}</p>}
                </div>
              ))}
            </div>
            {!funds.length && <p className="text-sm text-slate-500">No funds configured yet. Load the standard church funds to begin.</p>}
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <form onSubmit={onCreateFund} className="panel space-y-3 p-5">
              <SectionLabel>Add custom fund</SectionLabel>
              <input className="field" placeholder="Fund name" value={fundForm.name} onChange={(e) => setFundForm((p) => ({ ...p, name: e.target.value }))} required />
              <input className="field" placeholder="Description (optional)" value={fundForm.description} onChange={(e) => setFundForm((p) => ({ ...p, description: e.target.value }))} />
              <button type="submit" className="btn-primary">{createFundMutation.isPending ? 'Saving…' : 'Add Fund'}</button>
            </form>
            <form onSubmit={onCreateExpenseCategory} className="panel space-y-3 p-5">
              <SectionLabel>Add expense category</SectionLabel>
              <input className="field" placeholder="Category name" value={expenseCategoryForm.name} onChange={(e) => setExpenseCategoryForm((p) => ({ ...p, name: e.target.value }))} required />
              <input className="field" placeholder="Description (optional)" value={expenseCategoryForm.description} onChange={(e) => setExpenseCategoryForm((p) => ({ ...p, description: e.target.value }))} />
              <button type="submit" className="btn-primary">{createExpenseCategoryMutation.isPending ? 'Saving…' : 'Add Category'}</button>
            </form>
          </div>

          <div className="panel p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-base font-bold text-slate-900">Expense categories</p>
                <p className="mt-1 text-sm text-slate-500">Use categories to keep church spending easy to review.</p>
              </div>
              <button type="button" onClick={onBootstrapExpenseCategories} className="btn-outline text-xs">{bootstrapExpenseCategoriesMutation.isPending ? 'Adding…' : 'Load Standard Categories'}</button>
            </div>
            <div className="flex flex-wrap gap-2">
              {expenseCategories.map((category) => <span key={category.id} className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">{category.name}</span>)}
            </div>
            {!expenseCategories.length && <p className="text-sm text-slate-500">No expense categories configured yet.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
