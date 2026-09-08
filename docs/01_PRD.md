# FindBack AI — Product Requirements Document (PRD)

**Version:** 1.1 (Refined)
**Status:** MVP / Hackathon Build
**Owner:** Ricky

---

## 1. Executive Summary

FindBack AI is a web-based lost-and-found platform that uses multimodal AI (image + text + metadata) to automatically identify likely matches between lost-item reports and found-item reports, reducing the manual effort typically required to reunite people with their belongings.

## 2. Problem Statement

Traditional lost-and-found systems rely on manual searching, exact keyword matching, or staff intervention to connect lost and found reports. This fails in practice because:

- Users describe the same object in inconsistent language ("blue backpack" vs. "navy rucksack").
- Visually similar items are hard to discover through text search alone.
- There is no ranked, explainable way to surface the most likely match.
- Staff-mediated matching does not scale across item categories or locations.

FindBack AI addresses this by automatically retrieving, scoring, and explaining candidate matches using a combination of image similarity, text similarity, and structured metadata.

## 3. Product Vision

A generic, multi-category lost-and-found platform (electronics, bags, wallets, documents, clothing, keys, and more) where reporting an item is fast, AI assists with categorization, and the system proactively surfaces and explains potential matches instead of requiring users to search manually.

## 4. Target Users

| User | Description | Core Need |
|---|---|---|
| Regular User | Someone who lost or found an item | Report quickly, get notified of a plausible match, understand why it matched |
| Administrator | Platform moderator | Review reports, resolve duplicates, remove abuse, monitor platform health |

## 5. Goals

### Primary Goals
1. Let users report lost and found items easily (images + structured metadata).
2. Automatically interpret uploaded item images (category, color, brand, features).
3. Convert free-text descriptions into semantic (embedding) representations.
4. Retrieve relevant lost/found candidates via vector + metadata search.
5. Produce a single, explainable multimodal match score per candidate pair.
6. Notify users in-app when a strong potential match appears.
7. Provide basic administrative moderation and platform statistics.

### Non-Goals (Out of Scope for MVP)
- GPS / live location tracking
- Maps and route navigation
- Private user-to-user chat
- Payments or rewards
- Native mobile application
- Blockchain-based verification
- Custom deep-learning model training from scratch
- General-purpose chatbot functionality

## 6. Supported Item Categories

Platform is category-agnostic by design. Initial reference categories: Electronics, Bags, Wallets, Documents, Clothing, Keys, Books, Accessories, Bottles, Watches, Earbuds/Headphones, Other. No category is hardcoded into the architecture.

## 7. Core User Journeys

### 7.1 Lost Item Journey
1. User signs in.
2. Selects **Report Lost Item**.
3. Uploads 1–3 images.
4. Enters title, category, color, brand, description, location, date, approximate time.
5. AI analyzes image(s) and suggests category/attributes.
6. User reviews and corrects AI suggestions if needed.
7. System generates image and text embeddings.
8. System searches active **found** reports.
9. Matching engine scores candidates.
10. System shows top 3–5 potential matches with explanations.
11. User opens a match-detail page.
12. Strong matches trigger an in-app notification.

### 7.2 Found Item Journey
Identical flow with report type `FOUND`, matched against active **lost** reports.

## 8. User Stories

- As a user, I want to report a lost item with photos so the system can find candidate matches automatically.
- As a user, I want AI to pre-fill category/attributes from my photo so reporting is faster.
- As a user, I want to see *why* a match was suggested, not just a score, so I can trust the result.
- As a user, I want to be notified when a strong match appears without checking manually.
- As a user, I want to filter/search reports manually as a fallback to automatic matching.
- As an admin, I want to see platform-wide stats and flagged duplicates so I can moderate efficiently.
- As an admin, I want to remove inappropriate reports and resolve confirmed matches.

## 9. Functional Scope (Summary)

Authentication · Lost/Found report creation · AI image analysis · Text embedding · Image embedding · Semantic + metadata search · Multimodal match scoring · Explainable match reasons · In-app notifications · Dashboard · Report status lifecycle · Search/filters · Duplicate detection · Admin dashboard · Report quality suggestions · Privacy controls.

*(Full functional requirements are defined in the companion SRS document.)*

## 10. MVP Scope

### Must Have
Authentication, lost/found reports, image upload, AI image analysis, text processing, image + text embeddings, metadata matching, multimodal score, ranked matches, explanations, match details, notifications, dashboard, report statuses.

### Strong Additions (post-core)
Semantic location matching, natural-language search, duplicate detection, report-quality suggestions, admin dashboard, advanced filtering.

### Nice to Have
Email notifications, multilingual descriptions, match feedback loop, reputation score, AI-generated summaries, advanced analytics.

## 11. Success Metrics

**Product**
- % of reports successfully submitted
- % of reports with usable images
- Match click-through rate
- % of users opening match details
- Number of confirmed recoveries (test/demo data)

**AI**
- Category accuracy on validation images
- Top-k retrieval accuracy
- Precision of high-confidence matches
- False-positive rate at the selected threshold

A small validation dataset with intentionally matched and non-matched pairs will be maintained for evaluation.

## 12. Assumptions

- Pretrained CLIP/OpenCLIP and Sentence Transformers are sufficient for MVP accuracy; no custom model training is required.
- Users will upload reasonably clear, single-item-focused photos.
- Location and time signals can be approximated via text/aliases rather than GPS for MVP.
- Supabase (Postgres + pgvector + Auth + Storage) is available and sufficient for the target scale.

## 13. Risks

| Risk | Mitigation |
|---|---|
| Similar-looking but different objects | Combine image similarity with text + metadata, never image-only |
| Incorrect AI category prediction | Allow user correction; always include an "Other" category |
| False high-confidence matches | Calibrate thresholds against known positive/negative validation pairs |
| Weak location semantics without GPS | Use text similarity + normalized location aliases |
| Small dataset for evaluation | Rely on pretrained models; focus evaluation on retrieval quality, not training |

## 14. MVP Acceptance Criteria

- A new user can register and log in.
- A user can create LOST and FOUND reports with images.
- Images upload and store correctly.
- AI suggests a generic item category without custom training.
- Image and text embeddings are generated and stored.
- Lost reports retrieve found candidates and vice versa.
- A final weighted match score is generated and ranked.
- Match reasons are displayed alongside scores.
- A qualifying match generates an in-app notification.
- Users can view and manage their own reports.
- Admins can review, close, or remove reports.
