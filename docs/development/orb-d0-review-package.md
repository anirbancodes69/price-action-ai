# ORB D0 Acceptance Package

| Field | Value |
|---|---|
| Version | 1.6.0 (2026-11-25, **D0 formally ACCEPTED WITH CAVEATS by the owner (DEC-035)**; the review remains NON-INDEPENDENT; D1-D6 not authorised) |
| Status | **D0 is ACCEPTED WITH CAVEATS (owner decision of 2026-11-25, [DEC-035](../../DECISIONS.md)).** The D0 review is and remains a **NON-INDEPENDENT owner self-review** (DEC-033 / DR-10); it is not an independent review. The off-device requirement is **WAIVED BY OWNER (DEC-032 / DR-9); not completed, not equivalent to an off-device backup.** Acceptance authorises only its own recording: **D1-D6, P0-1/P0-1b, backtests, ORB implementation, service restarts, database changes and Git operations are NOT authorised.** DR-7 and DR-7a still apply to D1-D6 (an independent human reviewer must be appointed first). Caveats: section 3.4 |
| Related | [Remediation page](orb-data-remediation.md) (decisions DR-1 to DR-8, D0 specification, §2.5-§2.7 execution records) · [DEC-028..031](../../DECISIONS.md) |
| Evidence location | `~/priceaction-backups/d0-20261123/evidence/` (files 00 to 23, scripts, the `SHA256SUMS*` files; outside the repository, not committed). The same files were produced in the working scratchpad |

Nothing in this package changes a development database, B0, `ORB-MG-02`, PAQS, a ruleset, a strategy or a decision status. No service was restarted.

## 1. Acceptance matrix

Verification classes: **[A]** verified by automated checks (commands and outputs are in the evidence files); **[O]** needs an owner action that only the owner can perform; **[R]** awaiting independent human review; **[F]** awaiting the owner's formal acceptance. A row can carry more than one class.

