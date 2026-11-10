# Demo script

How to replay, by hand and in front of an audience, the five steps of the [walkthrough](02_walkthrough.md). For each step: the command, what to show, what you must see, and what to say.

Rehearse it once from the reset to the end before showing it to anyone. Every output quoted here was captured on Denodo Platform 9.4.7.

## At a glance

| Step | Command | Lasts | The point to make |
|---|---|---|---|
| Reset (before the audience arrives) | `python run_demo.py --teardown` then `python run_demo.py` | 1 min 30 s | none |
| 1. A data model you can trust | `python run_demo.py --dbt` | 3 min | descriptions and tests travel with the views |
| 1. The test that fails | `python run_demo.py --dbt dbt_sales` | 40 s | bad data stops at the door |
| 2. Two areas | nothing to run | | consumers only see the published area |
| 3. Roles | `python run_demo.py --roles` then `--verify` | 10 s | a role opens the door, and only the door |
| 4. Global Security Policies | `python run_demo.py --policies` then `--verify` | 10 s | same query, different answers |
| 5. A fourth data product | `python run_demo.py --add-product` | 1 min | protected without touching a rule |
| 5. The audit | `python run_demo.py --audit` | 1 min 30 s | what was changed by hand is visible |

About ten minutes of commands. Count twenty-five to thirty minutes with the explanations.

## Before you start

