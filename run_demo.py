#!/usr/bin/env python3
"""Deploy, verify, audit or tear down the governed data-mesh demo on a Denodo VDP.

Three responsibilities, three folders, three owners:

    platform/     virtual databases, datasources, base views   -> integration team
    governance/   tags, users, identity mappings, policies       -> federated governance
    dbt/          the views of each data product                 -> the domain teams

This script deploys the first two; the views (and the roles) come from dbt.

    python run_demo.py --all        # everything below, in order
    python run_demo.py              # 1. VQL: platform/ + governance/ (except 8*)
    python run_demo.py --dbt        # 2. dbt build, music -> sales -> analytics
                                    #    (--dbt dbt_sales builds one project)
    python run_demo.py --post       # 3. VQL: governance/8* (user -> role, policies)
    python run_demo.py --verify     # 4. who sees what, per account

Step 3 in two moves, to show what the roles give alone and what the policies add:

    python run_demo.py --roles          # 3a. governance/80: user -> role
    python run_demo.py --policies       # 3b. governance/82+: Global Security Policies
    python run_demo.py --drop-policies  #     back to 3a (the tags stay)

And the day after: a fourth data product (dbt/dbt_finance) that declares no tag and no
policy, and is protected all the same.

    python run_demo.py --add-product    # database + dbt build + who sees what

    python run_demo.py --audit      #    server vs governance/, then server vs each
                                    #    product's YAML (report only)
    python run_demo.py --teardown   #    drop every object of the demo

Step 3 exists because the ROLES are declared in the dbt projects (`vars: denodo:
security:`) and created by `dbt build`: assigning a user to a role, or naming a role in
a policy AUDIENCE, can only happen after the first build.

Re-runnable: datasources, wrappers, base views, tags and policies use CREATE OR REPLACE;
a database, a role or a user that already exists is reported as `skip` and left as is.
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

from vdp_connect import ENV, ROOT, connect, connect_admin, statements

DATA_DIR = os.path.join(ROOT, "data").replace("\\", "/")
DBT_DIR = os.path.join(ROOT, "dbt")
DBT_PROJECTS = ["dbt_music", "dbt_sales", "dbt_analytics"]   # dependency order
EXTRA_PROJECT = "dbt_finance"                                # built by --add-product only
USERS_PASSWORD = ENV["DEMO_USERS_PASSWORD"]

# Errors that only mean "already there" on a re-run. Anything else is a FAIL.
BENIGN = ("already exist", "duplicate")


# Which VQL files each stage applies, by file name. "base" runs before dbt, the others
# after it: they name roles that only exist once the data products are built.
STAGES = {
    "base": lambda name: not name.startswith("8"),       # platform/ + governance/ 1*-3*
    "roles": lambda name: name.startswith("80"),         # user -> role
    "policies": lambda name: name.startswith("8") and not name.startswith("80"),
    "post": lambda name: name.startswith("8"),           # roles + policies
}


def vql_files(stage):
    found = (sorted(glob.glob(os.path.join(ROOT, "platform", "*.vql")))
             + sorted(glob.glob(os.path.join(ROOT, "governance", "*.vql"))))
    return [f for f in found if STAGES[stage](os.path.basename(f))]


def deploy(stage="base"):
    failures = 0
    conn = connect_admin(); cur = conn.cursor()
    # Users that already exist are left alone. Denodo answers the same empty message
    # ("Error modifying user password") to a CREATE USER on an existing user and to a
    # password its policy refuses, so the two cases cannot be told apart afterwards.
    cur.execute("LIST USERS")
    existing_users = {str(r[0]).lower() for r in cur.fetchall()}
    for path in vql_files(stage):
        print(f"\n=== {os.path.relpath(path, ROOT)} ===")
        for stmt in statements(path):
            head = " ".join(stmt.split())[:64]
            if stmt.upper().startswith("CONNECT DATABASE"):
                db = stmt.split()[2].strip('"')
                cur.close(); conn.close()
                conn = connect_admin(db); cur = conn.cursor()
                print(f"  -- now in database {db}")
                continue
            if stmt.upper().startswith("CREATE USER "):
                if stmt.split()[2].strip('"').lower() in existing_users:
                    print(f"  skip {head}\n         >> user already exists, password kept")
                    continue
            # placeholders: no absolute path and no secret is stored in the repository
            stmt = stmt.replace("@DATA_DIR@", DATA_DIR).replace("@PWD@", USERS_PASSWORD)
            try:
                cur.execute(stmt)
                print(f"  ok   {head}")
            except Exception as e:
                msg = str(e).splitlines()[0]
                benign = any(b in msg.lower() for b in BENIGN)
                failures += not benign
                print(f"  {'skip' if benign else 'FAIL'} {head}\n         >> {msg[:140]}")
                if "modifying user password" in msg.lower():
                    print("         >> DEMO_USERS_PASSWORD does not satisfy the server's password policy")
    cur.close(); conn.close()
    print("\n" + "=" * 66)
    print(f"{failures} failure(s)." if failures else "Done, no failure.")
    if stage == "base":
        print("Next: python run_demo.py --dbt   then   python run_demo.py --post")
    print("=" * 66)
    return failures


def dbt(command, projects, stop_on_error=True):
    """Run one dbt command in each project, in the order given. dbt reads its connection
    from the environment (see dbt/profiles.yml), filled here from demo.env."""
    exe = shutil.which("dbt")
    if not exe:
        sys.exit("dbt not found on PATH. pip install dbt-core dbt-denodo (see README).")
    env = dict(os.environ, **{k: ENV[k] for k in ("VDP_HOST", "VDP_ODBC_PORT", "VDP_USER", "VDP_PASS")})
    for project in projects:
        if not os.path.isdir(os.path.join(DBT_DIR, project)):
            sys.exit(f"No dbt project named {project} in dbt/. Known: {', '.join(DBT_PROJECTS + [EXTRA_PROJECT])}")
        print(f"\n=== dbt {' '.join(command)}: {project} ===", flush=True)
        rc = subprocess.call([exe] + command + ["--profiles-dir", ".."],
                             cwd=os.path.join(DBT_DIR, project), env=env)
        if rc and stop_on_error:
            sys.exit(f"dbt {command[0]} failed for {project} (exit {rc})")


def dbt_build(projects=None):
    dbt(["build"], projects or DBT_PROJECTS)


def audit():
    """Governance side: what runs on the server vs what governance/ declares.

    The counterpart of `dbt run-operation denodo_audit`, which checks the other way
    round (what each data product declares vs the server). Here: the cross-cutting
    objects no dbt project owns (tags, policies).

    Report only: a policy present on the server and absent from the repository may be
    legitimate (set up during an incident). It must be seen, then versioned.
    """
    print("=" * 66 + "\nGOVERNANCE AUDIT: server vs governance/\n" + "=" * 66)
    declared = "\n".join(open(f, encoding="utf-8").read()
                         for f in vql_files("base") + vql_files("post"))
    conn = connect_admin(); cur = conn.cursor()
    findings = []

    def listing(sql):
        try:
            cur.execute(sql)
            return [r[0] for r in cur.fetchall()]
        except Exception as e:
            print(f"  !! {sql}: {str(e).splitlines()[0][:70]}")
            return []

    for kind, sql, pattern in [
        ("POLICY", "LIST GLOBAL_SECURITY_POLICIES", r"GLOBAL_SECURITY_POLICY\s+{name}\b"),
        ("TAG", "LIST TAGS", r"TAG\s+{name}\b"),
    ]:
        for name in listing(sql):
            if not re.search(pattern.format(name=re.escape(name)), declared, re.I):
                findings.append(f"{kind:6} {name}: on the server, not in governance/")

    # a disabled policy is a silent hole: the rule exists and applies to nothing
    for name in listing("LIST GLOBAL_SECURITY_POLICIES"):
        try:
            cur.execute(f'DESC VQL GLOBAL_SECURITY_POLICY "{name}"')
            if re.search(r"ENABLED\s*=\s*FALSE", cur.fetchall()[0][0], re.I):
                findings.append(f"POLICY {name}: DISABLED, the rule exists but does not apply")
        except Exception:
            pass
    cur.close(); conn.close()

    if not findings:
        print("No drift: everything running on the server is declared in governance/.")
    else:
        for f in findings:
            print(f"  {f}")
        print("-" * 66 + f"\n{len(findings)} finding(s). Report only: nothing was modified.")

    # The other way round: what each data product declares vs the server.
    cur = connect_admin().cursor()
    cur.execute("LIST DATABASES")
    databases = {str(r[0]).lower() for r in cur.fetchall()}
    extra = [EXTRA_PROJECT] if "chinook_finance" in databases else []
    dbt(["run-operation", "denodo_audit"], DBT_PROJECTS + extra, stop_on_error=False)


def run(user, db, sql, label):
    """Run one query as one account and print what that account gets back."""
    try:
        c = connect_admin(db) if user == "admin" else connect(user, USERS_PASSWORD, db)
        cur = c.cursor(); cur.execute(sql)
        rows = cur.fetchall(); cur.close(); c.close()
        print(f"\n[{user}] {label} ({len(rows)} rows):")
        for r in rows:
            print("   ", tuple(r))
    except Exception as e:
        print(f"\n[{user}] ERROR: {str(e).splitlines()[0]}")


def add_product():
    """The fourth data product. Its project grants three existing roles the right to
    enter and declares nothing else about security: the tags sit on the columns of the
    products it reads, and the policies follow them into the new database."""
    conn = connect_admin(); cur = conn.cursor()
    try:
        cur.execute("CREATE DATABASE chinook_finance"); print("  ok   CREATE DATABASE chinook_finance")
    except Exception as e:
        print(f"  skip CREATE DATABASE chinook_finance  ({str(e).splitlines()[0][:50]})")
    cur.close(); conn.close()
    dbt_build([EXTRA_PROJECT])
    print("\n" + "=" * 66 + "\nTHE NEW PRODUCT: who sees what, with no tag and no policy added\n" + "=" * 66)
    sql = ("SELECT invoice_id, customer_name, email, label_name, cost_price "
           "FROM iv_customer_statement ORDER BY invoice_id, label_name")
    for user, label in [
        ("admin", "everything in clear"),
        ("analyst_bob", "analyst -> e-mail and cost masked"),
        ("rep_alice", "sales rep -> own customers only, e-mail and cost masked"),
        ("support_sarah", "customer support -> e-mail in clear, cost masked"),
        ("buyer_blue", "buyer -> not invited into this product: REFUSED"),
    ]:
        run(user, "chinook_finance", sql, f"iv_customer_statement ({label})")


def verify():
    print("\n" + "=" * 66 + "\nWHO SEES WHAT\n" + "=" * 66)

    cat = "SELECT track_title, label_name, unit_price, cost_price FROM iv_catalog ORDER BY label_name, track_title"
    print("\n----- RULE 1: COST, secure by default (masked except for a buyer, on their own labels) -----")
    run("admin", "chinook_music", cat, "iv_catalog (admin -> everything in clear)")
    run("buyer_blue", "chinook_music", cat, "iv_catalog (Blue Note buyer -> cost on THEIR labels only)")
    run("buyer_red", "chinook_music", cat, "iv_catalog (Motown buyer -> cost on THEIR labels only)")
    run("analyst_bob", "chinook_music", cat, "iv_catalog (analyst -> cost ALWAYS masked)")

    sales = "SELECT invoice_id, customer_name, track_title, label_name, cost_price FROM iv_sales ORDER BY invoice_id"
    print("\n----- Cross-database: the same rule applies through chinook_analytics.iv_sales -----")
    run("buyer_blue", "chinook_analytics", sales, "iv_sales (cost masked outside Blue Note)")

    inv = "SELECT invoice_id, customer_name, email FROM iv_invoices ORDER BY invoice_id"
    print("\n----- RULE 2: SALES REP, only the invoices of their own customers -----")
    run("admin", "chinook_sales", inv, "iv_invoices")
    run("rep_alice", "chinook_sales", inv, "iv_invoices (Alice's customers: 1, 2)")
    run("rep_ben", "chinook_sales", inv, "iv_invoices (Ben's customer: 3)")

    print("\n----- RULE 3: PERSONAL DATA, e-mail masked for everyone except customer support -----")
    run("analyst_bob", "chinook_sales", inv, "iv_invoices (analyst -> e-mail masked)")
    run("rep_alice", "chinook_sales", inv, "iv_invoices (sales rep -> own customers + e-mail masked)")
    run("support_sarah", "chinook_sales", inv, "iv_invoices (customer support -> EXCEPTION, e-mail in clear)")

    det = "SELECT invoice_id, customer_name, cost_price FROM iv_sales ORDER BY invoice_id"
    print("\n----- RULE 4: DENY, the confidential sales detail is forbidden to the analyst -----")
    run("buyer_blue", "chinook_analytics", det, "iv_sales (buyer -> allowed, cost masked)")
    run("analyst_bob", "chinook_analytics", det, "iv_sales (analyst -> DENY = privilege error)")

    raw = "SELECT track_id, track_title, cost_price FROM bv_track ORDER BY track_id"
    print("\n----- STAGING ISOLATION: no consumer can read the raw layer -----")
    run("admin", "chinook_music_staging", raw, "bv_track (admin reads the raw source)")
    run("buyer_blue", "chinook_music_staging", raw, "bv_track directly (buyer -> must be REFUSED)")


DROP_POLICIES = [
    "DROP GLOBAL_SECURITY_POLICY p_cost_default_deny",
    "DROP GLOBAL_SECURITY_POLICY p_buyer_cost_mask",
    "DROP GLOBAL_SECURITY_POLICY p_salesrep_own_customers",
    "DROP GLOBAL_SECURITY_POLICY p_mask_email_pii",
    "DROP GLOBAL_SECURITY_POLICY p_deny_sales_analyst",
]

TEARDOWN = DROP_POLICIES + [
    "DROP TAG class_cost CASCADE", "DROP TAG scope_label CASCADE",
    "DROP TAG scope_customer CASCADE", "DROP TAG class_pii CASCADE",
    "DROP TAG class_confidential CASCADE",
    "DROP USER buyer_blue", "DROP USER buyer_red", "DROP USER rep_alice",
    "DROP USER rep_ben", "DROP USER analyst_bob", "DROP USER support_sarah",
    "DROP USER dev_global",
    # business and developer roles: created by dbt (vars: denodo: security:)
    "DROP ROLE buyer", "DROP ROLE sales_rep", "DROP ROLE analyst", "DROP ROLE customer_support",
    "DROP ROLE chinook_music_developer", "DROP ROLE chinook_sales_developer",
    "DROP ROLE chinook_analytics_developer", "DROP ROLE chinook_finance_developer",
    # umbrella role: created by governance/30_users.vql
    "DROP ROLE denodo_developer_global",
    # consumers first, then gold, then staging (cross-database dependencies)
    "DROP DATABASE chinook_finance", "DROP DATABASE chinook_analytics",
    "DROP DATABASE chinook_sales", "DROP DATABASE chinook_music",
    "DROP DATABASE chinook_sales_staging", "DROP DATABASE chinook_music_staging",
    "DROP DATABASE chinook_security_staging",
]


def drop(title, statements_):
    print("=" * 66 + f"\n{title}\n" + "=" * 66)
    conn = connect_admin(); cur = conn.cursor()
    for sql in statements_:
        try:
            cur.execute(sql); print(f"  ok   {sql}")
        except Exception as e:
            print(f"  skip {sql}  ({str(e).splitlines()[0][:50]})")
    cur.close(); conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="deploy + dbt + post + verify, in order")
    g.add_argument("--dbt", nargs="*", metavar="PROJECT", default=None,
                   help="dbt build the three data products, or only the ones named")
    g.add_argument("--post", action="store_true", help="governance/8*: run AFTER the dbt build")
    g.add_argument("--roles", action="store_true", help="governance/80 only: user -> role")
    g.add_argument("--policies", action="store_true", help="governance/82+ only: the policies")
    g.add_argument("--drop-policies", action="store_true", help="drop the policies, keep the rest")
    g.add_argument("--add-product", action="store_true", help="build a fourth data product (finance)")
    g.add_argument("--verify", action="store_true", help="who sees what, per demo account")
    g.add_argument("--audit", action="store_true", help="server vs governance/, then vs each product")
    g.add_argument("--teardown", action="store_true", help="drop every object of the demo")
    a = ap.parse_args()
    if a.all:
        if deploy():
            sys.exit(1)      # dbt on a half-deployed platform only hides the cause
        dbt_build()
        if deploy("post"):
            sys.exit(1)
        verify()
    elif a.dbt is not None:
        dbt_build(a.dbt)
    elif a.post or a.roles or a.policies:
        sys.exit(1 if deploy("post" if a.post else "roles" if a.roles else "policies") else 0)
    elif a.drop_policies:
        drop("Dropping the Global Security Policies (tags and roles stay)", DROP_POLICIES)
    elif a.add_product:
        add_product()
    elif a.verify:
        verify()
    elif a.audit:
        audit()
    elif a.teardown:
        drop("TEARDOWN: dropping every object of the demo", TEARDOWN)
    else:
        sys.exit(1 if deploy() else 0)
