# Denodo governance as code

**Global Security Policies declared, reviewed and audited with dbt.**

*Vincent Harcq (vincent.harcq@contraste.com), Contraste Europe*

## Summary

Denodo's tags and Global Security Policies let a security team write a rule once ("personal data is masked for everyone except customer support") and have it applied wherever the data goes. This paper shows how to build a governed set of data products around them, step by step, with every definition kept in text files: the data model, the descriptions, the tests, the roles and the tags. The files are reviewed like code and deployed by one command, using dbt and Denodo's official dbt adapter.

Each of the five steps answers one question a data owner asks, shows what the step adds, and shows what is still missing before the next one.

| Step | Question | What is added |
|---|---|---|
| 1 | Can I trust this data? | Descriptions and automatic tests |
| 2 | What exactly am I exposing? | A working area and a published area |
| 3 | Who can open what? | Roles |
| 4 | What does each person see inside? | Tags and Global Security Policies |
| 5 | What happens when things change? | A fourth data product, and an audit |

The result that matters most comes at the end. A fourth data product was added after the rules were in place. Its team wrote no rule and declared no tag, and the security team changed nothing. The new product was protected from its first deployment, in 29 seconds.

Everything in this paper was measured on Denodo Platform 9.4.7 with a small fictitious dataset, and can be replayed from two public repositories listed at the end.

## Three ideas to know first

**Data governance.** The rules that decide who may see which data, and the means to prove that those rules are really applied. "A sales representative only sees their own customers" is a governance rule. Without governance, either everything is open to everyone, or every request for data waits for someone's approval.

**Data product and data mesh.** A data product is a set of data that one team publishes for others to use, with a description, a level of quality it commits to and a named owner, like a product on a shelf. A data mesh is a way of organising a company in which each business team publishes its own data products, instead of handing all its data to one central team. Its difficulty is governance: many teams publish, yet the rules must be the same everywhere.

**"As code".** A way of working borrowed from software. Instead of configuring a system by clicking through its screens, you describe what you want in text files, and a tool makes the system match them. The files keep their history, a colleague reviews each change before it is applied, and the same result can be rebuilt at any time. "Governance as code" applies this to the rules of governance.

Two products appear throughout this paper.

| Product | What it is | What it does here |
|---|---|---|
| Denodo | A data virtualization platform: one place to query data that stays in its original systems | It serves the data and enforces the rules. A *tag* is a label put on a column ("personal data"); a *Global Security Policy* is a rule written against a tag |
| dbt | An open-source tool widely used by data teams to build views from text files, test them and document them | It turns the text files into views, descriptions, roles and tags in Denodo, through Denodo's official adapter |

## The example

A music company has three teams. Each one publishes a **data product**: a set of views that other people are allowed to use.

| Data product | Team | What it publishes |
|---|---|---|
| Music | Catalogue | Tracks with their album, artist and label, their selling price and their purchase cost |
| Sales | Invoicing | Invoices, invoice lines and customers, with the customer's e-mail address |
| Analytics | Reporting | Sales detail and sales per label, built only from what the two others publish |

Seven people use them. Two buyers each negotiate with one record label. Two sales representatives each look after their own customers. There is one analyst, one customer support agent and one platform developer.

Three things in this data are sensitive: the **purchase cost** (a buyer may see it for their own label only), the **customer e-mail** (personal data), and the **link between a sales representative and their customers**.

## Step 1. A data model you can trust

**The question: can I trust this data?**

Each data product is a dbt project: a folder of text files in which every view is one SQL query, and every view and column has a description written next to it. One command builds the views in Denodo, in the right order.

**What it adds**

- **Descriptions that stay.** Every published view and column is described in the project, reviewed with the rest of the change, and written into Denodo at each deployment. They appear where people look for them: Design Studio, the Data Catalog, reporting tools. A description typed by hand in Denodo would be lost the next time the view is redeployed; a description in the project cannot be.
- **Tests on every deployment.** Each project lists what must always be true: an identifier is never empty and never duplicated, an invoice line always points to an invoice that exists, a track is never bought for more than it is sold. The three products carry 37 such tests on 13 views, and they run every time the views are built.
- **A contract on what is published.** A published view declares its columns. A change that removes or renames one stops at the team that made it, before any consumer notices.

