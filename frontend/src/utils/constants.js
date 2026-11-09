export const ROLES = ['church_admin', 'secretary', 'finance', 'group_leader', 'member'];
export const ROLE_LABELS = {
  church_admin: 'Church Admin',
  secretary: 'Secretary',
  finance: 'Finance Officer',
  group_leader: 'Group Leader',
  member: 'Member',
};
export const MEMBERSHIP_STATUS = ['active', 'inactive', 'visitor', 'new_convert'];
export const GENDERS = ['male', 'female'];
export const MARITAL_STATUS = ['single', 'married', 'divorced', 'widowed'];
export const CHURCH_SERVICE_TYPES = [
  { value: 'sunday_service', label: 'Sunday Service' },
  { value: 'midweek_service', label: 'Midweek Service' },
  { value: 'bible_study', label: 'Bible Study' },
  { value: 'prayer_meeting', label: 'Prayer Meeting' },
  { value: 'youth_service', label: 'Youth Service' },
  { value: 'special_service', label: 'Special Service' },
];
export const DONATION_METHODS = ['cash', 'mobile_money', 'cheque', 'online'];
export const STANDARD_FINANCE_FUNDS = ['Tithe', 'Offering', 'Harvest', 'Thanksgiving', 'Missions', 'Welfare', 'Building Fund', 'Seed'];

export const VISITOR_STATUSES = [
  { value: 'new', label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'returning', label: 'Returning' },
  { value: 'converted', label: 'Converted' },
  { value: 'not_interested', label: 'Not interested' },
];
export const HOW_HEARD = ['Friend or family', 'Social media', 'Radio / TV', 'Walked past', 'Outreach / crusade', 'Website', 'Other'];
export const AGE_GROUPS = ['child', 'youth', 'adult', 'senior'];
export const PRAYER_STATUSES = [
  { value: 'new', label: 'New' },
  { value: 'praying', label: 'Praying' },
  { value: 'answered', label: 'Answered' },
  { value: 'closed', label: 'Closed' },
];
export const PRAYER_CATEGORIES = ['healing', 'family', 'finances', 'salvation', 'career', 'thanksgiving', 'other'];
export const COUNTRIES = [
  { code: 'GH', name: 'Ghana', currency: 'GHS', timezone: 'Africa/Accra' },
  { code: 'NG', name: 'Nigeria', currency: 'NGN', timezone: 'Africa/Lagos' },
  { code: 'KE', name: 'Kenya', currency: 'KES', timezone: 'Africa/Nairobi' },
  { code: 'ZA', name: 'South Africa', currency: 'ZAR', timezone: 'Africa/Johannesburg' },
  { code: 'GB', name: 'United Kingdom', currency: 'GBP', timezone: 'Europe/London' },
  { code: 'US', name: 'United States', currency: 'USD', timezone: 'America/New_York' },
];
