# DESIGN.md — Living Spring International Church CMS
## UI/UX Design System & Redesign Specification

**Designer Spec Author:** AI Design Lead (Google-level spec)
**Project:** Living Spring International Church Management System
**Date:** April 2026
**Version:** 1.0

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Color System — Extracted from Church Logo](#2-color-system)
3. [Typography](#3-typography)
4. [Spacing & Layout Grid](#4-spacing--layout-grid)
5. [Component Library](#5-component-library)
6. [Page-by-Page Designs](#6-page-by-page-designs)
7. [Navigation & Sidebar](#7-navigation--sidebar)
8. [Icon System](#8-icon-system)
9. [Responsive Breakpoints](#9-responsive-breakpoints)
10. [UX States & Patterns](#10-ux-states--patterns)
11. [Tailwind Config Changes](#11-tailwind-config-changes)
12. [Implementation Checklist](#12-implementation-checklist)

---

## 1. Design Principles

These four principles govern every design decision in this system:

### 1.1 Church People First
Users include elderly members, deacons, volunteers, and church secretaries — not tech workers.
- Label everything plainly: "Register Member", not "Create Resource"
- Use full words in buttons, not icons alone
- Never hide critical actions behind hover states

### 1.2 Clarity Over Density
Church staff open this system once a week (Sunday). They need to orient instantly.
- Large readable text (minimum 14px body)
- High contrast — WCAG AA minimum
- Generous padding on all interactive elements (minimum 44px touch target)
- Never show more than 5 stat cards on one row

### 1.3 Brand Identity is Sacred
The church logo has three specific swirl colors. Those colors ARE the brand.
Every CTA, badge, chart, and highlight must tie back to these three colors.
No arbitrary Tailwind blues or teals that don't come from the logo.

### 1.4 Mobile is Real
Church secretaries may use phones or tablets at the door during services.
- The layout must be fully usable at 390px width
- Sidebar collapses to a bottom navigation bar on mobile
- Forms stack to single column below md

---

## 2. Color System

### 2.1 Logo Color Extraction

The "Living Springs International Church" logo contains a dynamic triple-swirl emblem
with three distinct arc colors, and the wordmark text in the same crimson as one of the arcs.

```
Logo Color Palette:
┌─────────────────────────────────────────────────────┐
│  COBALT BLUE   │  hex: #1A4FA0  │  The upper-left arc  │
│  CRIMSON RED   │  hex: #C02416  │  The lower arc + wordmark text │
│  AMBER ORANGE  │  hex: #E07218  │  The right arc       │
└─────────────────────────────────────────────────────┘
```

### 2.2 Full Design Token Palette

#### Primary Brand — Cobalt Blue (from blue swirl)
Used for: primary CTAs, sidebar active states, links, form focus rings, chart bars

| Token           | Hex       | Usage                              |
|----------------|-----------|------------------------------------|
| `brand-50`     | `#EEF4FC` | Light backgrounds, hover tints     |
| `brand-100`    | `#D5E6F9` | Focus rings, selected row tints    |
| `brand-200`    | `#A8CCEE` | Borders on brand elements          |
| `brand-600`    | `#1E5BB5` | Hover states for primary buttons   |
| `brand-700`    | `#1A4FA0` | **Primary brand color — CTAs, active nav** |
| `brand-800`    | `#153F80` | Pressed/active button states       |
| `brand-900`    | `#0E2B58` | Deep brand backgrounds             |

#### Accent — Crimson Red (from red swirl + wordmark)
Used for: danger actions, delete buttons, low-attendance badges, important alerts

| Token           | Hex       | Usage                              |
|----------------|-----------|------------------------------------|
| `accent-50`    | `#FEF2F0` | Alert backgrounds                  |
| `accent-100`   | `#FDDBD7` | Badge backgrounds                  |
| `accent-600`   | `#D42A1A` | Hover on danger                    |
| `accent-700`   | `#C02416` | **Accent — danger, alerts, emphasis** |
| `accent-800`   | `#9A1C10` | Pressed danger                     |

#### Highlight — Amber Orange (from orange swirl)
Used for: "follow-up" badges, warning states, finance highlights, charts (income)

| Token           | Hex       | Usage                                   |
|----------------|-----------|-----------------------------------------|
| `amber-50`     | `#FFF8EE` | Warning tint backgrounds               |
| `amber-100`    | `#FFE9C4` | Warning badge backgrounds              |
| `amber-600`    | `#D06A14` | Hover on amber buttons                 |
| `amber-700`    | `#E07218` | **Amber — warnings, finance, charts**  |
| `amber-800`    | `#B85B12` | Pressed amber                          |

#### Semantic — Success Green
Used for: "stable" attendance, active status, positive trend

| Token        | Hex       | Usage                                  |
|-------------|-----------|----------------------------------------|
| `success-50` | `#F0FDF4` | Success backgrounds                    |
| `success-700`| `#15803D` | Success text, active member badge      |

#### Neutral — Slate (keep existing)
| Token        | Hex       | Usage                                  |
|-------------|-----------|----------------------------------------|
| `slate-50`   | `#F8FAFC` | Page background                        |
| `slate-100`  | `#F1F5F9` | Sidebar background                     |
| `slate-200`  | `#E2E8F0` | Card borders, dividers                 |
| `slate-400`  | `#94A3B8` | Placeholder text, disabled             |
| `slate-600`  | `#475569` | Secondary / muted text                 |
| `slate-800`  | `#1E293B` | Label text                             |
| `slate-900`  | `#0F172A` | Primary body text                      |
| `white`      | `#FFFFFF` | Card surfaces, inputs                  |

### 2.3 Color Roles Summary

```
PRIMARY ACTION   → brand-700  (#1A4FA0)  — "Register Member", sidebar active
DANGER ACTION    → accent-700 (#C02416)  — "Delete", "Deactivate"
WARNING / ALERT  → amber-700  (#E07218)  — "Follow Up", finance warnings
SUCCESS / GOOD   → success-700 (#15803D) — "Active", "Stable", positive stats
SURFACE          → white      (#FFFFFF)  — card/panel background
PAGE BACKGROUND  → slate-50   (#F8FAFC)  — root page background
SIDEBAR          → slate-100  (#F1F5F9)  — sidebar background (light sidebar)
PRIMARY TEXT     → slate-900  (#0F172A)
MUTED TEXT       → slate-600  (#475569)
BORDER           → slate-200  (#E2E8F0)
```

---

## 3. Typography

Font: **Manrope** (already installed — keep)
Fallback: `system-ui, -apple-system, sans-serif`

### 3.1 Type Scale

| Role                | Size  | Weight | Color       | Usage                              |
|--------------------|-------|--------|-------------|------------------------------------|
| `page-title`       | 28px  | 800    | slate-900   | Page headings ("Members")          |
| `section-heading`  | 20px  | 700    | slate-900   | Card/section titles                |
| `card-title`       | 16px  | 700    | slate-900   | Stat card labels                   |
| `body`             | 14px  | 500    | slate-800   | Table cells, descriptions          |
| `label`            | 12px  | 700    | slate-600   | Form labels, table headers         |
| `caption`          | 11px  | 600    | slate-400   | Section category labels (ALL CAPS) |
| `stat-number`      | 30px  | 800    | slate-900   | Big metric numbers on stat cards   |
| `stat-number-lg`   | 48px  | 800    | brand-700   | Hero metric on dashboard           |

### 3.2 Type Rules
- Line height: 1.5 for body, 1.2 for headings
- Letter spacing: 0.16em on ALL CAPS labels (tracking-widest)
- Avoid using text-xs for anything a user must act on
- Never use font-normal (400) for interactive elements — minimum 500 (medium)

---

## 4. Spacing & Layout Grid

### 4.1 Spacing Tokens (Tailwind scale)
```
4px  → gap between inline elements (icon + label)
8px  → padding inside compact badges/chips
12px → padding inside form inputs (py-3 px-4)
16px → card inner padding (p-4)
20px → section padding (p-5)
24px → card outer padding (p-6)
32px → section spacing (mb-8)
```

### 4.2 Layout Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  SIDEBAR (w-56 fixed)  │  MAIN CONTENT AREA (flex-1)            │
│                        │  ┌──────────────────────────────────┐  │
│  [Logo + Church Name]  │  │  TOP NAV BAR (h-16 sticky)       │  │
│                        │  │  [Search] [Bell] [User Avatar]   │  │
│  ─ Core ────────────   │  └──────────────────────────────────┘  │
│  • Dashboard           │                                         │
│  • Members             │  ┌──────────────────────────────────┐  │
│  • Attendance          │  │  PAGE CONTENT (scrollable)       │  │
│                        │  │  [PageHeader]                    │  │
│  ─ Ministry ────────   │  │  [Stat Cards Row]                │  │
│  • Finance             │  │  [Main Content Grid]             │  │
│  • Groups              │  └──────────────────────────────────┘  │
│  • Events              │                                         │
│  • Communication       │                                         │
│  • Reports             │                                         │
│                        │                                         │
│  ─────────────────     │                                         │
│  [User Avatar + Name]  │                                         │
│  [Role badge]          │                                         │
│  [Logout]              │                                         │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 Sidebar Width
- Desktop (lg+): `w-56` (224px) — fixed, not sticky
- Tablet (md): collapsible overlay, toggled by hamburger
- Mobile (sm): bottom navigation bar with icons only

### 4.4 Content max-width
- Max content width: `max-w-screen-2xl` with `mx-auto` and `px-6` padding
- Stat cards: 4-column grid on xl, 2-column on sm, 1-column on mobile

---

## 5. Component Library

### 5.1 Sidebar Navigation Item

**Default (inactive):**
```
[ icon ] Label
bg: transparent | text: slate-700 | icon: slate-400
hover: bg-slate-200/80, text: slate-900, icon: slate-700
border-radius: rounded-xl
padding: px-3 py-2.5
```

**Active:**
```
[ icon ] Label
bg: brand-700 | text: white | icon: white
left-border: none (use background fill instead)
border-radius: rounded-xl
font-weight: 600
```

**With badge (e.g., unread count):**
```
[ icon ] Label    [count]
Badge: bg-accent-700, text-white, rounded-full, px-2 text-xs
```

### 5.2 Stat Card

Structure:
```
┌────────────────────────────────┐
│  [icon]              [trend ↑] │  ← icon: colored bg circle (brand/amber/accent/green)
│                                │
│  248                           │  ← large bold number (text-3xl font-extrabold)
│  Total Members                 │  ← label (text-sm font-semibold text-slate-600)
│  All registered records        │  ← helper (text-xs text-slate-400)
└────────────────────────────────┘
```

**Variants:**
- `default` — icon bg: brand-100, icon color: brand-700
- `good` (growth/positive) — icon bg: success-50, icon color: success-700, number: success-700
- `warn` (needs action) — icon bg: amber-50, icon color: amber-700, number: amber-700
- `danger` (critical) — icon bg: accent-50, icon color: accent-700, number: accent-700

**Icon suggestions per card:**
- Total Members → `Users` icon
- New This Month → `UserPlus` icon
- Low Attendance → `AlertTriangle` icon
- Income → `TrendingUp` icon
- Expenses → `TrendingDown` icon
- Attendance % → `BarChart2` icon
- Upcoming Events → `CalendarDays` icon

### 5.3 Page Header

```
┌────────────────────────────────────────────────────────────┐
│  [Page Title — 28px extrabold]     [Action Button(s) →]   │
│  [Subtitle — 14px slate-600]                               │
│  ─────────────────────────────────────────────────────     │
└────────────────────────────────────────────────────────────┘
```
- Title: `text-2xl font-extrabold text-slate-900`
- Subtitle: `text-sm text-slate-500 mt-1`
- Bottom border: `border-b border-slate-200 pb-4 mb-6`
- Breadcrumb (optional): small path above title `Dashboard / Members`

### 5.4 Buttons

**Primary:**
```
bg: brand-700 | text: white | hover: brand-800
rounded-xl | px-4 py-2.5 | text-sm font-semibold
icon (optional): mr-2, size-4
```

**Secondary / Outline:**
```
bg: white | border: slate-300 | text: slate-700 | hover: bg-slate-50
rounded-xl | px-4 py-2.5 | text-sm font-semibold
```

**Danger:**
```
bg: accent-700 | text: white | hover: accent-800
rounded-xl | px-4 py-2.5 | text-sm font-semibold
```

**Ghost (table actions):**
```
bg: transparent | text: brand-700 | hover: bg-brand-50
rounded-lg | px-2 py-1 | text-xs font-semibold
```

**Icon-only button:**
```
bg: white | border: slate-200 | h-9 w-9
rounded-lg | flex items-center justify-center
hover: bg-slate-100
```

### 5.5 Form Fields

**Input:**
```css
.field {
  w-full rounded-xl border border-slate-300 bg-white
  px-4 py-2.5 text-sm text-slate-800
  outline-none transition
  placeholder: text-slate-400
  focus: border-brand-700 ring-2 ring-brand-100
}
```

**Label:**
```
text-sm font-semibold text-slate-700 mb-1.5
```

**Error state:**
```
border-accent-700 ring-2 ring-accent-100
error message: text-xs text-accent-700 mt-1
```

**Select:**
Same as input with a chevron icon on the right

**Textarea:**
Same as input, min-h-24

**Field group (label + input + helper):**
```
<div class="space-y-1.5">
  <label>...</label>
  <input class="field" />
  <p class="text-xs text-slate-400">Helper text</p>  {/* optional */}
</div>
```

### 5.6 Status Badges

```
Active:      bg-success-50  text-success-700  ring-success-200
Inactive:    bg-slate-100   text-slate-600    ring-slate-200
Visitor:     bg-brand-50    text-brand-700    ring-brand-200
New Convert: bg-amber-50    text-amber-700    ring-amber-200
Follow Up:   bg-accent-50   text-accent-700   ring-accent-200
```

All badges: `rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 inline-flex`

### 5.7 Data Table

```
Table wrapper: panel overflow-hidden  (no inner padding — table edge-to-edge)
Table header:  bg-slate-50 border-b border-slate-200
               th: px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500
Table row:     border-b border-slate-100 hover:bg-brand-50/40 transition
               td: px-4 py-3.5 text-sm text-slate-700
               first td: font-semibold text-slate-900
Striping:      none — use hover highlight only
Responsive:    wrap in overflow-x-auto
```

### 5.8 Cards / Panels

```css
.panel {
  rounded-2xl bg-white shadow-sm ring-1 ring-slate-200
}
```

**Card with colored left accent border:**
```
border-l-4 border-brand-700 (or accent/amber/success)
rounded-r-2xl rounded-l-none (for list items)
```

**Chart card:**
```
panel p-5
  header: flex justify-between items-center mb-4
  chart area: min-h-48
```

### 5.9 Top Navigation Bar

```
┌────────────────────────────────────────────────────────────────┐
│  [Hamburger]  [Breadcrumb / Page Title]    [Bell] [Avatar]    │
└────────────────────────────────────────────────────────────────┘
bg: white/95 backdrop-blur sticky top-0 z-20
height: h-16
border-bottom: border-b border-slate-200
padding: px-6
```

**Notification Bell:**
- Bell icon with a red dot (accent-700 bg) when unread announcements exist
- Dropdown list of announcements on click

**User Avatar:**
- Initials circle: bg-brand-100 text-brand-800 font-bold
- Dropdown: "My Profile", "Change Password", "Logout"

### 5.10 Mobile Bottom Navigation (< md breakpoint)

```
┌──────────────────────────────────────────────────────────────┐
│  [Dashboard]  [Members]  [Attendance]  [Finance]  [More...]  │
│     icon         icon        icon        icon       icon     │
│     label        label       label       label      label    │
└──────────────────────────────────────────────────────────────┘
height: h-16  bg: white  border-top: border-t border-slate-200
Active tab: icon + label in brand-700
Inactive: icon + label in slate-400
```

---

## 6. Page-by-Page Designs

### 6.1 Login Page

**Layout:** Full-screen split. Left panel = brand. Right panel = form.

**Left Panel (brand side) — `bg-brand-900` with brand gradient:**
```
Background: linear-gradient from brand-900 to brand-700
Corner decorations: two large circles (white/10 opacity)

Content:
  [Church Logo Image — centered, w-20 h-20]
  "Living Springs International Church"  (text-white font-bold text-2xl, mt-6)
  Tagline: "Managing God's people with purpose."  (text-white/80 text-sm mt-2)

  Divider line (mt-8 mb-8, border-white/20)

  Feature pills (3 items, each on own line):
  ✓  "Real-time member visibility"
  ✓  "Role-based access control"
  ✓  "Attendance and finance insights"
  (text-white/90, text-sm, each with a check icon in amber-400)

  Footer: "Built for Living Spring, Accra, Ghana"
         (text-white/40 text-xs, absolute bottom-6)
```

**Right Panel (form side) — `bg-white`:**
```
Centered form, max-w-sm mx-auto

  [Small logo] (20x20, tucked top)
  "Welcome back"  (text-2xl font-extrabold text-slate-900)
  "Sign in to your account"  (text-sm text-slate-500 mt-1)

  mt-8:
  Email field (label + input)
  Password field (label + input + "show password" eye icon toggle)
  [Error message if any]

  mt-6:
  [Sign In →]  (btn-primary w-full)
```

---

### 6.2 Dashboard Page

**Header:**
```
"Good morning, John 👋"  (text-2xl font-extrabold text-slate-900)
"Sunday, 18 April 2026 — Here's what's happening at Living Spring."
(text-sm text-slate-500)
```

**Row 1 — Stat Cards (5 columns on xl, 2 on sm):**
```
[Total Members]  [New This Month]  [Last Sunday Attendance]  [Income (MTD)]  [Expenses (MTD)]
   icon: Users    icon: UserPlus    icon: BarChart2             icon: TrendUp   icon: TrendDown
   tone: default  tone: good        tone: default              tone: good      tone: warn
```

**Row 2 — Hero Metric Card (full width):**
```
┌──────────────────────────────────────────────────────┐
│  Live Snapshot                                        │
│  Church operations at a glance                        │
│                                                       │
│  [Attendance this month: 72%  ████████░░ ]           │
│  [Net Cash Flow: GHS 6,000    ████████░░ ]           │
│  [Member Growth: +12 (5%)     ██████░░░░ ]           │
└──────────────────────────────────────────────────────┘
```
Uses horizontal progress bars (custom component) with brand/amber/success colors.

**Row 3 — Charts (4 columns on xl, 2 on lg):**
```
[Monthly Attendance bar chart]  [Monthly Income bar chart]
[Monthly Expenses bar chart]    [Member Growth line chart]
```
Chart colors:
- Attendance → brand-700
- Income → success-700
- Expenses → accent-700
- Growth → amber-700

**Row 4 — Activity + Alerts (2 columns on lg):**
```
┌──────────────────────────┐  ┌──────────────────────────────┐
│  Upcoming Events (3)     │  │  Pastoral Follow-Up (18)     │
│  ─────────────────────   │  │  ───────────────────────────  │
│  [date] [title] [arrow]  │  │  [avatar][name][last seen]   │
│  [date] [title] [arrow]  │  │  [avatar][name][last seen]   │
│  [View all events →]     │  │  [View all members →]        │
└──────────────────────────┘  └──────────────────────────────┘
```

**Row 5 — Quick Actions (3 columns):**
```
[Members Directory]  [Attendance Desk]  [Finance Center]
(panel with icon, title, description, CTA link)
Icon backgrounds: brand-50, amber-50, success-50
```

---

### 6.3 Members Page

**Page Header:**
```
Members                             [Register Member +]  [Export CSV ↓]
Browse, search and manage your congregation.
```

**Stat Row (4 cards):**
```
[Total Members]  [Active]  [Pastoral Follow-Up]  [Page X/Y]
```

**Filter Bar:**
```
┌──────────────────────────────────────────────────────────────┐
│  [🔍 Search by name, phone, email...]  [Status ▼]  [Clear]  │
└──────────────────────────────────────────────────────────────┘
panel p-4
```

**Member Table:**
```
Columns: [Avatar + Name (link)] | Phone | Email | Status (badge) | Joined | Risk (badge)
Row hover: bg-brand-50/40
Name cell: font-semibold text-brand-700 (clickable)
Photo: rounded-full h-10 w-10 ring-1 ring-slate-200
       fallback: bg-brand-100 initials in brand-800
```

**Pagination:**
```
"Showing 20 of 248 members"       [← Previous]  [1]  [2] ... [Next →]
(text-sm text-slate-600)          (outline buttons)
```

---

### 6.4 Member Profile Page

**Hero Header:**
```
┌──────────────────────────────────────────────────────────────┐
│  [Large Avatar 80px]  John Kwame Asante           [Edit ✏]  │
│                       Secretary · Joined Jan 2023            │
│                       [Active ●]  [🎂 May 14]                │
│                       📱 +233 24 123 4567  ✉ john@gmail.com │
└──────────────────────────────────────────────────────────────┘
bg: brand-900 gradient panel (like login left panel, subtle)
text: white
```

**Tab Navigation (below header):**
```
[Overview]  [Attendance]  [Giving]  [Groups]
Underline tab style: brand-700 underline, 2px, active tab
```

**Tab: Overview**
```
Two columns:
Left: Personal Details card
  - Date of Birth, Gender, Marital Status, Occupation, Address, Emergency Contact
Right: Optional Family Household card
  - No family, existing household selector, or create new family
```

**Tab: Attendance**
```
Top: attendance % ring chart (circular) + "Present X / Total Y sessions"
     Punctuality: "On time X times"
Below: Attendance history table
  Date | Service | Status (Present/Absent) | Checked in at
```

**Tab: Giving**
```
Top: Total Tithe (YTD) | Total Giving (YTD) — two metric cards
Below: Giving history table
  Date | Fund | Amount | Method
Bottom: [Download Statement]
```

**Tab: Groups**
```
List of groups member belongs to:
[Group Name]  [Role in group]  [Leader: ...]  [joined date]
```

---

### 6.5 Member Registration Page

**Layout:** Single-column centered form, max-w-2xl, inside a white panel

**Form Sections (Accordion or visible stacked sections):**

```
Section 1: Personal Information
  First Name* | Last Name*
  Date of Birth | Gender
  Phone* | Email
  Address | Occupation

Section 2: Church Details
  Membership Status* | Date Joined*
  Department / Ministry (optional, freetext)
  Family (existing household or new)

Section 3: Emergency Contact
  Name | Phone | Relationship

Section 4: Profile Photo
  Upload area (drag & drop or click to select)
  Preview thumbnail
```

**Submit bar (sticky bottom on mobile):**
```
[Cancel]  [Register Member →]
```

---

### 6.6 Attendance Page

**Page Header:**
```
Attendance                              [+ New Session]
Track Sunday services and special events.
```

**Session Selector bar:**
```
┌─────────────────────────────────────────────────────────────┐
│  Session:  [Sunday Service — 13 April 2026 ▼]   [🔄 Load] │
│  Or:  [Create new session]                                   │
└─────────────────────────────────────────────────────────────┘
```

**Session Stats (3 cards):**
```
[Total Members]  [Present]  [Attendance %]
```

**Attendance Marking Grid:**
```
View toggle: [Grid] [Table]

GRID VIEW:
─────────────────────────────────────────────────────────────
Each member = a card (4 per row on desktop):
┌─────────────────┐
│  [Avatar]       │
│  John Asante    │
│  [✓ Present] [✗]│  ← toggle buttons
└─────────────────┘

TABLE VIEW:
[Avatar + Name] | [Present] | [Absent] | [Checked in at]
(radio/checkbox per row for bulk marking)
```

**Bulk Actions bar (appears when items selected):**
```
[3 selected]  [Mark Present]  [Mark Absent]  [Clear Selection]
```

---

### 6.7 Finance Page

**Tab Navigation (full width horizontal tabs):**
```
[Service Batches]  [Giving]  [Expenses]  [Funds]  [Reports]
```

**Tab: Giving**
```
Header: [Record Giving +]
Filter: Date range, Fund type, Member name, Payment method

Stat row:
[Total This Month]  [Tithe Collected]  [Offering]  [Other Funds]

Table:
Date | Member (if applicable) | Fund | Amount | Method | Batch | Recorded by
```

**Tab: Expenses**
```
Header: [Record Expense +]
Table: Date | Category | Description | Amount | Recorded by
Stat row: [Total Expenses MTD] [Top Category]
```

**Tab: Service Batches**
```
Header: [New Batch +]
A service batch = one service day's collection envelope
Each row: Batch name | Date | Service type | Total collected | Status
Click to expand: shows all giving records in that batch
```

**Tab: Funds**
```
Grid of fund cards:
[Tithe]  [Offering]  [Harvest]  [Missions]
[Welfare]  [Building]  [Thanksgiving]  [+ Custom]
Each card: Fund name, total YTD, icon (configurable)
```

**Tab: Reports**
```
Top: [Monthly Giving Chart] | [Monthly Expenses Chart]
Bottom: Member giving statement search
  Enter member name → [Download PDF Statement]
  Date range selector
```

---

### 6.8 Departments & Ministries Page

**Page Header:**
```
Departments & Ministries                    [+ Create Department]
Manage each church department as one complete ministry team.
```

**Departments Grid (3 per row on xl):**
```
┌──────────────────────────────────┐
│  [group icon/color swatch]       │
│  Men's Fellowship                │
│  12 members  ·  Leader: Kwame    │
│  ─────────────────────────────── │
│  [View Members →]  [Edit]        │
└──────────────────────────────────┘
```
Department icon color: cycle through brand-700, accent-700, amber-700, success-700

**Department Detail (slide-over panel or separate page):**
```
Header: Department name, description, leader
Member list: searchable, with add/remove actions. There are no sub-units under a department.
```

---

### 6.9 Events & Calendar Page

**View Toggle:**
```
[Calendar View]  [List View]   ← top-right toggle
```

**Calendar View:**
```
Standard monthly calendar grid
Events appear as colored pills on date cells:
  - Sunday Service → brand-700 pill
  - Midweek → amber-700 pill
  - Special → accent-700 pill
```

**List View:**
```
Grouped by month:

APRIL 2026
────────────────────────────────
[Icon]  Easter Sunday Service     Sun, 20 Apr  ·  8:00 AM
        Main Auditorium  ·  All Members

[Icon]  Youth Retreat             Sat, 26 Apr  ·  6:00 AM
        Accra Beach Resort  ·  Youth Ministry

MAY 2026
────────────────────────────────
...
```

**Event Detail Panel (slide-over):**
```
Title, Date/Time, Location
Description
Capacity: 200 / 250 registered
[Register Member]  [Send Reminder]  [Edit]  [Delete]
```

---

### 6.10 Communication Page

**Layout: Two-panel**
```
┌─────────────────────────────┐  ┌──────────────────────────────┐
│  COMPOSE (left)             │  │  HISTORY (right)             │
│  ─────────────────────────  │  │  ──────────────────────────  │
│  [SMS]  [Email]  [Announce] │  │  Filter: type | date         │
│                             │  │  ────────────────────────    │
│  Send to:                   │  │  Apr 14 · SMS · 248 sent     │
│  [All] [Group▼] [Custom]    │  │  "Sunday service reminder"   │
│                             │  │  ────────────────────────    │
│  Message:                   │  │  Apr 7 · Email · 200 sent    │
│  [textarea]                 │  │  "Monthly newsletter"        │
│                             │  │                              │
│  [Send Message →]           │  │                              │
└─────────────────────────────┘  └──────────────────────────────┘
```

**Automatic Reminders tab:** configure a weekly day, Africa/Accra time, audience (all members, active members, inactive members, or one department), and SMS template. Show active/paused state and last run.

---

### 6.11 Reports Page

**Layout: Analytics dashboard**

**Header Row:**
```
Reports & Analytics                [Export Members CSV] [Export Finance Excel]
Attendance, growth, and financial trends for Living Spring.
```

**Date Range Selector (global filter):**
```
[Last 6 months ▼]  [Custom Range]
```

**Charts grid (2x2 on desktop):**
```
┌─────────────────────┐  ┌─────────────────────┐
│ Monthly Attendance  │  │ Member Growth        │
│ (bar chart)         │  │ (line chart)         │
└─────────────────────┘  └─────────────────────┘
┌─────────────────────┐  ┌─────────────────────┐
│ Monthly Income      │  │ Income vs Expenses   │
│ (bar chart)         │  │ (green/red line chart)│
└─────────────────────┘  └─────────────────────┘
```

**Summary table (below charts):**
```
Month-by-month breakdown: Month | Members | Attendance % | Income | Expenses | Net
```

---

### 6.12 Pastoral Care Page

**Purpose:** turn attendance concerns and member care needs into assigned,
trackable actions rather than standalone notes.

```
[Open Care]  [Overdue]  [Due Today]  [Completed]

[Attendance and membership concerns]
Member | Status | Reason | [Start follow-up]

[Open] [Overdue] [Completed] [All]              [Search]

Member care card:
Member | Membership status | Priority | Due state
Care notes
Action type | Next date | Assigned owner | Source
[Edit] [Complete / Reopen]
```

The creation form supports all membership statuses, an action type, priority,
care owner, next follow-up date, and detailed notes. Group leaders see only
records assigned to them.

---

## 7. Navigation & Sidebar

### 7.1 Full Sidebar Structure

```
┌──────────────────────────────┐
│  [Church Logo img, h-10]     │   ← actual logo from /img/
│  Living Springs              │   text-base font-bold text-slate-900
│  International Church        │   text-xs text-slate-500
├──────────────────────────────┤
│                              │
│  CORE                        │   caption label
│  [LayoutDashboard] Dashboard │
│  [Users]          Members    │
│  [CheckSquare]    Attendance │
│                              │
│  MINISTRY                    │   caption label
│  [Banknote]       Finance    │
│  [UsersRound]     Groups     │
│  [CalendarDays]   Events     │
│  [MessageSquare]  Communication│
│  [BarChart3]      Reports    │
│                              │
├──────────────────────────────┤
│  [Avatar] John Okyere        │   bottom pinned
│           Super Admin        │   role badge
│  [LogOut] Sign out           │   text-accent-700 hover
└──────────────────────────────┘
```

### 7.2 Sidebar Styling
```
Background:   bg-white (clean white sidebar)
Width:        w-56 (224px)
Height:       h-screen sticky top-0
Right border: border-r border-slate-200
Padding:      p-4
Shadow:       shadow-sm
```

### 7.3 Top Navbar (when sidebar is present)
```
Background:     bg-white/95 backdrop-blur
Sticky:         sticky top-0 z-20
Height:         h-16
Border bottom:  border-b border-slate-200
Left content:   [Breadcrumb] or [Page title — text-base font-semibold]
Right content:  [Announcements bell] [User avatar dropdown]
```

---

## 8. Icon System

Use **Lucide React** icons throughout (`lucide-react` package).
Size: `size-4` (16px) inline with text, `size-5` (20px) in sidebar, `size-6` (24px) stat cards.

### 8.1 Page Icon Map

| Page / Feature     | Lucide Icon          |
|-------------------|----------------------|
| Dashboard          | `LayoutDashboard`    |
| Members            | `Users`              |
| Member Profile     | `UserCircle`         |
| Register Member    | `UserPlus`           |
| Attendance         | `CheckSquare`        |
| Finance / Giving   | `Banknote`           |
| Expenses           | `Receipt`            |
| Funds              | `Landmark`           |
| Batches            | `FolderOpen`         |
| Groups             | `UsersRound`         |
| Events             | `CalendarDays`       |
| Communication      | `MessageSquare`      |
| SMS                | `Smartphone`         |
| Email              | `Mail`               |
| Announcement       | `Megaphone`          |
| Reports            | `BarChart3`          |
| Export             | `Download`           |
| Settings           | `Settings`           |
| Logout             | `LogOut`             |
| Edit               | `Pencil`             |
| Delete             | `Trash2`             |
| Search             | `Search`             |
| Filter             | `Filter`             |
| Alert / Follow-up  | `AlertTriangle`      |
| Check / Stable     | `CheckCircle2`       |
| Income / Tithe     | `TrendingUp`         |
| Expense            | `TrendingDown`       |
| Birthday           | `Cake`               |
| Phone              | `Phone`              |
| Email address      | `AtSign`             |
| Location           | `MapPin`             |
| Family             | `Home`               |

---

## 9. Responsive Breakpoints

### Tailwind breakpoints used:

| Breakpoint | Width   | Layout change                              |
|-----------|---------|---------------------------------------------|
| `sm`      | 640px   | 2-column grids, stack forms                |
| `md`      | 768px   | Sidebar appears (collapsible drawer)        |
| `lg`      | 1024px  | Sidebar fixed, 3-column content grids       |
| `xl`      | 1280px  | 4–5 column stat rows, full chart grid       |
| `2xl`     | 1536px  | Max content width cap (max-w-screen-2xl)   |

### Mobile-specific (< md):
- Sidebar hidden → bottom nav bar with 5 icons (Dashboard, Members, Attendance, Finance, More)
- "More" opens a slide-up drawer with remaining nav items
- Tables scroll horizontally (overflow-x-auto)
- All forms single-column
- Stat cards 2-per-row (not 5)
- Buttons full-width in forms

---

## 10. UX States & Patterns

### 10.1 Loading States
```
Component-level skeleton loaders (not full-page spinners):
  - Stat cards: pulse grey rectangles in place of numbers
  - Tables: 5 skeleton rows
  - Charts: grey placeholder rectangle
  - Page-level: only use full spinner when entire route is loading
```

### 10.2 Empty States
```
When no data is found:
  [Icon — large, slate-300]
  "No members found"
  "Try adjusting your search filters."
  [optional: CTA button — "Register first member"]

Position: centered in the table/content area
Icon size: size-12, text-slate-300
Title: text-base font-semibold text-slate-500
Sub: text-sm text-slate-400
```

### 10.3 Error States
```
API error:
  [AlertTriangle icon — accent-700]
  "Something went wrong"
  "Unable to load members. Please try again."
  [Try Again] button — outline style
```

### 10.4 Success Feedback
```
Inline success message (not toast):
  bg-success-50 ring-1 ring-success-200 rounded-xl px-4 py-3
  [CheckCircle2 icon — success-700] "Member registered successfully."

For destructive actions:
  Confirmation dialog (ShadCN AlertDialog):
  "Delete Member?"
  "This will permanently remove John Asante from the system."
  [Cancel] [Delete Member — btn-danger]
```

### 10.5 Forms — Validation
```
Real-time validation on blur (not on keystroke)
Required field error: shows below the input in text-xs text-accent-700
Required indicator: red asterisk (*) after label, text-accent-700
Disabled submit while submitting: opacity-60 cursor-not-allowed
```

### 10.6 Attendance Quick-Mark UX
```
One-tap mark: tap card → green border → "Present" confirmed instantly
Double-tap or long-press: toggle back to absent
Undo strip: "[✓ Marked John present]  [Undo]" — 4 second auto-dismiss
Bulk mode: header checkbox selects all → mark all present/absent
```

---

## 11. Tailwind Config Changes

Replace the current `tailwind.config.js` brand colors with the full logo-derived palette:

```javascript
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#EEF4FC',
          100: '#D5E6F9',
          200: '#A8CCEE',
          600: '#1E5BB5',
          700: '#1A4FA0',  // PRIMARY — cobalt blue from logo
          800: '#153F80',
          900: '#0E2B58',
        },
        accent: {
          50:  '#FEF2F0',
          100: '#FDDBD7',
          600: '#D42A1A',
          700: '#C02416',  // ACCENT — crimson red from logo
          800: '#9A1C10',
        },
        amber: {
          // extend Tailwind's amber to match logo orange
          50:  '#FFF8EE',
          100: '#FFE9C4',
          600: '#D06A14',
          700: '#E07218',  // HIGHLIGHT — amber orange from logo
          800: '#B85B12',
        },
        success: {
          50:  '#F0FDF4',
          700: '#15803D',
        },
      },
      fontFamily: {
        sans: ['Manrope', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
```

### index.css CSS Variables Update:
```css
:root {
  --cms-ink:          #0F172A;
  --cms-muted:        #475569;
  --cms-border:       #E2E8F0;
  --cms-surface:      #FFFFFF;
  --cms-surface-soft: #F8FAFC;
  --cms-brand:        #1A4FA0;   /* cobalt blue — logo primary */
  --cms-brand-soft:   #EEF4FC;
  --cms-accent:       #C02416;   /* crimson red — logo secondary */
  --cms-amber:        #E07218;   /* amber orange — logo tertiary */
  --cms-success:      #15803D;
}
```

---

## 12. Implementation Checklist

Work through these tasks in order. Each item maps to a code change.

### Phase 1 — Design Tokens & Base (do first, everything depends on this)
- [ ] Update `tailwind.config.js` with full color palette (Section 11)
- [ ] Update `src/index.css` CSS variables and body background (Section 11)
- [ ] Add `lucide-react` to package.json and install

### Phase 2 — Layout Shell
- [ ] Redesign `Sidebar.jsx` — add icons, logo image, user profile section at bottom, section labels
- [ ] Redesign `Navbar.jsx` (top bar) — sticky, breadcrumb, notification bell, avatar dropdown
- [ ] Redesign `Layout.jsx` — proper grid with sidebar + main, mobile bottom nav
- [ ] Update `LoadingSpinner.jsx` — skeleton loader version

### Phase 3 — Shared Components
- [ ] Redesign `StatCard.jsx` — icon + tone variants (default/good/warn/danger)
- [ ] Redesign `PageHeader.jsx` — bottom border, breadcrumb, action slot
- [ ] Redesign `DataTable.jsx` — proper header styling, hover rows, overflow-x-auto
- [ ] Create `Badge.jsx` — status badge component with all variants
- [ ] Create `EmptyState.jsx` — reusable empty state with icon + text + CTA
- [ ] Create `ConfirmDialog.jsx` — ShadCN AlertDialog wrapper for destructive actions

### Phase 4 — Authentication
- [ ] Redesign `LoginPage.jsx` — new left panel with actual logo, feature list, brand gradient

### Phase 5 — Dashboard
- [ ] Redesign `DashboardPage.jsx` — greeting, progress bars, charts, activity panels

### Phase 6 — Members Module
- [ ] Redesign `MembersPage.jsx` — improved filter bar, better table
- [ ] Redesign `MemberProfilePage.jsx` — hero header, tabbed layout
- [ ] Redesign `MemberRegistrationPage.jsx` — sectioned form with progress

### Phase 7 — Attendance Module
- [ ] Redesign `AttendancePage.jsx` — session selector, grid/table toggle, bulk actions

### Phase 8 — Finance Module
- [ ] Redesign `DonationsPage.jsx` — tabbed interface (Giving/Expenses/Batches/Funds/Reports)

### Phase 9 — Other Modules
- [ ] Redesign `GroupsPage.jsx` — group cards grid
- [ ] Redesign `EventsPage.jsx` — list view + calendar view toggle
- [ ] Redesign `CommunicationPage.jsx` — two-panel compose + history
- [ ] Redesign `ReportsPage.jsx` — analytics grid with export actions

### Phase 10 — Polish
- [ ] Implement mobile bottom navigation bar
- [ ] Add skeleton loaders to all data-fetching components
- [ ] Add empty states to all list/table pages
- [ ] Review all text — plain English labels, no technical jargon
- [ ] Test responsiveness at 390px (iPhone), 768px (iPad), 1440px (laptop)

---

*This document is the single source of truth for all UI decisions.
Any design question not answered here should be resolved by applying the principles in Section 1.*