**What we measured.** We added one invoice line that points to an invoice that does not exist. The deployment ended in error and named the two tests that failed, and the customer view built on top of the invoice lines was skipped instead of being rebuilt on broken data.

**What is still missing.** The data is correct and documented. But everything sits in one place: the raw tables, the intermediate work and the finished views.

## Step 2. Two areas: where we work, and what we publish

**The question: what exactly am I exposing?**

Each data product gets two Denodo databases.

| Area | Contains | Who may open it |
|---|---|---|
| Staging (for example `chinook_sales_staging`) | The connections to the sources, the raw tables, and views that only fix types and names | The product's own team |
| Published (for example `chinook_sales`) | Only the finished views | Consumers |

This is the usual layering of a modern data platform, sometimes called bronze, silver and gold: staging holds bronze and silver, and the published database is gold.

**What it adds**

- **A clean shop window.** A consumer who opens the published database sees a handful of finished, described views, and nothing else.
- **Freedom to change the inside.** The team can reorganise its staging area without breaking anyone, because nobody outside depends on it.
- **A single place to protect.** Since consumers can only reach the published database, the rules of the next steps only have to hold there.

The Analytics product has no staging at all. It owns no source: it reads the published views of Music and Sales, never their staging.

**What is still missing.** The two areas exist, but nothing yet says who may enter which.

## Step 3. Roles: who may enter

**The question: who can open what?**

Each data product declares, in a few lines of its project, which roles may enter its databases and what they may do there. The deployment applies exactly that: it grants what is declared and removes what is not.

**What it adds**

- **Consumers reach the published area only.** A buyer who tries to open the staging database of Music is refused by Denodo.
- **Developers see how things are built, not the data.** A platform developer can read the definitions and the lineage of every product and is refused every query on the data.
- **Access that cannot drift quietly.** We granted ten extra privileges by hand to a role on one database. The next deployment removed all ten, and left that role's rights on the other products untouched.
- **Access always goes through a role.** People are attached to roles by the security team, never given rights one by one. This matters for the next step.

**What we measured, and what is still missing.** With roles alone, the door works but the room has no walls. Everyone who may enter the published database sees everything in it:

| Account | What they should see | What they see with roles alone |
|---|---|---|
| Sales representative Alice | The invoices of her two customers | All three invoices, with e-mails |
| Sales representative Ben | The invoice of his one customer | All three invoices, with e-mails |
| Analyst | Invoices without personal data, no purchase cost | All e-mails and all purchase costs |
| Customer support | Invoices with e-mails | All three invoices, with e-mails |

A role says who enters. It does not say what each person sees once inside.

## Step 4. Global Security Policies: what each person sees

**The question: what does each person see inside?**

This step uses two Denodo features together, and splits the work between two teams.

- **The data product team says what the data is.** In its project, next to the column, it attaches a tag: "this column is personal data", "this column is a purchase cost". It writes no rule.
- **The security team says what that means.** It writes one Global Security Policy per rule, against the tag and not against any particular view: "personal data is masked for everyone except customer support".

The tag is the only point of contact between the two teams. Neither needs to know the other's work.

Five tags and five policies cover the whole example.

| Rule | In plain words |
|---|---|
| Purchase cost | Hidden from everyone; a buyer sees it for their own label only |
| Own customers | A sales representative sees only the invoices of their own customers |
| Personal data | The e-mail is hidden from everyone except customer support |
| Confidential detail | The analyst may not open the detailed sales view at all |

**What we measured.** The same query on the invoices, run by four accounts, before and after the policies were switched on:

| Account | Roles alone (step 3) | With the policies (step 4) |
|---|---|---|
| Sales representative Alice | 3 invoices, e-mails visible | Her 2 invoices, e-mails hidden |
| Sales representative Ben | 3 invoices, e-mails visible | His 1 invoice, e-mail hidden |
| Analyst | 3 invoices, e-mails visible | 3 invoices, e-mails hidden |
| Customer support | 3 invoices, e-mails visible | 3 invoices, e-mails visible |

