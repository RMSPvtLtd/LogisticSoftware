# Security posture — Raaziq logistics platform

Written after the security audit of the air vertical (the sea vertical is a
stateless public container-tracking proxy and holds no customer data). This
documents what is enforced, what is deliberately not, and what has to be
configured outside the codebase.

It does **not** claim the system is secure against all attack. It states
what was tested and what remains outside the application's control.

---

## Trust model

The frontend is treated as fully untrusted and provides **zero** security
value. Every control below is enforced server-side and is expected to hold
against an attacker who:

- calls the API directly with a scripted client,
- knows or guesses any integer id,
- controls every byte of every request (headers, body, query string),
- has a valid account of *some* kind (customer, worker, or ops).

## Principals

| Principal | Auth | Scope |
|---|---|---|
| **Ops** | `POST /ops/login` → JWT (`typ: ops`, `tv: token_version`) | Full business surface. One flat role — see "Known limitations". |
| **Worker** | `POST /auth/login` → JWT (`typ: worker`) | Only shipments waiting to enter *their own Area's* stage. |
| **Customer** | `POST /customer/login` → JWT (`typ: customer`) | Read-only, and only their own records. |
| **Public** | none | `GET /tracking/{ref}` and `GET /meta/stages` only. |

Tokens are **not interchangeable**: every token carries a `typ` claim that
is checked on decode, so a customer token cannot open an ops route even
though both are signed with the same key.

## What is enforced

**Authentication**
- bcrypt password hashing (never plaintext, never a reversible cipher, never
  a bare/unsalted digest like MD5/SHA1/SHA256).
- JWT `alg` is pinned to `HS256` on decode — `alg: none` and algorithm
  confusion are rejected.
- Uniform failure messages across "no such user" / "wrong password" /
  "deactivated", so login is not an account-enumeration oracle.
- Deactivating an account (`is_active` / `portal_active`) takes effect on the
  **next request**, not at token expiry.
- An ops password change increments `token_version`, invalidating every
  token issued before it — not just the session that made the change.
- Failed-login throttling per (account + client IP): 10 attempts, then a
  15-minute lockout. The correct password is also refused while locked out,
  so lockout can't be used as a "right guess" oracle.

**Authorization**
- Every ops route requires an ops token at the router level, so a new route
  cannot forget it. A parametrised test asserts this across the whole route
  table and fails closed on any addition.
- Customer identity comes from the token, never from a request-supplied
  `customer_id`. Cross-customer access returns **404, not 403**, so an
  attacker cannot confirm that another customer's id exists.
- Worker area restriction is derived, not duplicated: a worker may only
  submit their own Area's stage, and `advance_stage` independently requires
  that stage to be the shipment's immediate next one.

**Data isolation**
- Supplier/shipper identity is omitted from every customer-facing schema
  (a customer learning the actual shipper could route around Raaziq).
- Internal cancellation reasons and internal notes never reach customer
  surfaces: `StatusEvent.is_internal` is filtered in one place, and
  cancellation deliberately writes two separate events (internal + a
  customer-safe note) rather than one that has to be redacted downstream.
- Documents are an ops-only surface; no customer endpoint serves them.

**Injection**
- All database access is SQLAlchemy Core/ORM with bound parameters. There is
  no raw SQL, no string-interpolated SQL, and no dynamic table/column/ORDER
  BY built from user input.
- No `subprocess`/`eval`/`exec`/shell anywhere — command injection has no
  surface.
- No filesystem access anywhere — uploads are stored as `bytea` in Postgres,
  so path traversal and arbitrary file read have no surface.
- Untrusted values are escaped before entering reportlab `Paragraph`, which
  parses a mini-HTML dialect (see "PDF" below).
- React auto-escapes all rendered values; there is no `dangerouslySetInnerHTML`.

**Financial integrity**
- Totals are always recomputed server-side from stored line items. A
  client-supplied `total` is rejected outright (`extra="forbid"`).
- Money fields are bounded to `NUMERIC(12,2)`: non-negative, ≤ 9,999,999,999.99,
  ≤ 2 decimal places. NaN/Infinity are rejected.
- A discount that would drive the total negative is refused — a per-field
  check cannot catch this, so the guard lives in `recalculate_totals` where
  the arithmetic happens and therefore covers every caller.
- Issued invoices are immutable snapshots; editing the quote, customer, or
  shipment afterward provably does not alter them.

**Uploads**
- Type is decided by **actual magic bytes**, not the declared MIME type or
  the extension. PE/ELF/PHP/HTML payloads renamed `.pdf` are rejected.