- The setup of the [README](../README.md#setup) is done: both repositories ([denodo-data-mesh-demo](https://github.com/vharcq/denodo-data-mesh-demo) and [dbt-denodo-extras](https://github.com/vharcq/dbt-denodo-extras)) cloned side by side, `demo.env` filled in, the Python environment active (`dbt --version` answers).
- One terminal, opened in the folder of this repository, with a font large enough to be read from the back of the room.
- Design Studio open in a browser, logged in as an administrator.
- The file `data/invoice_line.csv` open in a text editor (used in step 1).

`--verify` prints many blocks. In each step below, only the blocks named are worth showing; scroll to them.

## Reset

Do this before the audience arrives. It removes every object of the demo from the server, then recreates the empty databases, the sources, the tag vocabulary and the seven demo users.

```bash
python run_demo.py --teardown
python run_demo.py
```

**You must see** `Done, no failure.` at the end of the second command. On a server that never ran the demo, the teardown prints `skip` on every line: that is expected.

At this point the server has sources and users, and no view and no rule.

## Step 1. A data model you can trust

**Say.** "Each team's data product is a folder of text files. Every view is one query, and every view and column has its description written next to it. One command builds everything in Denodo, in the right order, and tests it."

```bash
python run_demo.py --dbt
```

It takes about three minutes: use them to explain the three products (Music, Sales, Analytics) while the lines scroll.

**You must see**, once per product:

```
Done. PASS=21 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=21      (music)
Done. PASS=24 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=24      (sales)
Done. PASS=8 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=8        (analytics)
```

**Show in Design Studio.** Refresh the tree. Open the database `chinook_music`, then the view `iv_catalog`, and show its description and the description of its columns (for instance `cost_price`: *"Purchase cost of one unit of the track, in euros. Confidential."*).

**Say.** "Nobody typed these descriptions in Denodo. They come from the project, they were reviewed with it, and they are written again at every deployment."

### The test that fails

**Say.** "Now let us break the data. I add an invoice line for invoice 99, which does not exist."

In `data/invoice_line.csv`, add this line at the end and save:

```
5,99,1,1
```

```bash
python run_demo.py --dbt dbt_sales
```

**You must see** two failed tests, three skipped steps and an error at the end:

```
FAIL 1 relationships_stg_invoice_line_invoice_id__invoice_id__ref_stg_invoice_
FAIL 1 relationships_iv_invoice_line_invoice_id__invoice_id__ref_iv_invoices_
SKIP relation chinook_sales.be_customer
  Got 1 result, configured to fail if != 0
Done. PASS=19 WARN=0 ERROR=2 SKIP=3 NO-OP=0 REUSED=0 TOTAL=24
```

**Say.** "The deployment says which rule was broken and how many rows break it, and it did not rebuild the customer view on top of the broken data. Denodo alone has no such test."

**Put it back.** Remove the line you added, save, and run the same command again. You must see `PASS=24` and `ERROR=0`. Do not go on before you see it.

## Step 2. Two areas: where we work, and what we publish

Nothing to run: the two areas were built in step 1.

**Show in Design Studio.** Side by side:

- `chinook_sales_staging`: the data source, the base views (`bv_`) and the views that only fix types and names (`stg_`).
- `chinook_sales`: three finished views, in folders `/30 Integration views` and `/40 Business Entities`.

**Say.** "Every data product is two databases. The first one is the workshop: the team changes it as it likes. The second one is the shop window: it is the only thing a consumer will ever see. Analytics has no workshop at all, because it owns no source: it only reads what the two others publish."

**Then say what is missing.** "Two areas exist, but nothing says yet who may enter which."

## Step 3. Roles: who may enter

**Say.** "Each product declares, in a few lines of its project, which roles may enter its databases. The deployment already created those roles. The security team now attaches people to them."

```bash
python run_demo.py --roles
python run_demo.py --verify
```

**Show first, at the very end of the output**, the block `STAGING ISOLATION`:

```
[buyer_blue] ERROR: ... Insufficient privileges to connect to the database 'chinook_music_staging'
```

**Say.** "The door works. A buyer cannot open the workshop."

**Then scroll up to** `RULE 2` and `RULE 3`:

```
[rep_alice] iv_invoices (Alice's customers: 1, 2) (3 rows):
    (1, 'Alice Martin', 'alice@example.com')
    (2, 'Bob Durand', 'bob@example.com')
    (3, 'Chloe Petit', 'chloe@example.com')

[analyst_bob] iv_invoices (analyst -> e-mail masked) (3 rows):
    (1, 'Alice Martin', 'alice@example.com')
    ...
```

**Say.** "But look inside. Alice should see the invoices of her two customers: she sees all three. The analyst should not see personal data: every e-mail is there. A role says who enters. It does not say what each person sees once inside."

The labels in brackets describe what each account *should* see. In this step they are wrong on purpose: that gap is the point.

## Step 4. Global Security Policies: what each person sees

**Say.** "Two teams, one point of contact. The product team says what the data is: it puts a tag next to the column, 'this is personal data'. The security team says what that means: one rule per tag. Here are the rules."

**Show in Design Studio.** Menu *Administration > Semantics and governance > Global security policies*: none of the five policies of the demo is there yet.

```bash
python run_demo.py --policies
python run_demo.py --verify
```

**Show in Design Studio.** Refresh the same dialog: five policies. Open `p_mask_email_pii` and read it aloud: everyone except the role `customer_support`, on columns tagged `class_pii`, masked.

**Show in the terminal** the same blocks as in step 3:

```
[rep_alice] iv_invoices (Alice's customers: 1, 2) (2 rows):
    (1, 'Alice Martin', None)
    (2, 'Bob Durand', None)

[analyst_bob] iv_invoices (analyst -> e-mail masked) (3 rows):
    (1, 'Alice Martin', None)
    (2, 'Bob Durand', None)
    (3, 'Chloe Petit', None)

[support_sarah] iv_invoices (customer support -> EXCEPTION, e-mail in clear) (3 rows):
    (1, 'Alice Martin', 'alice@example.com')
    ...
```

**Say.** "Same query, same views, nothing redeployed. Alice now sees her two customers, the e-mails are hidden from everyone except customer support."

**Then show** the block `Cross-database`: the Blue Note buyer queries the Analytics product and sees the purchase cost on the Blue Note lines only.

**Say.** "Analytics declared no tag and no rule. The cost was tagged in Music, where it is born, and the rule followed it into another database built by another team."

To replay the change from step 3 to step 4, `python run_demo.py --drop-policies` removes the five policies and leaves everything else.

## Step 5. The day after

### A fourth data product

**Say.** "The system is right today. What does it cost tomorrow? The finance team wants a customer statement: invoice lines with the customer's e-mail and the purchase cost, the two most sensitive things we have, in one view."

**Show in the editor** the file `dbt/dbt_finance/dbt_project.yml`, section `security:`.

**Say.** "This is all the finance team wrote about security: eighteen lines that say which existing roles may enter. No tag. No rule. And the security team is not even in the room."

```bash
python run_demo.py --add-product
```

**You must see** the build succeed (`PASS=4`), then:

```
[analyst_bob] iv_customer_statement (analyst -> e-mail and cost masked) (4 rows):
    (1, 'Alice Martin', None, 'Blue Note', None)
    ...
[rep_alice] iv_customer_statement (sales rep -> own customers only, e-mail and cost masked) (3 rows):
    ...
[support_sarah] iv_customer_statement (customer support -> e-mail in clear, cost masked) (4 rows):
    (1, 'Alice Martin', 'alice@example.com', 'Blue Note', None)
    ...
[buyer_blue] ERROR: ... Insufficient privileges to connect to the database 'chinook_finance'
```

**Say.** "A database that did not exist one minute ago, protected from its first second. Zero policy changed, zero tag declared. The fourth product cost the security team nothing, and so will the fortieth."

### Seeing what was changed by hand

**Say.** "Things also change outside the files. Somebody grants an access in a hurry and forgets it. Let me do exactly that."

In the VQL Shell of Design Studio, as administrator:

```sql
ALTER USER analyst_bob GRANT EXECUTE ON chinook_sales.iv_invoices;
```

```bash
python run_demo.py --audit
```

**You must see**, in the part about `dbt_sales`:

```
USER  analyst_bob: DIRECT privilege on chinook_sales.iv_invoices (EXECUTE): not through a role, so the policies written on roles do not restrict it
1 finding(s). Report only: nothing was modified.
```

The other parts say `No drift`.

**Say.** "The audit found it. And this one matters: a right given directly to a person is not restricted by rules written for roles. Denodo documents it. With this single grant, the analyst reads the e-mails again. So access always goes through a role, and the audit tells us when it does not. It only reports: a person decides whether the access is legitimate."

If you have time, prove it with `python run_demo.py --verify`: in `RULE 3`, the analyst's e-mails are visible again.

**Put it back**, in the VQL Shell:

```sql
ALTER USER analyst_bob REVOKE EXECUTE ON chinook_sales.iv_invoices;
```

## Closing line

"One rule, written once, by the people responsible for it. Every team that publishes data only says what its data is. Everything is in files that are reviewed and can be replayed, and Denodo enforces it wherever the data goes."

## If something goes wrong

| What you see | What to do |
|---|---|
| `dbt not found on PATH` | The Python environment is not active in this terminal |
| A `FAIL` line during the reset mentioning the user password | `DEMO_USERS_PASSWORD` in `demo.env` does not satisfy the server's password policy |
| Step 1 still fails after you removed the extra line | The file was not saved in the editor |
| `--policies` fails on a role that does not exist | `--dbt` has not been run: the roles are created by the build |
| Anything else | Start again from the reset: the whole sequence takes about seven minutes |

After the session, `python run_demo.py --teardown` leaves the server as it was.
