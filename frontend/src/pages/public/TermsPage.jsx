import LegalPage, { ContactLine } from './LegalPage';

const sections = [
  {
    heading: 'The service',
    body: <p>Ekklesia is a web service for managing a church: members, attendance, giving, communication and reports. A church signs up, becomes the account holder, and invites its own team. These terms are an agreement between the church (the “Customer”) and Ekklesia (“we”).</p>,
  },
  {
    heading: 'Accounts and access',
    body: (
      <>
        <p>The person who creates a church confirms they are authorised to act for it. Customers are responsible for the people they invite, the roles they give them, and keeping passwords confidential. Tell us promptly if you suspect an account has been compromised.</p>
        <p>You must give accurate sign-up information and be at least 18 years old to create an account.</p>
      </>
    ),
  },
  {
    heading: 'Your data',
    body: (
      <>
        <p>Your church’s data belongs to your church. We process it only to provide the service, as described in our Privacy Policy. You can export members, giving, attendance and first-timers at any time from Settings.</p>
        <p>You are responsible for having a lawful basis to record the personal information you enter about members, visitors and donors, including any consent you need to send them SMS or email messages.</p>
      </>
    ),
  },
  {
    heading: 'Acceptable use',
    body: <p>Do not use Ekklesia to break the law, to send spam or unsolicited bulk messages, to harass anyone, to store data you have no right to hold, to probe or disrupt the service, or to access another church’s data. We may suspend an account that does.</p>,
  },
  {
    heading: 'Plans, trial and payment',
    body: (
      <>
        <p>New churches start with a free trial. After it ends the account becomes read-only until a plan is paid for; nothing is deleted. Prices are shown in Ghana cedis on the Pricing page and may change with advance notice for future billing periods.</p>
        <p>Plans are paid per period and do not renew automatically; each renewal is a new invoice. SMS credits are prepaid and are used as messages are sent. Charges are for the service period or credits purchased; contact us about any billing problem.</p>
      </>
    ),
  },
  {
    heading: 'Messages you send',
    body: <p>SMS and email are delivered through third-party providers. We do not guarantee delivery by networks or devices. You are responsible for the content of messages you send and for their compliance with applicable law.</p>,
  },
  {
    heading: 'Closing your account',
    body: <p>A church administrator can close the account from Settings. Access stops immediately and your data is kept for a short grace period (30 days) so a mistake can be reversed by support, after which it is permanently deleted. Export your data before closing.</p>,
  },
  {
    heading: 'Suspension',
    body: <p>We may suspend or restrict an account for non-payment, breach of these terms or to protect the service or other customers. Where we can, we will tell you why and give you a chance to fix the problem.</p>,
  },
  {
    heading: 'Availability and liability',
    body: (
      <>
        <p>We work to keep Ekklesia available and secure but provide it “as is”, without a guarantee of uninterrupted or error-free operation. Keep your own copies of anything critical by using the export tools.</p>
        <p>To the extent the law allows, we are not liable for indirect or consequential losses, and our total liability for any claim is limited to the amount you paid us in the three months before it arose.</p>
      </>
    ),
  },
  {
    heading: 'Changes and governing law',
    body: <p>We may update these terms; material changes will be announced in the product or by email before they apply. These terms are governed by the laws of the Republic of Ghana.</p>,
  },
  {
    heading: 'Contact',
    body: <p>Questions about these terms: <ContactLine />.</p>,
  },
];

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      intro="Please read these terms before using Ekklesia. By creating an account or using the service you agree to them."
      sections={sections}
    />
  );
}