On the catalogue, the buyer for the Blue Note label sees the seven tracks and the purchase cost of the four Blue Note tracks only. The buyer for Motown sees the cost of the two Motown tracks only. The analyst sees none.

**The rules follow the data.** The Analytics product declares no tag and no rule. It only reads what Music and Sales publish. Yet the Blue Note buyer, querying the Analytics sales view, sees the purchase cost on Blue Note lines and nothing elsewhere. Denodo applies the policies wherever the tagged data travels, in every database a query goes through.

**What is still missing.** The system is right today. The real test is what it costs tomorrow.

## Step 5. The day after

**The question: what happens when things change?**

### A fourth data product

The finance team wants a customer statement: each invoice line with the customer's e-mail, the track, its price and its purchase cost. That is one view containing both kinds of sensitive data.

The finance team built it as a fourth data product. Here is everything that touched security:

| What touched security | Count |
|---|---|
| Policies written or changed | 0 |
| Tags declared by the new product | 0 |
| Changes made by the security team | 0 |
| Lines written by the finance team | 18, saying which existing roles may enter |
| Time to deploy, tests included | 29 seconds |

And here is what each account saw in the new product, straight after that first deployment:

| Account | What they see in the new customer statement |
|---|---|
| Analyst | All 4 lines, e-mail and purchase cost hidden |
| Sales representative Alice | The 3 lines of her own customers, e-mail and purchase cost hidden |
| Customer support | All 4 lines, e-mail visible, purchase cost hidden |
| Buyer (not invited into this product) | Refused |

Nobody had to remember to protect the new view. The e-mail and the cost were tagged where they are born, in Sales and in Music, and the rules followed them.

### Seeing what was changed by hand

Things also change outside the files. Someone grants an access in a hurry during an incident and forgets it. Two audits compare what runs on the server with what the files declare and list the differences: a tag attached by hand, a rule that was switched off, a role with more rights than declared, a view nobody owns any more.

One finding deserves a mention. Denodo documents that a right granted directly to a person, instead of through a role, is not restricted by rules written for roles. We measured it: with one such direct grant, the analyst read the e-mails again. This is why step 3 insists that access always goes through a role, and why the audit reports every right granted directly to a person.

The audit only reports. An access granted at night during an incident may be legitimate, so a person decides whether to keep it and write it down, or remove it.

## What this means

- **For the security team:** a rule is written once, in one place, and covers data products that do not exist yet. Its history is the history of a text file: who changed it, when, and who approved it.
- **For the teams that build data products:** being compliant costs one line per sensitive column, and nothing at all when the product only reuses data that is already tagged.
- **For the organisation:** the cost of governance stops growing with the number of data products. The fourth product cost the security team nothing, and so will the fortieth.
- **For Denodo:** tags and Global Security Policies do the work. This approach adds nothing to the engine. It puts their definitions in files so that they can be reviewed, repeated and audited.

## Limits, stated plainly

- The example is small on purpose: 7 tracks, 3 customers, 3 invoices, 4 data products. It shows behaviour, not performance.
- On version 9.4.7, a column hidden by a tag-based policy is returned empty. We did not obtain partial masking, such as showing only the domain of an e-mail address.
- Administrator accounts are never restricted by Global Security Policies. The rules protect consumers, not administrators.
- The rules hold as long as access goes through roles. The audit reports the exceptions; it does not prevent them.
- People and their assignment to roles are kept outside the data product projects on purpose. They usually come from the company directory.

## To reproduce

Two public repositories contain everything used here. They are meant to be cloned side by side.

| Repository | Content |
|---|---|
| [github.com/vharcq/denodo-data-mesh-demo](https://github.com/vharcq/denodo-data-mesh-demo) | The example: sources, the four data products, tags, policies, and a script that deploys and checks each step. Its demo script (`docs/03_demo-script.md`) replays this walkthrough command by command. |
| [github.com/vharcq/dbt-denodo-extras](https://github.com/vharcq/dbt-denodo-extras) | The reusable part: the dbt macros that declare roles and tags from a project and run the audit. |

Verified on Denodo Platform 9.4.7 with dbt-core 1.12.6 and Denodo's official adapter `dbt-denodo` 1.0.0.
