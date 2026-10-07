#!/usr/bin/env python3
"""Bootstrap the Zettel GitHub repo and GitHub Project from tickets.json.

Creates (idempotently, safe to re-run):
  * labels                      (type:*)
  * milestones                  (M1 … M4)
  * issues                      (Z-01 … Z-65 plus backlog ideas)
  * a GitHub Project "Zettel"   (Projects v2, linked to the repo)
      - fields: Status, Sprint (iteration), Size, Area
      - every issue added with its field values

Requirements: gh CLI, logged in with the `repo` and `project` scopes:
    gh auth login
    gh auth refresh -s project

Usage:
    python3 scripts/github/bootstrap.py                 # everything
    python3 scripts/github/bootstrap.py --skip-project  # labels, milestones, issues only
    python3 scripts/github/bootstrap.py --only-project  # project only (issues must exist)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
DATA = json.loads((HERE / "tickets.json").read_text(encoding="utf-8"))

PROJECT_TITLE = "Zettel"
STATUS_OPTIONS = [
    ("Backlog", "GRAY", "Ideas and work without a sprint"),
    ("Todo", "BLUE", "Planned for a sprint"),
    ("In Progress", "YELLOW", "Being worked on"),
    ("In Review", "PURPLE", "PR open"),
    ("Done", "GREEN", "Merged and demonstrated"),
]
SIZE_OPTIONS = [("S", "GREEN", "≈ 1 hour"), ("M", "YELLOW", "2–3 hours")]
AREA_COLORS = ["GRAY", "BLUE", "PURPLE", "GREEN", "ORANGE", "YELLOW",
               "RED", "PINK", "GRAY", "BLUE", "GREEN", "ORANGE"]
PAUSE = 0.7  # seconds between write calls, stays clear of secondary rate limits


# --------------------------------------------------------------------------- gh helpers

def gh(*args: str, input_: str | None = None, check: bool = True) -> str:
    res = subprocess.run(["gh", *args], input=input_, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} … failed:\n{res.stderr.strip()}")
    return res.stdout


def rest(method: str, path: str, body: dict | None = None) -> object:
    args = ["api", "-X", method, path, "-H", "Accept: application/vnd.github+json"]
    out = gh(*args, "--input", "-", input_=json.dumps(body)) if body is not None else gh(*args)
    return json.loads(out) if out.strip() else None


def rest_paginated(path: str) -> list:
    out = gh("api", "--paginate", "--slurp", path)
    pages = json.loads(out)
    return [item for page in pages for item in page]


def gql(query: str, **variables) -> dict:
    out = gh("api", "graphql", "--input", "-",
             input_=json.dumps({"query": query, "variables": variables}))
    data = json.loads(out)
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]


# --------------------------------------------------------------------------- repo part

def plan_link(repo: str, section: str) -> str:
    return f"https://github.com/{repo}/blob/main/docs/PLAN.md#{section}"


def ticket_body(repo: str, t: dict, sprint_title: str) -> str:
    done = "\n".join(f"- [ ] {d}" for d in t["done"])
    notes = f"\n## Notes\n\n{t['notes']}\n" if t["notes"] else ""
    return (
        f"## Goal\n\n{t['goal']}\n\n"
        f"## Done when\n\n{done}\n"
        f"{notes}\n"
        f"---\n"
        f"**Sprint:** {sprint_title} · **Size:** {t['size']} · **Area:** {t['area']}  \n"
        f"Plan: [{t['section']}]({plan_link(repo, t['section'])}) · "
        f"[Definition of Done]({plan_link(repo, 'tech-stack--conventions')})\n"
    )


def backlog_body(repo: str, b: dict) -> str:
    return (
        f"## Idea\n\n{b['notes']}\n\n"
        f"---\n**Area:** {b['area']} · Not scheduled. "
        f"See [Backlog & later ideas]({plan_link(repo, 'backlog--later-ideas')}).\n"
    )


def ensure_labels(repo: str) -> None:
    for lab in DATA["labels"]:
        gh("label", "create", lab["name"], "--repo", repo, "--color", lab["color"],
           "--description", lab["description"], "--force")
    print(f"labels: {len(DATA['labels'])} ensured")


def ensure_milestones(repo: str) -> dict[int, int]:
    """Returns sprint index -> milestone number."""
    existing = {m["title"]: m for m in rest_paginated(f"repos/{repo}/milestones?state=all&per_page=100")}
    by_sprint: dict[int, int] = {}
    for m in DATA["milestones"]:
        body = {"title": m["title"], "description": m["description"],
                "due_on": f"{m['due']}T23:59:59Z"}
        if m["title"] in existing:
            num = existing[m["title"]]["number"]
            rest("PATCH", f"repos/{repo}/milestones/{num}", body)
        else:
            num = rest("POST", f"repos/{repo}/milestones", body)["number"]
            time.sleep(PAUSE)
        for s in m["sprints"]:
            by_sprint[s] = num
    print(f"milestones: {len(DATA['milestones'])} ensured")
    return by_sprint


def existing_issues(repo: str) -> dict[str, dict]:
    items = rest_paginated(f"repos/{repo}/issues?state=all&per_page=100")
    return {i["title"]: i for i in items if "pull_request" not in i}


def ensure_issues(repo: str, milestones: dict[int, int]) -> None:
    have = existing_issues(repo)
    sprints = {s["index"]: s["title"] for s in DATA["sprints"]}
    created = 0
    for t in DATA["tickets"]:
        title = f"{t['id']}: {t['title']}"
        if title in have:
            continue
        rest("POST", f"repos/{repo}/issues", {
            "title": title,
            "body": ticket_body(repo, t, sprints[t["sprint"]]),
            "labels": [f"type:{t['type']}"],
            "milestone": milestones[t["sprint"]],
        })
        created += 1
        print(f"  created {title}")
        time.sleep(PAUSE)
    for b in DATA["backlog"]:
        title = f"Idea: {b['title']}"
        if title in have:
            continue
        rest("POST", f"repos/{repo}/issues", {
            "title": title, "body": backlog_body(repo, b), "labels": ["type:feature"],
        })
        created += 1
        print(f"  created {title}")
        time.sleep(PAUSE)
    print(f"issues: {created} created, {len(have)} already existed")


# --------------------------------------------------------------------------- project part

FIELDS_Q = """
query($id: ID!) {
  node(id: $id) {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
          ... on ProjectV2FieldCommon { id name dataType }
          ... on ProjectV2SingleSelectField { options { id name } }
          ... on ProjectV2IterationField {
            configuration { iterations { id title startDate } completedIterations { id title startDate } }
          }
        }
      }
    }
  }
}"""


def project_fields(pid: str) -> dict[str, dict]:
    nodes = gql(FIELDS_Q, id=pid)["node"]["fields"]["nodes"]
    return {n["name"]: n for n in nodes if n}


def select_options(opts) -> list[dict]:
    return [{"name": n, "color": c, "description": d} for n, c, d in opts]


def ensure_project(repo: str) -> str:
    owner, name = repo.split("/")
    d = gql("""query($o: String!, $n: String!) {
      repository(owner: $o, name: $n) { id }
      repositoryOwner(login: $o) {
        id
        ... on ProjectV2Owner { projectsV2(first: 100) { nodes { id title number url } } }
      }
    }""", o=owner, n=name)
    repo_id, owner_id = d["repository"]["id"], d["repositoryOwner"]["id"]
    project = next((p for p in d["repositoryOwner"]["projectsV2"]["nodes"]
                    if p["title"] == PROJECT_TITLE), None)
    if project is None:
        project = gql("""mutation($o: ID!, $r: ID!, $t: String!) {
          createProjectV2(input: {ownerId: $o, repositoryId: $r, title: $t}) {
            projectV2 { id number url }
          }
        }""", o=owner_id, r=repo_id, t=PROJECT_TITLE)["createProjectV2"]["projectV2"]
        print(f"project: created {project['url']}")
    else:
        print(f"project: exists {project['url']}")
        try:
            gql("""mutation($p: ID!, $r: ID!) {
              linkProjectV2ToRepository(input: {projectId: $p, repositoryId: $r}) { repository { id } }
            }""", p=project["id"], r=repo_id)
        except RuntimeError:
            pass  # already linked
    gql("""mutation($p: ID!, $d: String!, $r: String!) {
      updateProjectV2(input: {projectId: $p, shortDescription: $d, readme: $r}) { projectV2 { id } }
    }""", p=project["id"],
        d="Shared household shopping list – Go gRPC microservices, SwiftUI app, Kubernetes",
        r=(f"Sprint board for [{repo}](https://github.com/{repo}).\n\n"
           f"Plan: [docs/PLAN.md](https://github.com/{repo}/blob/main/docs/PLAN.md)\n\n"
           "Sprints are two weeks long (Sprint field). Sizes: S ≈ 1 h, M ≈ 2–3 h."))
    return project["id"]


def ensure_fields(pid: str) -> dict[str, dict]:
    fields = project_fields(pid)
    warnings = []

    # Status: replace the default options (Todo / In Progress / Done)
    status = fields.get("Status")
    want = [o[0] for o in STATUS_OPTIONS]
    if status and [o["name"] for o in status["options"]] != want:
        try:
            gql("""mutation($f: ID!, $o: [ProjectV2SingleSelectFieldOptionInput!]) {
              updateProjectV2Field(input: {fieldId: $f, singleSelectOptions: $o}) { projectV2Field { __typename } }
            }""", f=status["id"], o=select_options(STATUS_OPTIONS))
        except RuntimeError as e:
            warnings.append(f"Status options not updated ({e.__class__.__name__}); "
                            f"add 'Backlog' and 'In Review' by hand.")

    def ensure_select(name: str, opts):
        if name in fields:
            return
        gql("""mutation($p: ID!, $n: String!, $o: [ProjectV2SingleSelectFieldOptionInput!]) {
          createProjectV2Field(input: {projectId: $p, dataType: SINGLE_SELECT, name: $n, singleSelectOptions: $o}) {
            projectV2Field { __typename }
          }
        }""", p=pid, n=name, o=select_options(opts))

    ensure_select("Size", SIZE_OPTIONS)
    ensure_select("Area", [(a, AREA_COLORS[i % len(AREA_COLORS)], "") for i, a in enumerate(DATA["areas"])])

    if "Sprint" not in fields:
        iterations = [{"title": s["title"], "startDate": s["start"], "duration": s["duration_days"]}
                      for s in DATA["sprints"]]
        try:
            gql("""mutation($p: ID!, $c: ProjectV2IterationFieldConfigurationInput!) {
              createProjectV2Field(input: {projectId: $p, dataType: ITERATION, name: "Sprint", iterationConfiguration: $c}) {
                projectV2Field { __typename }
              }
            }""", p=pid, c={"startDate": DATA["sprints"][0]["start"], "duration": 14, "iterations": iterations})
        except RuntimeError as e:
            warnings.append("Sprint iteration field could not be created via the API:\n"
                            f"{e}\nCreate it by hand: field 'Sprint', type Iteration, 2 weeks, "
                            "start 2026-10-12, add a break 2026-12-21 – 2027-01-03, then re-run "
                            "with --only-project.")

    for w in warnings:
        print("WARNING:", w, file=sys.stderr)
    return project_fields(pid)


def option_id(field: dict | None, name: str) -> str | None:
    if not field:
        return None
    return next((o["id"] for o in field.get("options", []) if o["name"] == name), None)


def iteration_id(field: dict | None, start: str) -> str | None:
    if not field:
        return None
    cfg = field["configuration"]
    its = cfg["iterations"] + cfg["completedIterations"]
    return next((i["id"] for i in its if i["startDate"] == start), None)


SET_VALUE = """mutation($p: ID!, $i: ID!, $f: ID!, $v: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(input: {projectId: $p, itemId: $i, fieldId: $f, value: $v}) {
    projectV2Item { id }
  }
}"""


def set_select(pid, item, field, name):
    oid = option_id(field, name)
    if oid:
        gql(SET_VALUE, p=pid, i=item, f=field["id"], v={"singleSelectOptionId": oid})


def populate(repo: str, pid: str, fields: dict[str, dict]) -> None:
    have = existing_issues(repo)
    sprint_start = {s["index"]: s["start"] for s in DATA["sprints"]}
    rows = [(f"{t['id']}: {t['title']}", "Todo", t["size"], t["area"], sprint_start[t["sprint"]])
            for t in DATA["tickets"]]
    rows += [(f"Idea: {b['title']}", "Backlog", None, b["area"], None) for b in DATA["backlog"]]

    for title, status, size, area, start in rows:
        issue = have.get(title)
        if not issue:
            print(f"  skip (no issue): {title}", file=sys.stderr)
            continue
        item = gql("""mutation($p: ID!, $c: ID!) {
          addProjectV2ItemById(input: {projectId: $p, contentId: $c}) { item { id } }
        }""", p=pid, c=issue["node_id"])["addProjectV2ItemById"]["item"]["id"]
        set_select(pid, item, fields.get("Status"), status)
        set_select(pid, item, fields.get("Area"), area)
        if size:
            set_select(pid, item, fields.get("Size"), size)
        if start:
            iid = iteration_id(fields.get("Sprint"), start)
            if iid:
                gql(SET_VALUE, p=pid, i=item, f=fields["Sprint"]["id"], v={"iterationId": iid})
        print(f"  project item: {title}")
        time.sleep(PAUSE / 2)


# --------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default="timkrebs/zettel")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--skip-project", action="store_true")
    g.add_argument("--only-project", action="store_true")
    args = ap.parse_args()

    if not args.only_project:
        ensure_labels(args.repo)
        ms = ensure_milestones(args.repo)
        ensure_issues(args.repo, ms)
    if not args.skip_project:
        pid = ensure_project(args.repo)
        fields = ensure_fields(pid)
        populate(args.repo, pid, fields)
    print("done")


if __name__ == "__main__":
    main()