- 4 MB cap (under Vercel's 4.5 MB hard body limit).
- Filenames are sanitised to an allowlist and can never contain path
  separators, quotes, or control characters.

**Transport / responses**
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, a restrictive `Content-Security-Policy`
  (`default-src 'none'; frame-ancestors 'none'`), `Permissions-Policy`, and
  `Cache-Control: no-store` on every response. HSTS in production only.
- CORS allows explicit origins only — never `*`, never a reflected `Origin`.
- Any unhandled exception becomes an opaque 500 with a random `error_id`;
  tracebacks, SQL text, and file paths never reach a client. The full detail
  is logged server-side against that id.
- `/docs`, `/redoc` and `/openapi.json` are disabled in production.

**Startup**
- The app **refuses to boot** in production with a development JWT secret, a
  signing key under 32 characters, the default ops password, or a CORS
  wildcard. Fails closed rather than serving traffic insecurely.

**CSRF** — not applicable by construction: authentication is a bearer token
in an `Authorization` header, never a cookie, so a cross-site form post
carries no credentials. This must be re-evaluated if cookie auth is ever
introduced.

---

## Production checklist

Before deploying, confirm each of these:

- [ ] `ENVIRONMENT=production` (turns on the startup checks below)
- [ ] `JWT_SECRET_KEY` set to a fresh random value ≥32 chars
      (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- [ ] `OPS_ADMIN_PASSWORD` set to a real value, **and** changed via
      `POST /ops/change-password` after first login
- [ ] `CORS_ORIGINS` set to the exact frontend origin(s), no `*`
- [ ] `DATABASE_URL` uses a least-privilege role, not a superuser
- [ ] Database is not publicly reachable (IP allowlist / private networking)
- [ ] TLS enforced end-to-end; no plaintext HTTP path to the API
- [ ] Demo/seed accounts removed or credentials rotated (the seed script
      creates demo workers and customer portal logins with shared passwords)
- [ ] Automated database backups configured, encrypted, and **restore-tested**
- [ ] `raaziq.security` logger routed to a retained, access-controlled sink

---

## Known limitations (accepted, not oversights)

1. **Rate limiting is per-process and in-memory.** On Vercel serverless each
   instance keeps its own counters, so the effective limit across many cold
   starts is higher than configured. It stops the cheap single-client case at
   zero infrastructure cost. *Upgrade path: a shared Redis/Postgres counter.*

2. **Ops is a single flat role.** Any ops user can cancel invoices, change
   billing entities and create worker accounts. There is no maker/checker
   split or step-up authentication for high-value actions.
   *Upgrade path: an ops role/permission column plus per-action checks.*

3. **Tokens are stored in `localStorage`.** This is XSS-exposed. It is
   mitigated by there being no HTML injection sink in the app (React
   auto-escaping, no `dangerouslySetInnerHTML`, strict CSP), but a future XSS
   would yield a token. *Upgrade path: `HttpOnly` `Secure` `SameSite=Strict`
   cookies plus CSRF tokens — a deliberate trade, since that adds the CSRF
   surface this design currently avoids entirely.*

4. **No password-reset or MFA flow.** Ops resets are manual (an ops user
   changes their own password; a locked-out account needs direct DB
   intervention). No TOTP/WebAuthn.

5. **JWTs carry no `aud`/`iss` claims** and, for workers/customers, cannot be
   revoked before expiry other than by deactivating the account. Ops tokens
   *can* be revoked via `token_version`.

6. **Uploaded PDFs are not malware-scanned.** They are validated as
   structurally PDF and never executed server-side, but a malicious PDF could
   still target a viewer on an ops user's machine.
   *Upgrade path: an AV/CDR scan step on upload.*

7. **No automated backups are configured by this codebase.** Backup
   frequency, retention, encryption and restore testing are entirely a
   database/infrastructure concern (Neon PITR or equivalent) and must be set
   up and verified outside the application.

8. **Business-logic race conditions rely on database constraints**, which is
   the correct layer — but the row-level locks (`SELECT … FOR UPDATE`) only
   engage on PostgreSQL. The test suite runs on SQLite, so the constraints
   are what the tests actually prove; the locks are exercised only in
   production.

---

## Out of scope for this audit

- Infrastructure: Vercel account security, DNS, TLS certificate management,
  WAF/DDoS, database network exposure, OS patching.
- The SAPT third-party tracking provider's own security.
- Physical/operational security and staff device security.
- Denial of service — no load shedding or request-cost limiting beyond the
  login throttle and the upload size cap.