| # | Criterion | Status | Class | Evidence and basis |
|---|---|---|---|---|
| 1 | Baseline manifest complete (53 public tables, `candles` in 10,830 chunks, structure manifest, schema dump) | **Verified** | A, then R, F | Files 03, 05; the manifest was identical before and after the dump |
| 2 | Restore equals baseline | **Verified** (data manifest byte-identical; schema dump identical after removing PostgreSQL's per-run `\restrict` token lines; structure manifest identical after two documented representation effects: dropped-column ordinal numbers in two tables and the explicit-versus-default ACL of `migrations`) | A, then R, F | Files 07, 08. The reviewer should confirm that the structure-manifest explanation is acceptable |
| 3a | Two encrypted copies (A and B) exist in separate directories, outside the repository, and decrypt to the recorded plaintext hashes | **Verified** (ciphertext hashes of copy A, copy B and the Desktop duplicate of B re-checked on 2026-11-23: match; decryption check done at creation) | A | Files 06, 21; `verify_offdevice.sh` re-run without a key |
| 3b | One encrypted copy on **separate storage** (off-device) | **DEFERRED: WAIVED BY OWNER** (owner-approved same-device backup exception; confirmed in R14, 2026-11-25) (documented risk exception, DEC-032 / DR-9). **Not completed; not equivalent to an off-device backup.** Residual risk accepted by the owner: a physical failure, theft, loss or destruction of this Mac could destroy both backup copies | Owner decision | Remediation §2.8 |
| 3c | The decryption key stored in a password manager and shown recoverable | **VERIFIED through NON-INDEPENDENT owner attestation and a manual decryption verification (owner-reported, 2026-11-25).** Apple Passwords entry `PriceAction AI — D0 Backup Key`. **Caveat:** the official `verify_key_from_clipboard.sh` did **NOT pass**: the password-manager copy carries one trailing space, so the script failed at first. A separate manual decryption (trailing space removed in shell memory, documented parameters) decrypted both files to the recorded plaintext hashes (`priceaction.dump: OK`, `globals.sql: OK`). The script was not modified. Recovery from this entry therefore needs the trailing space removed. The terminal output is not stored in the evidence folder | O (owner attestation) | Section 2; evidence file 23; [R5](#34-owner-self-review-record-recorded-2026-11-25) |
| 3d | The local key file removed only after 3c is confirmed | **VERIFIED** (owner-reported removal with the documented command; owner confirmed the file is gone and the key directory empty; preparer check, existence only: `~/priceaction-backups/keys/d0-20261123.key` absent, directory empty, modified 2026-11-25 03:05 +05:30). The key was never read by the preparer. Overwrite by `rm -P` is not guaranteed on an SSD; FileVault is On | O (owner attestation) | Section 2; evidence file 23 |
| 3e | Same-device copies verified; residual risk accepted in writing | **VERIFIED** (NON-INDEPENDENT owner attestation and evidence; confirmed by the owner 2026-11-25). Copy A, copy B and the owner's Desktop duplicate of copy B (`~/Desktop/D0-Backup-Copy/copy-b/`, byte-identical to copy B) match the recorded ciphertext SHA-256; all on the same device; the Desktop folder may sync to iCloud as ciphertext (unverified, not relied on). Residual risk: all backup copies are on this Mac | A; owner decision | Evidence file 21; remediation §2.8 |
| 4 | Engine integration tests cannot write to the development database | **Verified** (guard refuses every unapproved target; role `app_test` rejected by the development database; 52 tests passed against `priceaction_test`). The owner accepted this on the evidence | A; owner accepted; R | Files 10 to 14 |
| 5 | Laravel/PHPUnit tests cannot write to the development database | **Verified** (bootstrap guard exits 2 with no test run for every unapproved target; role `app_test_schema` rejected by the development database with `permission denied for database`; `make test-backend`: 217 tests, 2,972 assertions, OK, run on the final code). CI environments pass the guards (CI itself not executed) | A, then R, F | Files 15 to 20 |
| 6 | Development database integrity: no development data changed by any D0 step | **Verified** (data manifest byte-identical to the pre-D0 baseline, re-checked on 2026-11-23 after all work; structure manifest differs only by the two new cluster roles `app_test` and `app_test_schema`) | A, then R, F | Files 09, 14, 19; re-run |
| 7 | Secret scan: neither test-role password appears in any repository file other than the gitignored `.env`, in the evidence files, or in the backup folder; no temporary password file left | **Verified** (0 files) | A | Scan completed 2026-11-23 |
| 8 | Evidence integrity: all evidence files verify against their recorded sha256 sums | **Verified** (0 non-OK lines in each of the three sum files, 2026-11-23) | A | `SHA256SUMS`, `.remaining-gates`, `.remaining-gates-2` |
| 9 | B0, `ORB-MG-02`, PAQS, rulesets, strategies unchanged; P0-1 artifacts unchanged (hashes) | **Verified** | A | `git diff` shows no change under the engine app, rulesets, backend app or database folders; P0-1 hashes match |
| 10 | Test-role provisioning documented and separate from the historical `globals.sql` baseline | **Verified** (documented and scripted: `scripts/provision-test-db.sh`, idempotent) | A, then R | Remediation §2.7 |
| 11 | Human review of the D0 evidence | **DEFERRED: independence waived for D0 only (DEC-033 / DR-10, 2026-11-25).** The NON-INDEPENDENT owner self-review was executed and recorded (section 3.4): R1-R4 and R6-R12 PASS (owner-run), R5 PASS by attestation, R13 approved, R14 confirmed. Residual risk accepted: no separate human reviewer verified the preparation, the evidence or the owner's decisions. DR-7 and DR-7a still apply to D1-D6 | Owner self-review | Section 3; remediation §2.9 |
| 12 | Application services restarted only after acceptance | **DEFERRED by design:** D0 is now accepted (2026-11-25); a restart still needs a separate owner authorisation, which has **not** been given (backend, queue, scheduler, engine stopped since 2026-11-23 14:29 UTC) | F | |
| 13 | Formal owner acceptance of D0 | **ACCEPTED WITH CAVEATS (2026-11-25, [DEC-035](../../DECISIONS.md)).** Owner decision: "I formally accept D0 with the caveats listed." The review stays NON-INDEPENDENT. D1-D6 are not authorised by it | F | Section 3.4; section 6 |

Open items by class. **Owner actions [O]:** none. **Review:** complete (NON-INDEPENDENT). **Formal acceptance [F]:** row 13 done (2026-11-25). Row 12 (service restart) remains deferred until the owner separately authorises it.

## 2. Owner instructions: password-manager key and local key removal (exact steps)

**Owner-only. The AI does not perform password-manager actions, does not read the key file, and claims no step done until you confirm it.** The off-device copy is waived (DEC-032). Never put the key in a chat (with any AI), in Git, in any repository file, in a shell command argument, in shell history or in an ordinary evidence file. Do not delete or overwrite any backup copy at any point.

**What exists (all on this Mac, none off-device).** Copy A `~/priceaction-backups/d0-20261123/copy-a/`; copy B `~/priceaction-backups/d0-20261123/copy-b/`; the Desktop duplicate of B `~/Desktop/D0-Backup-Copy/copy-b/`. Recorded ciphertext checksums: copy A dump `d26ceaed…193b1c`, globals `2f607d20…286990`; copy B (and the duplicate) dump `2326fab1…8637c2`, globals `7263e3be…f7ed12` (full values in `evidence/06_encrypt.txt` and `evidence/SHA256SUMS`). Plaintext hashes the decryption must reproduce: dump `b9f0b4b7…b70176`, globals `3e3a6fb4…2bad1a` (`evidence/04_dump.txt`). The key file is `~/priceaction-backups/keys/d0-20261123.key` (mode 0600).

**Why the existing script is not used directly.** `verify_offdevice.sh` needs a key **file** and reads it twice (once per backup file), so it cannot take a pipe or a process substitution. Using it means a plaintext key file exists for a moment. Two safer methods are provided; **choose one and confirm the choice before you use it** (the AI does not choose for you).

**Step 1: open the password manager.**

**Step 2: create or update a secure entry named exactly `PriceAction AI — D0 Backup Key`.** Suggested note: "decrypts the D0 backup copies; AES-256-CBC, PBKDF2 600000 iterations; copies in ~/priceaction-backups/d0-20261123 and ~/Desktop/D0-Backup-Copy".

**Step 3: put the key into the entry without displaying it.** Either (a) attach the file `~/priceaction-backups/keys/d0-20261123.key` to the entry using the password manager's attachment feature (drag the file in; nothing touches the clipboard), or (b) `pbcopy < ~/priceaction-backups/keys/d0-20261123.key`, paste into the entry's password field, then clear the clipboard with `pbcopy < /dev/null`. (Option b puts the key on the clipboard briefly; Universal Clipboard to other devices or a clipboard-history utility could keep it, so prefer (a), or turn those off first.)

**Step 4: confirm that the entry is saved** (close and reopen it, or check it on a second device), without revealing the value.

**Step 5: retrieve the key from the password manager** (copy button; do not display it) and verify decryption against the original backup hashes, using **one** of these methods:

- **Method A (preferred; no key file at all).** The clipboard helper `~/priceaction-backups/d0-20261123/evidence/verify_key_from_clipboard.sh` reads the key once from the clipboard into shell memory, passes it to `openssl` on stdin through a shell builtin (never an argument, environment variable or file), and clears the clipboard when it ends. It was tested by the AI **only with dummy keys** (right key: OK; wrong key: mismatch, exit 1; empty clipboard: exit 1; wrong directory: refused). Read the 30-line script before first use. Then, with the key on the clipboard:
  `~/priceaction-backups/d0-20261123/evidence/verify_key_from_clipboard.sh ~/priceaction-backups/d0-20261123/copy-b`
  Expected output: `ciphertext hashes match a recorded copy`, `priceaction.dump: decrypts to the recorded plaintext hash (OK)`, `globals.sql: decrypts to the recorded plaintext hash (OK)`, `RESULT: the key on the clipboard is the correct D0 backup key`; exit status 0. Anything else: stop; remove nothing.
- **Method B (a temporary file, memory only; needs your explicit confirmation before use).** The existing script needs a key file. The safest temporary-file procedure is a 1 MB RAM disk, which is memory only and vanishes when detached (tested by the AI with a dummy value):
  `DEV=$(hdiutil attach -nomount ram://2048 | awk 'NR==1{print $1}'); diskutil erasevolume HFS+ D0KEY "$DEV"`
  `( umask 077; pbpaste > /Volumes/D0KEY/key ); pbcopy < /dev/null`
  `~/priceaction-backups/d0-20261123/evidence/verify_offdevice.sh ~/priceaction-backups/d0-20261123/copy-b /Volumes/D0KEY/key`
  `hdiutil detach "$DEV"`
  Expected: `ciphertext hashes match recorded copy: B` and two `decrypts to the recorded plaintext hash (OK)` lines. If the key came from an attached file, copy the attachment onto the RAM disk instead of using `pbpaste`.
- **Not recommended:** writing the key to an ordinary file (even `$HOME/.d0-key-check`) and deleting it afterwards; it touches the disk (FileVault is On, but overwriting with `rm -P` is not guaranteed on an SSD).

**Step 6: only after Step 5 passed, remove the local key file:** `rm -P ~/priceaction-backups/keys/d0-20261123.key`

**Step 7: confirm the local key file no longer exists:** `[ ! -e ~/priceaction-backups/keys/d0-20261123.key ] && echo "key file removed"; ls ~/priceaction-backups/keys`  (the listing should be empty).

**Step 8: confirm the encrypted backups are unchanged:** `for d in ~/priceaction-backups/d0-20261123/copy-a ~/priceaction-backups/d0-20261123/copy-b ~/Desktop/D0-Backup-Copy/copy-b; do ~/priceaction-backups/d0-20261123/evidence/verify_offdevice.sh "$d" | head -1; done` (expect `recorded copy: A`, `B`, `B`), and `cd ~/priceaction-backups/d0-20261123/copy-a && shasum -a 256 -c SHA256SUMS` (and the same in `copy-b`).

If the password manager is ever lost, the backups become unreadable; that is part of the accepted risk.

**What to report back (owner-confirmed only):** "entry `PriceAction AI — D0 Backup Key` saved and re-opened"; "decryption verified from the password-manager copy with method A (or B)"; "local key file removed (step 7 output)"; "step 8 checks match". None of these is claimed until you say so.

**Residual risk (accepted by the owner, DEC-032).** A physical failure, theft, loss or destruction of this Mac could destroy both backup copies. This exception is not equivalent to an off-device backup. The Desktop folder may sync to iCloud as ciphertext (setting is on; upload not verified; not relied on).

### 2.1 Recovery caveat: trailing space, and a proposed correction (not yet adopted)

**What happened (owner-reported).** The password-manager copy of the key carries one trailing space. The official `verify_key_from_clipboard.sh` reads the first clipboard line as is, so it failed at first. A manual decryption that trimmed the trailing space in shell memory decrypted both backups to the recorded plaintext hashes. **The official script did not pass.** The encryption key, the backups and the script are unchanged (the script's hash still matches `SHA256SUMS.final-review`).

**Consequences.** (1) Recovery from the stored entry works only if trailing whitespace is removed before use. (2) Anyone restoring from the backups with the entry exactly as copied would see a failed decryption that looks like a wrong key. (3) The documented procedure is therefore incomplete until the trim is documented.

**Proposed correction (a proposal for the owner; nothing has been changed).**
1. **Procedure text now:** add one line to the recovery steps: "the stored key may end with one trailing space; remove trailing whitespace (spaces, tabs, CR) before use; never other characters".
2. **A new, separately versioned script** (for example `verify_key_from_clipboard_v2.sh`) that trims only trailing whitespace from the single clipboard line in memory and is otherwise identical. The original script stays preserved with its recorded hash and is not edited.
3. **Tests before adoption, dummy keys only** (never the real key): key with no trailing space; one trailing space; trailing tab; CRLF; two lines on the clipboard (first line used); empty clipboard (must fail); a wrong key (must fail); a key with a leading space (must **not** be silently accepted); confirm the clipboard is cleared and the key never appears in arguments, the environment or any file. Record the outputs as evidence.
4. **Optional and separate:** clean the trailing space from the password-manager entry. It needs an owner decision; a change risks replacing the only copy of the key, so do it only after a verified, recoverable copy exists, and verify recovery again afterwards.
5. **Do not** change the encryption key, the encrypted backups or the recorded hashes.

Adopting any of this is the owner's decision (task T-I165).

## 3. Independent reviewer checklist (DR-7a: OPEN)

**Who may review.** A human who did not prepare the D0 work or the data and is not the AI session that produced the evidence, with enough PostgreSQL and backup-and-restore competence to judge it. The owner has not named a reviewer; none is assumed, and this checklist names nobody.

For each item: record Pass, Fail or Query, with a note. The evidence files are in the folder named at the top.

| # | Area | What to check | Where | Expected |
|---|---|---|---|---|
| R1 | Evidence integrity | `shasum -a 256 -c` on each of the three `SHA256SUMS*` files | evidence folder | No failures |
| R2 | Backup restoration | The pre-dump manifest, the post-dump manifest and the manifest of the scratch restore are the same file; open `07_restore.txt` for the restore log (separate PostgreSQL 17.12 instance, no errors) | files 03, 05, 07, 08 | Identical data manifests (53 tables; `candles` in 10,830 chunks); restore log without errors |
| R3 | Restore: schema and structure | The schema-only dumps are identical once the per-run `\restrict`/`\unrestrict` lines are removed; the structure manifests differ only in two documented ways | files 03, 05, 08; `00_summary.txt`; remediation §2.5 | Two benign differences only (ordinal numbers after dropped columns; explicit versus default owner ACL on `migrations`). Decide whether this satisfies the criterion |
| R4 | Backup contents and handling | Two encrypted copies exist in separate directories (plus the owner's Desktop duplicate of B, byte-identical, evidence file 21); plaintext was deleted; the decrypt-and-hash check at creation matched; both copies' ciphertext hashes still match today; the dump was taken with all writers stopped (see `02_quiesce.txt`: only the checking session connected, write counters unchanged over 20 s) | files 02, 04, 06 | As described |
| R5 | Waiver, residual risk and key handling | That the owner's written waiver (DEC-032 / DR-9) and the residual-risk statement are recorded and not presented as an off-device backup; the owner's report that the key is in the password manager and recovery was verified (step 2), and that the local key file was removed afterwards; that the key is not stored beside the copies | DEC-032; remediation §2.8; owner confirmation | Waiver recorded; key steps confirmed. **Key steps currently NOT DONE** |
| R6 | Development database integrity | Re-run the data manifest on the development database (read-only) and compare it with `03_manifest_dev_pre.txt`; confirm the structure manifest differs only by the two new roles (`19_structure_dev_final2.txt`) | files 03, 09, 14, 19 | Byte-identical data manifest |
| R7 | Test database isolation: engine | Read `db_guard.py` and its 36 tests; confirm the refusal cases in `11_guard_behaviour.txt`; confirm that the development database refuses `app_test` (`12_test_role.txt`) | files 11, 12, 13 | Every unapproved case refused before any connection |
| R8 | Test database isolation: Laravel | Read `backend/tests/bootstrap.php`, `Support/DatabaseGuard.php` and `TestCase.php` (`setUpTraits` runs before any trait); confirm exit 2 and no test run for every unapproved target (`17_laravel_guard.txt`), the refused development connection (`16_laravel_role.txt`) and the 217-test run (`18_laravel_tests_on_test_db.txt`) | files 15 to 20 | As described |
| R9 | Role privileges | Run the catalog queries in `12_test_role.txt` and `16_laravel_role.txt` yourself: neither role has `CONNECT` or any table privilege on `priceaction` | files 12, 16 | 0 of 53 development tables; connect refused |
| R10 | Secrets | The two test-role passwords exist only in `.env` (gitignored, mode 0600); search the repository, the evidence folder and the backup folder for them | repository; evidence | No match anywhere else |
| R11 | Provisioning | Read `scripts/provision-test-db.sh` and remediation §2.7: separate from the historical `globals.sql`; idempotent; passwords on stdin only; touches only roles and the named test database | script; §2.7 | As described |
| R12 | Scope | `git diff` shows no change to B0, `ORB-MG-02`, PAQS, rulesets, strategies or the engine and backend application code; the P0-1 artifacts hash as recorded | repository | Only test code, the Makefile, `phpunit.xml`, the provisioning script and documents changed |
| R13 | Historical data provenance and limitations (review, not part of D0 acceptance) | Read the limitations in section 4 and decide whether D1-D6 as planned address them | section 4; remediation §5 | Understood and accepted as the scope of D1-D6 |
| R14 | D0 acceptance criteria | Walk the matrix in section 1 against the evidence | section 1 | Every row either Verified or explicitly deferred |

The reviewer reports to the owner; the reviewer's name and date go in the register entry DR-7a when the owner supplies them.

### 3.1 Self-review run sheet: read-only commands the owner runs

**Runner (recommended).** `~/priceaction-backups/d0-20261123/evidence/owner_review.sh` executes the automatable parts of R1-R14 and records, for every item, the purpose, the command, whether it can write, the output, the exit code and a verdict. Run it yourself as `RUN_BY=owner ~/priceaction-backups/d0-20261123/evidence/owner_review.sh`; it writes `owner-review-<utc>-owner.log` beside the evidence. Setting `RUN_BY=ai-assisted` labels the log as **not** owner-executed. The development database is only read (read-only sessions); items R7 and R8b write only to the dedicated test database `priceaction_test`; no key is read or needed; R5, R13 and R14 are manual and always show PENDING. It takes a few minutes (the Laravel suite and the secrets search are the slow parts). `SKIP_R8_FULL=1` skips the Laravel suite.

For the **proposed** NON-INDEPENDENT owner self-review (DR-10; not approved). Run from `~/Desktop/priceaction-ai` unless stated. `E` is `~/priceaction-backups/d0-20261123/evidence`. All commands are read-only with respect to the development database; none prints a key or a password. Each was run by the AI on 2026-11-24 with the result shown; the owner should run them personally and compare.

| Item | Command | Expected |
|---|---|---|
| R1 evidence integrity | `cd $E && for f in SHA256SUMS SHA256SUMS.remaining-gates SHA256SUMS.remaining-gates-2 SHA256SUMS.backup-exception; do echo "$f: $(shasum -a 256 -c $f 2>&1 \| grep -vc ': OK') failures"; done` | 0 failures for each of the four |
| R4 copies | `for d in ~/priceaction-backups/d0-20261123/copy-a ~/priceaction-backups/d0-20261123/copy-b ~/Desktop/D0-Backup-Copy/copy-b; do $E/verify_offdevice.sh "$d" \| head -1; done` | `match recorded copy: A`, then `B`, then `B` |
| R6 development integrity | `docker compose exec -T -e PGOPTIONS='-c default_transaction_read_only=on' postgres psql -X -U postgres -d priceaction -f - < $E/manifest.sql \| cmp - $E/03_manifest_dev_pre.txt && echo IDENTICAL` | `IDENTICAL` |
| R9 role privileges | `docker compose exec -T -e PGOPTIONS='-c default_transaction_read_only=on' postgres psql -X -U postgres -d priceaction -At -c "select r.rolname\|\|': connect='\|\|has_database_privilege(r.rolname,'priceaction','CONNECT')\|\|', tables with any privilege='\|\|(select count(*) from pg_tables t where t.schemaname='public' and has_table_privilege(r.rolname,format('%I.%I',t.schemaname,t.tablename),'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')) from pg_roles r where r.rolname in ('app_test','app_test_schema') order by 1"` | `app_test: connect=false, tables with any privilege=0` and the same for `app_test_schema` |
| R7 engine tests | `$E/ct.sh tests/integration tests/test_db_guard.py -rA \| grep -E "^(PASSED\|FAILED\|ERROR\|SKIPPED)" \| sed -E 's/^(PASSED\|FAILED\|ERROR\|SKIPPED) ([^:]+)::.*/\1 \2/' \| sort \| uniq -c` (writes only to `priceaction_test`) | 4 + 8 + 4 + 36 PASSED, nothing else |
| R8 Laravel tests | `make test-backend` (provisions the test roles, then runs phpunit against `priceaction_test`; takes a few minutes) | `OK (217 tests, 2972 assertions)` |
| R8 Laravel guard | `RUNENV="-e DB_CONNECTION=pgsql -e DB_DATABASE=priceaction -e DB_USERNAME=app_backend -e DB_HOST=postgres -e DB_PASSWORD=x" $E/lg.sh; echo "exit=$?"` | `REFUSING TO RUN THE TEST SUITE: database 'priceaction' is not an approved test database.` and `exit=2` |
| R10 secrets | `for v in DB_TEST_PASSWORD DB_TEST_SCHEMA_PASSWORD; do val=$(grep "^$v=" .env \| cut -d= -f2-); echo "$v: $(git ls-files -m -o --exclude-standard -z \| xargs -0 grep -l -F "$val" 2>/dev/null \| wc -l) changed or new repo files; $(grep -rIl -F "$val" $E ~/Desktop/D0-Backup-Copy 2>/dev/null \| wc -l) evidence or Desktop-copy files"; done` (takes a minute or two; prints counts only) | 0 and 0 for both |
| R12 scope | `git diff --stat -- python-engine/app python-engine/rulesets backend/app backend/database` and `git status --short` | The diff prints nothing; the status lists only test code, `Makefile`, `backend/phpunit.xml`, `scripts/provision-test-db.sh` and documents |
| R2, R3, R11, R13, R14 | Read: `$E/07_restore.txt`, `$E/00_summary.txt`, remediation §2.5, `scripts/provision-test-db.sh`, package §4 and §1 | As described in the checklist |

(In the commands above `\|` means a literal pipe character inside a table cell; type it as `|`.)

### 3.2 Self-review record template

Completed by the owner, dated, and kept with the evidence. **It must carry the label below.**

```
D0 REVIEW RECORD  -  NON-INDEPENDENT OWNER SELF-REVIEW  (DR-10 / DEC-033; independence waived by the owner)
Reviewer: the owner      Date: ____________      Commands run by: [ ] the owner personally  [ ] with AI assistance (weaker; state which)
R1  ___  R2  ___  R3  ___  R4  ___  R5  ___  R6  ___  R7  ___  R8  ___  R9  ___  R10 ___  R11 ___  R12 ___  R13 ___  R14 ___
(Pass / Fail / Query)    Notes: ______________________________________________
Key: [ ] stored in the password manager   [ ] recovery verified by the decryption check   [ ] local key file removed
Residual risks acknowledged: [ ] no independent reviewer  [ ] backups on this Mac only (DEC-032)
Outcome: [ ] all Pass  [ ] items to resolve: ___________      D0 acceptance is a separate decision.
```

### 3.3 Owner self-review execution sheet (R1-R14)

**NON-INDEPENDENT owner self-review (DEC-033 / DR-10).** Item names and expected results are those of the checklist in section 3 (nothing renamed or omitted; for R1 note that the checklist says three `SHA256SUMS*` files and a fourth, `.backup-exception`, was added later, so four are checked). "AI-assisted result" is the AI's run of `owner_review.sh` with `RUN_BY=ai-assisted` (evidence files 22, 22a); **it is AI-generated evidence, not owner-executed evidence, and it makes no item PASS in the owner's review.** "Owner result" stays PENDING until the owner executes the item and the output and exit code are available. The runner item names are in the second column.

| R | Purpose | Runner item / method | Expected result | Mode | AI-assisted result (not owner evidence) | Owner-executed result |
|---|---|---|---|---|---|---|
| R1 | Evidence integrity | R1: `shasum -a 256 -c` on the four sum files | 0 failures in each | read-only | exit 0; 0, 0, 0, 0 failures; PASS | **PASS** (owner-run; log) |
| R2 | Backup restoration | R2: `cmp` pre-dump, post-dump and scratch manifests; count `candles` chunks; restore-log errors | Identical; 10,830 chunks; 0 pg_restore errors | read-only | exit 0; `MANIFESTS_IDENTICAL`, 10830, 0 errors; PASS | **PASS** (owner-run; log) |
| R3 | Restore: schema and structure | R3: schema dumps with the per-run restrict lines removed; count structure differences | `SCHEMA_IDENTICAL`; 38 differing structure lines (the two documented effects) | read-only | exit 0; `SCHEMA_IDENTICAL`, 38; PASS | **PASS** (owner-run; log). Also analysed line by line: 36 ordinal-only lines in `analysis_runs`/`candle_snapshots` plus 2 `migrations` ACL lines; nothing else; owner accepted the explanation |
| R4 | Backup contents and handling | R4: ciphertext hashes of copy A, copy B and the Desktop duplicate; duplicate byte-identical; plaintext directory removed. Also read `02_quiesce.txt`, `04_dump.txt`, `06_encrypt.txt` | A, B, B match; duplicate identical; work directory removed | read-only | exit 0; as expected; PASS (the three files are for reading) | **PASS** (owner-run; log) |
| R5 | Waiver, residual risk and key handling | Manual: read DEC-032 and §2.8; then attest the key steps (section 2) | Waiver recorded and not called an off-device backup; key stored, recovery verified, local key removed | manual | Facts only: the waiver is recorded; **the local key file still exists; recovery not verified**. PENDING | **PASS by NON-INDEPENDENT OWNER ATTESTATION** (DEC-033), with a caveat: the official clipboard script did **not** pass (trailing space); the key was verified by a separate manual decryption; local key removed, directory empty. See section 3.4 |
| R6 | Development database integrity | R6: read-only manifest compared with the baseline; structure differences | `MANIFEST_IDENTICAL`; 0 unexpected structure differences | read-only (read-only database session) | exit 0; identical; 0; PASS | **PASS** (owner-run; log) |
| R7 | Test isolation: engine | R7: engine integration tests and guard tests as `app_test`; refusals recorded in evidence 11 | 4 + 8 + 4 + 36 passed, none skipped | **writes only to `priceaction_test`** | exit 0; 52 passed; 8 refusals recorded; PASS | **PASS** (owner-run; log) |
| R8 | Test isolation: Laravel | R8a: container default environment refused (exit 2); R8b: `make test-backend` | Refused with exit 2; `OK (217 tests, 2972 assertions)` | R8a no network; **R8b writes only to `priceaction_test`** | exit 0 each; refused, exit=2; OK (217 tests, 2972 assertions); PASS | **PASS** (owner-run; log; R8a and R8b) |
| R9 | Role privileges | R9: catalog query and a real connection attempt for each role | `connect=false`, 0 tables with any privilege; both attempts refused | read-only; refused connection attempts | exit 0; false, 0, 0; refused yes, yes; PASS | **PASS** (owner-run; log) |
| R10 | Secrets | R10: counts of files containing either test password | 0 and 0 for both | read-only | exit 0; 0 and 0 for both; PASS | **PASS** (owner-run; log) |
| R11 | Provisioning | R11: syntax, name-pattern guard, no development connection, password never rotated. Also read §2.7 | `SYNTAX_OK`; guard present; 0 development connections; unchanged-branch present | read-only | exit 0; as expected; PASS | **PASS** (owner-run; log) |
| R12 | Scope | R12: no change under engine app, rulesets, backend app, database; changes within the permitted set; P0-1 artifact hashes | 0; 0; `77f4bbc89e696d47 231069837c7b406e b8f44a428a89b4b5` | read-only | exit 0; as expected; PASS | **PASS** (owner-run; log) |
| R13 | Historical data provenance and limitations | Manual: read section 4 | Understood and accepted as the scope of D1-D6 | manual | PENDING (reading) | **APPROVED by the owner (2026-11-25)**: the minimum-sufficient remediation approach of [remediation §2.10](orb-data-remediation.md#210-r13-proposed-minimum-sufficient-remediation-approved-approach-only) (approach only; D1-D6 not authorised) |
| R14 | D0 acceptance criteria | Manual: walk the matrix in section 1 and the final gate in section 6 | Every row Verified or explicitly deferred | manual | PENDING | **CONFIRMED by the owner (2026-11-25)**: the matrix of section 1 was reviewed and confirmed. This is a completed matrix review, **not** a formal D0 acceptance |

Summary of the AI-assisted run: automated PASS 12, FAIL 0; manual PENDING 3 (R5, R13, R14). A first attempt showed 8 FAIL verdicts caused by defects in the runner itself (verdict patterns, one escaping error, one quoting error); the underlying outputs were correct, the runner was fixed and the run repeated (evidence 22a keeps the first log). **Owner-executed R1-R14: 0 of 14 executed.**

### 3.4 Owner self-review record (recorded 2026-11-25)

```
D0 REVIEW RECORD  -  NON-INDEPENDENT OWNER SELF-REVIEW  (DR-10 / DEC-033; independence waived by the owner)
Reviewer: the owner      Date: 2026-11-24/25      Commands run by: [x] the owner personally  [ ] with AI assistance
R1  PASS  R2  PASS  R3  PASS  R4  PASS  R5  PASS (owner attestation, caveat)  R6  PASS  R7  PASS  R8  PASS  R9  PASS  R10 PASS  R11 PASS  R12 PASS
R13 APPROVED (approach only)     R14 CONFIRMED (matrix review; not an acceptance)
Key: [x] stored in the password manager (Apple Passwords, trailing-space caveat)   [x] recovery verified by a MANUAL decryption check (the official script did NOT pass)   [x] local key file removed (directory empty)
Residual risks acknowledged: [x] no independent reviewer  [x] backups on this Mac only (DEC-032)
Outcome: [x] all items recorded (R1-R12 Pass, R13 approved, R14 confirmed)      D0 acceptance is a separate decision, NOT given.
```

**Canonical log and the second log.** The canonical latest owner-run log is `owner-review-20261124T213558Z-owner.log` (run by owner, repo HEAD `a33bb83`). An earlier owner-run log, `owner-review-20261124T193158Z-owner.log`, is preserved unchanged. Both give R1-R4 and R6-R12 PASS and R5, R13, R14 PENDING. After masking timestamps, their only difference is one fact line in R5 (key file exists: YES in the earlier log, NO in the later one). Why the earlier run was made is not known and is not asserted here. Checksums are in `SHA256SUMS.owner-review` and evidence file 23.

**R3 (PASS, owner accepted the explanation).** The 38 differing structure lines are 36 column lines (18 development, 18 restore) in `analysis_runs` (14) and `candle_snapshots` (4) that differ only in ordinal position after dropped columns (identical once the ordinal is removed), plus 2 lines for the explicit versus default owner ACL of `public.migrations`. No other structure difference was found. The schema dumps are identical after the per-run `\restrict` lines are removed. The original manifests (files 03, 05, 08, 09) are unchanged.

**R5 (PASS by NON-INDEPENDENT OWNER ATTESTATION, DEC-033; owner-reported, not independently observed).**
1. The original key was saved in Apple Passwords, entry `PriceAction AI — D0 Backup Key`.
2. The password-manager copy included one trailing space.
3. The official `verify_key_from_clipboard.sh` initially **failed** because of that trailing space. **It did not pass.** The script was not modified.
4. A separate manual verification removed the trailing space in shell memory and decrypted both encrypted files with the documented parameters (`aes-256-cbc`, `pbkdf2`, 600,000 iterations). `priceaction.dump: OK` and `globals.sql: OK` (the recorded plaintext SHA-256 values).
5. The local key file was then removed with the documented command. The owner confirmed that it no longer exists and that the key directory is empty. A read-only existence check by the preparer agrees (file absent, 0 entries); no key was read.
- **Caveats.** The recovery was proven by a manual method, not by the documented script. The terminal output of the manual verification is not stored in the evidence folder. Recovery from the stored entry needs trailing whitespace removed. The script cannot be used on that entry as it stands; changing it is a separate decision.
- **Warning.** Both encrypted copies are on this Mac only (DEC-032); the key now exists only in the password manager.

**R13: APPROVED by the owner (2026-11-25), approach only.** The owner approved the minimum-sufficient remediation approach of [remediation §2.10](orb-data-remediation.md#210-r13-proposed-minimum-sufficient-remediation-approved-approach-only) ([DEC-034](../../DECISIONS.md)). D1-D6 are unchanged; D1-D5 complete before D6; D6 needs a frozen dataset and the required independent human review (DR-7); material unresolved corporate actions exclude the affected instrument-sessions from Stage A; unknown or unverifiable tick sizes are not failures; survivorship bias, unverified costs and slippage, missing minute data and the inferred test-activity churn remain documented limitations that D1-D6 are not claimed to resolve. **This approval does not authorise executing D1-D6.**

**R14: CONFIRMED by the owner (2026-11-25).** The matrix in section 1 is confirmed: rows 1-2, 3a, 3c-3e and 4-10 VERIFIED; rows 3b, 11 and 12 DEFERRED; row 13 pending formal acceptance. This is a completed matrix review, **not** formal D0 acceptance.

**D0 formal acceptance: ACCEPTED WITH CAVEATS (owner decision, 2026-11-25; [DEC-035](../../DECISIONS.md)).** Exact owner decision: "I formally accept D0 with the caveats listed." The review record above is preserved as written at the time of the review (its last line, "D0 acceptance is a separate decision, NOT given", was true then); the acceptance is this separate, later decision. The review classification stays **NON-INDEPENDENT**.

Caveats retained:
1. The official `verify_key_from_clipboard.sh` did **not** pass, because the copied password-manager key contained trailing whitespace. The script, the key and the backups are unchanged.
2. Manual decryption after trimming the whitespace in memory passed for **both** backup files (`priceaction.dump`, `globals.sql`).
3. All backup copies are on the same physical Mac. This is **not equivalent to an off-device backup** (DEC-032): a physical failure, theft, loss or destruction of this Mac could destroy both copies.
4. The recovery key exists only in the password manager.
5. R5 was supported by owner attestation and was **not independently observed**.
6. DR-7 and DR-7a still apply to D1-D6. An independent human reviewer must be appointed before that work proceeds.
7. T-I165 (recovery-script correction, section 2.1) remains proposal-only and is not executed.

Scope boundary: this acceptance authorises only the recording and verification of the decision. It does **not** authorise D1-D6 execution or data remediation, P0-1 or P0-1b, any historical or prospective backtest, ORB implementation or strategy, ruleset or PAQS changes, service restarts (the backend, queue, scheduler and engine stay stopped), database mutations, or commits, merges and pushes.

**Recovery caveat (R5).** See section 2.1.

## 4. Historical data provenance and outstanding limitations (context for R13)

D0 does not remediate these; D1-D6 do. D0 was accepted with caveats on 2026-11-25, but D1-D6 are **not authorised** by that acceptance and need a separate owner decision and an appointed independent reviewer (DR-7a).

- **Tick sizes:** no historical tick-size record exists. Pre-2026-11-19 rows for 29 of the 50 instruments are demo-seeder placeholders (0.05); 21 instruments have none. The tick clause of `ORB-MG-02` is frozen; the amendment MG02-A1 (policy formally approved; no adjusted-price exception; strict definition of a known tick) is not yet adopted.
- **Corporate actions:** the table was never populated and no authoritative source exists in the repository or database for 2024-2026; provider history is split and bonus adjusted, demergers are not adjusted.
- **Calendar:** no authoritative historical exchange calendar; sessions can only be inferred from stored candles (39 weekdays without bars, three full-length weekend sessions, special and Muhurat sessions unverified).
- **Provenance:** 29 of 50 instruments are flagged `is_demo = true` although they carry Kite data (labelling defect plus shared instrument identity across data modes); candles are partitioned by data source.
- **Opening-range integrity:** four of the five missing-bar sessions have a recorded cause (a provider 09:15 bar rejected as "OHLC out of order"); one (ITC, 2025-01-06) has none; closure at capture cannot be shown for backfilled data.
- **Other:** survivorship (today's NIFTY 50 applied to all history), unverified costs and slippage, no minute data. The 150 inserted-and-deleted `data_quality_issues` rows and the instrument-snapshot churn are most likely integration-test activity on the development database (inferred, not proven); the D0 guards now prevent a repeat.

## 5. Remaining items after D0 acceptance

D0 blockers: **none** (formal acceptance recorded 2026-11-25, DEC-035). Still open, none of them part of D0: a decision on when the stopped services restart; the appointment of an independent human reviewer (DR-7a) and a separate authorisation before any D1-D6 work; the optional recovery-script correction (T-I165, proposal-only). Caveats are listed in section 3.4.

## 6. Final D0 acceptance gate

D0 could be **recommended** for acceptance only when every condition below was met. The recommendation was not an acceptance: **formal acceptance required a separate, explicit owner decision, which the owner gave on 2026-11-25 (DEC-035).**

| Condition | Status (2026-11-25) | Class |
|---|---|---|
| Backup and restore evidence valid | **MET** (owner-run R1-R4; R3 differences fully explained) | Owner-run |
| DEC-032 conditions satisfied: copies in separate directories; recorded SHA-256 match; restore evidence preserved | **MET** (R4) | Owner-run |
| DEC-032 condition: key stored in the password manager | **MET by owner attestation** (Apple Passwords; trailing-space caveat) | Owner attestation |
| Password-manager recovery verified | **MET by manual decryption (owner-reported); the official script did NOT pass** (caveat, section 2.1) | Owner attestation |
| Local key file removed after successful verification | **MET** (owner-reported; file absent, directory empty) | Owner attestation |
| R1-R14 completed and recorded (NON-INDEPENDENT owner self-review) | **MET** (R1-R12 PASS, R13 approved, R14 confirmed) | Owner self-review |
| Development database integrity confirmed | **MET** (R6) | Owner-run |
| Test isolation verified (engine and Laravel) | **MET** (R7, R8, R9) | Owner-run |
| Residual risks documented | **MET** (DEC-032: same-device backups; DEC-033: no separate human reviewer) | Documentation |
| No unexplained scope changes | **MET** (R12) | Owner-run |
| Formal owner acceptance (separate, explicit decision) | **MET: ACCEPTED WITH CAVEATS on 2026-11-25 (DEC-035)** | Owner decision |

**Gate complete: D0 is ACCEPTED WITH CAVEATS (owner, 2026-11-25, [DEC-035](../../DECISIONS.md)).** Owner decision: "I formally accept D0 with the caveats listed." Every gate condition above is met and the formal acceptance condition is now met. The review remains classified **NON-INDEPENDENT**. The recommendation made before the decision (D0 recommended for acceptance, with caveats) is preserved in the version history of this package.

Caveats retained: the official clipboard script did not pass (trailing whitespace); a manual decryption after trimming passed for both backup files; all backup copies are on the same physical Mac and this is not an off-device backup; the recovery key exists only in the password manager; R5 is owner attestation, not independently observed; DR-7 and DR-7a still apply to D1-D6 and an independent human reviewer must be appointed before that work proceeds; T-I165 is proposal-only.

**Not authorised by this acceptance:** D1-D6 execution or data remediation; P0-1 and P0-1b; historical or prospective backtests; ORB implementation or strategy, ruleset or PAQS changes; service restarts; database mutations; commits, merges or pushes.
