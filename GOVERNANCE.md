# Governance register

The `governance/` folder is the **governance project**, shared by all data products. It is not a dbt project and builds no view: it holds the *vocabulary* and the *rules*, while each data product holds its views and its access rights.

| The governance project declares | A data product declares (in its `dbt_project.yml` and YAML) |
|---|---|
| the **tags** (the sensitivity vocabulary) | the **attachment** of a tag to one of its columns or views |
| the **policies** (one rule per category) | its **roles** and their privileges on *its* databases |
| the **users** and the **umbrella roles** (`denodo_developer_global`): they pre-exist every product and hold real people | plugs its own developer role into an umbrella role (`granted_to`), never creates or changes it |
| the **identity mappings** read by the policies | |

The tag is the only point of contact: the product says *"this column is personal data"*, the governance says *"personal data is masked like this"*. Neither needs to know the other.

This file is the **readable** register; the `.vql` files of `governance/` are the implementation. `python run_demo.py --audit` compares those `.vql` files with what actually runs on the server.

## Tag vocabulary

Two families, because a policy cites them in two different places: `class_` says **what the data is** (the target of a mask or a deny), `scope_` says **which key decides the slice you see** (cited inside the rule's condition).

| Tag | Meaning | Attached by | Where |
|---|---|---|---|
| `class_cost` | purchase cost, confidential | music product | `iv_catalog.cost_price` |
| `class_pii` | personal data (GDPR) | sales product | `iv_invoices.email` |
| `class_confidential` | transactional detail view, restricted access | analytics product | `iv_sales` (whole view) |
| `scope_label` | scope key: the labels a buyer manages | music product | `iv_catalog.label_id` |
| `scope_customer` | scope key: the customers of a sales rep | sales product | `iv_invoices.customer_id` |

Declared in [`governance/20_tags.vql`](governance/20_tags.vql), **without attachment**, on purpose: attachments live with the views, in the dbt projects, because they live and die with them.

## Rules

### `p_cost_default_deny`

| | |
|---|---|
| **Intent** | the purchase cost is not ordinary working data: it is masked by default |
| **Category** | `class_cost` |
| **Audience** | every role **except** `buyer` |
| **Effect** | column masking: the value is returned as `NULL` |
| **Why this form** | `NOT_IN ROLES`, not `ANY ROLES`: a role created tomorrow is covered automatically. With `ANY ROLES`, the analyst role, never listed, saw the cost |
| **Implemented in** | [`governance/82_policies.vql`](governance/82_policies.vql) |

### `p_buyer_cost_mask`

| | |
|---|---|
| **Intent** | a buyer needs the cost, but only on the labels they manage |
| **Category** | `class_cost`, keyed by `scope_label` |
| **Audience** | `buyer` |
| **Effect** | conditional masking: cost in clear on their labels, null elsewhere. The whole catalogue stays visible |
| **Identity** | derived from the connected login through `governance/10_security_staging.vql`, never from a query parameter |
| **Implemented in** | [`governance/82_policies.vql`](governance/82_policies.vql) |

### `p_salesrep_own_customers`

| | |
|---|---|
| **Intent** | a sales rep only sees the invoices of their own portfolio |
| **Category** | keyed by `scope_customer` |
| **Audience** | `sales_rep` |
| **Effect** | **row** filtering: other invoices are removed, not masked |
| **Identity** | login -> managed customers, through `governance/10_security_staging.vql` |
| **Implemented in** | [`governance/82_policies.vql`](governance/82_policies.vql) |

### `p_mask_email_pii`

| | |
|---|---|
| **Intent** | personal data is not readable in clear |
| **Category** | `class_pii` |
| **Audience** | everyone **except** `customer_support` |
| **Effect** | unconditional masking: the value is returned as `NULL` |
| **Exception** | customer support, who must be able to call a customer back. Granted to a **role**, never to a user: a privilege granted directly to a person is not restricted by a policy written on roles |
| **Review** | yearly |
| **Implemented in** | [`governance/84_policies_pii.vql`](governance/84_policies_pii.vql) |

### `p_deny_sales_analyst`

| | |
|---|---|
| **Intent** | the transactional detail (cost and named customer) is not an analysis playground |
| **Category** | `class_confidential` |
| **Audience** | `analyst` |
| **Effect** | execution **denied**: a privilege error, not redacted data |
| **Implemented in** | [`governance/86_policy_deny.vql`](governance/86_policy_deny.vql) |

## Roles

| Role | Created by | Members |
|---|---|---|
| `buyer`, `sales_rep`, `analyst`, `customer_support` | dbt, declared in each product that admits them | assigned in `governance/80_user_roles.vql` |
| `chinook_music_developer`, `chinook_sales_developer`, `chinook_analytics_developer` | dbt, one per product: `CONNECT, METADATA` only | granted to `denodo_developer_global` through `granted_to` |
| `denodo_developer_global` | `governance/30_users.vql`: a pre-existing umbrella role that holds real people | `dev_global` |

## What this register does not describe

- **database privileges**: they belong to the data products (their `dbt_project.yml`) and converge on every build;
- **tag attachments**: same, they live with the view;
- **privileges granted at view level, or directly to a user**: they should not exist. A grant on one view shows in no database-level declaration. A grant made directly to a user is worse: the policies above have their audience written in roles, so they do not restrict it (documented Denodo behaviour, measured on this demo). The audit (`dbt run-operation denodo_audit`) reports both.

## Deployment order

Files `0*` to `7*` are deployed **before** the dbt projects (the vocabulary and the users must exist). Files `8*` are deployed **after**: a policy refuses to be created when the roles of its audience do not exist, and the roles are created by dbt.

```bash
python run_demo.py            # platform + governance (0* to 7*)
python run_demo.py --dbt      # dbt build, the three products
python run_demo.py --post     # governance (8*)
python run_demo.py --verify   # who sees what
python run_demo.py --audit    # server vs this folder
```
