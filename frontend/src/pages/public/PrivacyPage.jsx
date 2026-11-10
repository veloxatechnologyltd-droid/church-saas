import LegalPage, { ContactLine } from './LegalPage';

const sections = [
  {
    heading: 'Who is responsible for what',
    body: <p>Each church is the <strong>data controller</strong> for the information it records about its members, visitors and donors. Ekklesia acts as the church’s <strong>processor</strong>: we store and handle that data on the church’s behalf and on its instructions. For information about church staff accounts (names, email addresses, sign-in activity) and for billing, Ekklesia is the controller. We handle personal data in line with the Ghana Data Protection Act, 2012 (Act 843).</p>,
  },
  {
    heading: 'What we collect',
    body: (
      <ul className="list-disc space-y-1 pl-5">
        <li><strong>Account data:</strong> name, email, phone, password (stored only as a salted hash) and role.</li>
        <li><strong>Church records you enter:</strong> member profiles and contact details, families, groups, attendance, giving and pledges, first-timer and prayer-request forms, pastoral notes and messages sent.</li>
        <li><strong>Billing data:</strong> invoices and payment references. Mobile-money details are handled by the payment provider and are not stored by us.</li>
        <li><strong>Technical data:</strong> request logs (time, address, church) and an audit trail of changes, kept to secure and support the service.</li>
      </ul>
    ),
  },
  {
    heading: 'Sensitive information',
    body: <p>Giving records and pastoral notes can reveal religious belief and personal circumstances. Access is limited by role: staff only see what their role allows, and branch-limited staff only see their own branch. Every church’s data is isolated from every other church’s at the database level. Churches should record only what they need and tell the people concerned how it is used.</p>,
  },
  {
    heading: 'How we use it',
    body: <p>To run the service for your church, deliver the messages you ask us to send, take payment, keep the service secure, prevent abuse and provide support. We do not sell personal data and do not use church records for advertising.</p>,
  },
  {
    heading: 'Who we share it with',
    body: (
      <>
        <p>We use a small number of service providers (sub-processors) to operate Ekklesia. They receive only what they need:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Vercel: application hosting.</li>
          <li>Neon: database hosting.</li>
          <li>Cloudinary: storage of uploaded logos and member photos.</li>
          <li>SendGrid: email delivery (invitations, password resets).</li>
          <li>Arkesel: SMS delivery to the recipients a church chooses.</li>
          <li>Seevplus: payment processing for plan and SMS-credit purchases.</li>
        </ul>
        <p>Some providers process data outside Ghana. We require them to protect it appropriately. We may also disclose information where the law requires.</p>
      </>
    ),
  },
  {
    heading: 'Security',
    body: <p>Data is encrypted in transit, passwords are hashed, access is role-based, sign-in and public forms are rate-limited, and changes are recorded in an audit trail. Support access to a church is time-limited and is recorded in that church’s own audit trail. If we become aware of a breach affecting personal data we will notify affected churches and the regulator as the law requires.</p>,
  },
  {
    heading: 'Keeping and deleting data',
    body: <p>We keep a church’s data while its account is open. When a church closes its account, access stops immediately and, after a 30-day grace period, all of its data, uploaded files and staff accounts that belong to no other church are permanently deleted. Backups are rotated out on the provider’s normal schedule. Churches can export their data at any time before then.</p>,
  },
  {
    heading: 'Rights of individuals',
    body: <p>People whose information a church holds can ask <em>that church</em> to access, correct or delete it, or to stop contacting them; the church can do this inside Ekklesia, and we help on request. Staff can ask us about their own account data at <ContactLine />.</p>,
  },
  {
    heading: 'Cookies and storage',
    body: <p>We use browser storage only to keep you signed in and remember interface preferences. We do not use advertising or cross-site tracking cookies.</p>,
  },
  {
    heading: 'Changes and contact',
    body: <p>We will announce material changes to this policy in the product or by email. Contact: <ContactLine />.</p>,
  },
];

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      intro="This policy explains what personal information Ekklesia handles, why, and the choices churches and individuals have."
      sections={sections}
    />
  );
}
