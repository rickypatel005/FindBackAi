# FindBack AI — UI/UX Document

**Version:** 1.0
**Status:** MVP / Hackathon Build

---

## 1. Design Principles

1. **Clarity over cleverness** — Lost vs. Found must always be visually unambiguous.
2. **Show AI, don't lecture about it** — surface AI suggestions and explanations; hide model/technical detail.
3. **Trust through explanation** — every match score is accompanied by *why*, never a bare number.
4. **Fast reporting** — minimize friction between "I lost something" and a submitted report.
5. **Calm empty/loading states** — no dead ends; every screen suggests a next action.

## 2. Core Screens

1. Landing page
2. Login
3. Register
4. User Dashboard
5. Report Lost
6. Report Found
7. My Lost Items
8. My Found Items
9. Potential Matches
10. Match Details
11. Notifications
12. Search / Browse
13. Admin Dashboard
14. Admin Report Management

## 3. Navigation Structure

```
Landing
 ├─ Login / Register
 └─ (after auth) Dashboard
      ├─ Report Lost
      ├─ Report Found
      ├─ My Lost Items
      ├─ My Found Items
      ├─ Potential Matches → Match Details
      ├─ Notifications
      ├─ Search / Browse
      └─ (Admin only) Admin Dashboard → Admin Report Management
```

Primary nav (persistent header/sidebar): Dashboard · Report Lost · Report Found · My Items · Matches · Notifications (with unread badge) · Search. Admin link only visible to `Admin` role.

## 4. Key User Flows

### 4.1 Report Lost/Found Flow
```
Dashboard → "Report Lost/Found" CTA
  → Upload images (1–3)
  → AI analyzes → suggested category/attributes appear (editable, clearly labeled "AI suggested")
  → User confirms/edits fields
  → Submit
  → Loading state ("Finding potential matches…")
  → Redirect to Potential Matches (or My Items if none found yet)
```

### 4.2 Match Review Flow
```
Notification / Dashboard card → Potential Matches list (top 3–5, score + short reason)
  → Tap a match → Match Details (side-by-side lost/found, full component scores, explanation list)
  → Action: mark as recovered / not a match / contact flow (if implemented)
```

### 4.3 Admin Moderation Flow
```
Admin Dashboard (stat cards) → Admin Report Management (table, filters)
  → Select report → View / Mark Duplicate / Remove / Resolve Match / Close
```

## 5. Screen-Level Notes

**Landing:** value proposition, "How it works" (3-step: report → AI matches → get notified), Login/Register CTAs.

**Login / Register:** minimal fields, inline validation, clear error states (wrong password, existing email).

**Dashboard:** summary cards (lost count, found count, potential matches, recovered items), recent reports list, notifications preview.

**Report Lost / Report Found:** identical layout, differentiated by a persistent color-coded header (e.g. Lost = one accent, Found = a distinct second accent) so users never confuse which flow they're in. Image dropzone first, then AI-suggested fields, then manual fields, then submit.

**My Lost Items / My Found Items:** card or table list with status badges (`SEARCHING`, `MATCH_FOUND`, etc.), filter by status.

**Potential Matches:** ranked list, each item shows thumbnail, score, and top 1–2 explanation chips (e.g. "Same category," "Similar appearance").

**Match Details:** two-column side-by-side comparison (lost report | found report), score breakdown (bar or chip per component), full explanation list, primary action button.

**Notifications:** chronological list, unread indicator, tap-through to Match Details.

**Search / Browse:** filter panel (category, color, brand, location, date, status) + results grid; natural-language search bar as a strong-addition feature.

**Admin Dashboard:** stat cards (total/lost/found/potential/recovered/pending) + shortcuts into Admin Report Management.

**Admin Report Management:** data table with per-row actions (view, mark duplicate, remove, resolve, close), bulk filters.

## 6. Component Inventory

- Image dropzone/uploader (1–3 images, preview thumbnails, remove action)
- AI-suggestion field (labeled badge distinguishing "AI suggested" from user-entered)
- Status badge (color-coded per lifecycle state)
- Score chip/bar (visual 0–100 representation)
- Explanation chip list
- Report card (used across dashboard, my items, search)
- Match card (thumbnail + score + reasons)
- Notification item (read/unread state)
- Filter panel (category, color, brand, location, date, status)
- Admin data table (sortable, filterable, row actions)
- Empty state (illustration/message + CTA, used for "no reports yet," "no matches yet," "no notifications")
- Loading state (skeleton cards for lists, spinner/progress copy for AI processing steps)

## 7. Forms & Validation

- Required fields marked clearly; submit disabled until required fields are valid.
- Image upload: reject wrong file type / oversized file inline, before submission.
- Inline error messages adjacent to the offending field, not just a top-of-form banner.
- AI-suggested fields visually distinct (e.g. subtle highlight + "AI suggested" label) until the user edits them, after which the label disappears.

## 8. Loading / Error / Empty States

| State | Treatment |
|---|---|
| AI processing after submit | Non-blocking loading state with short reassuring copy ("Analyzing your photo…", "Finding potential matches…") |
| No matches found | Empty state explaining the system will keep checking as new reports come in |
| No reports yet (My Items) | Empty state with a direct "Report Lost/Found" CTA |
| No notifications | Simple empty state, no CTA needed |
| API/network error | Inline retry affordance, plain-language message, no raw error codes shown to end users |
| Invalid session | Redirect to Login with a brief explanation |

## 9. Responsive Behavior

- Mobile-first layout; single-column forms and cards below tablet breakpoint.
- Sidebar nav collapses to a bottom nav or hamburger menu on mobile.
- Match Details' side-by-side comparison stacks vertically on narrow screens (lost report above found report).
- Admin data table becomes a stacked card list on mobile.

## 10. Accessibility

- Sufficient color contrast for status badges and score indicators; never rely on color alone (pair with icon/text label).
- All interactive elements keyboard-navigable and focus-visible.
- Form fields have associated labels (not placeholder-only).
- Images include alt text (e.g. derived from report title/category).
- Loading and error states announced via ARIA live regions where applicable.

## 11. Visual Language (Starting Point)

- **Typography:** one clean sans-serif family; clear hierarchy (page title / section header / body / caption).
- **Color:** neutral base palette + one accent for Lost, one distinct accent for Found, plus a semantic set for status (success/warning/neutral/danger) reused consistently for badges and score bands.
- **Spacing:** consistent spacing scale (e.g. 4/8/16/24/32px) across cards, forms, and lists for visual rhythm.
- **Components:** shadcn/ui as the base component library, themed to the above palette rather than left default, so the UI doesn't read as generic/templated.
