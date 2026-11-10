# Security Architecture & RBAC Permissions Matrix

BRIDGE enforces strict role-based access control (RBAC) across all API endpoints, background jobs, and frontend UI actions.

## Role Hierarchy & Personas

| Role | Primary Responsibility | Scope |
| :--- | :--- | :--- |
| **Administrator** (`administrator`) | Full tenant governance, user provisioning, rule/guideline approvals, impact simulation | Tenant-wide |
| **Brand Manager** (`brand_manager`) | Knowledge source authoring, rule catalog maintenance, GuidelineX adoption | Tenant-wide |
| **Reviewer** (`reviewer`) | Content review queue, finding overrides, review signal logging | Assigned queues & submissions |
| **Creator** (`creator`) | Content submission, pre-flight validation execution, viewing own findings | Own submissions only |
| **Auditor** (`auditor`) | Cryptographic audit chain verification, compliance reporting | Read-only across tenant |

---

## Detailed Permissions Matrix

| Capability / API Domain | Administrator | Brand Manager | Reviewer | Creator | Auditor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Authentication & Profile** |
| Login / Refresh Token / Logout | ✅ | ✅ | ✅ | ✅ | ✅ |
| View Own Profile (`/auth/me`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage Tenant Users (`/users`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Manage Tenant Settings (`/organisations`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Knowledge Center** |
| View Sources & Approved Rules | ✅ | ✅ | ✅ | ✅ | ✅ (Read) |
| Ingest Brand Documents / Sources | ✅ | ✅ | ❌ | ❌ | ❌ |
| Create Knowledge Records (Drafts) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Approve / Supersede Knowledge Versions | ✅ | ✅ | ❌ | ❌ | ❌ |
| Inspect Authoritative Passages | ✅ | ✅ | ✅ | ✅ | ✅ (Read) |
| **Validation Engine** |
| Submit Content for Validation | ✅ | ✅ | ✅ | ✅ | ❌ |
| View Own Validation Runs | ✅ | ✅ | ✅ | ✅ | ✅ (Read) |
| View All Tenant Validation Runs | ✅ | ✅ | ✅ | ❌ | ✅ (Read) |
| View Evidence Receipts & Citations | ✅ | ✅ | ✅ | ✅ | ✅ (Read) |
| Override Finding with Reason Code | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Brand Continuity Engine** |
| View Dependency Topology Graph | ✅ | ✅ | ✅ | ❌ | ✅ (Read) |
| Confirm Inferred Dependency Edges | ✅ | ✅ | ✅ | ❌ | ❌ |
| Run Version Change Impact Simulation | ✅ | ✅ | ❌ | ❌ | ❌ |
| Process Revalidation Queue Tasks | ✅ | ✅ | ✅ | ❌ | ❌ |
| **GuidelineX Intelligence** |
| View Review Friction Signals | ✅ | ✅ | ✅ | ❌ | ✅ (Read) |
| Log Review Signal Observation | ✅ | ✅ | ✅ | ❌ | ❌ |
| View Ambiguity Radar Analyses | ✅ | ✅ | ✅ | ❌ | ✅ (Read) |
| Approve & Adopt Normative Recommendation | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Audit Ledger & Verification** |
| View Immutable Audit Ledger | ✅ | ✅ | ✅ | ❌ | ✅ (Read) |
| Trigger Cryptographic SHA-256 Chain Verification | ✅ | ✅ | ✅ | ❌ | ✅ |
| Export Audit Compliance Receipt | ✅ | ✅ | ❌ | ❌ | ✅ |

---

## Security Invariants

1. **Cross-Tenant Isolation**:
   - Every request is authenticated with a JWT payload containing `org` (Organization UUID).
   - All database queries filter on `org_id == current_user.org_id`.
   - Accessing another tenant's resource ID returns HTTP 404 (or 403 Forbidden).

2. **Immutable Audit Ledger Protection**:
   - The PostgreSQL engine enforces a trigger blocking `UPDATE` and `DELETE` on `audit_events`.
   - Any attempt to modify a past record breaks the SHA-256 hash chain: `hash(event) = SHA256(canonical_payload + prev_hash)`.
   - Verification fails immediately with the exact broken event ID.

3. **Data Sanitization & Redaction**:
   - Passwords, JWT secrets, authorization headers, and API keys are scrubbed before logging.
   - Long document raw texts are never dumped to structured logging streams.

