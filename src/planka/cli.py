#!/usr/bin/env python3
import argparse
import json
import yaml
import jq
from rich.console import Console
from rich.table import Table
from .client import PlankaClient

console = Console()

def apply_jq(data, jq_filter):
    if not jq_filter:
        return data
    return jq.compile(jq_filter).input(data).all()

def to_table(data):
    if isinstance(data, dict):
        data = [data]
    if not data:
        console.print("[dim]No data[/dim]")
        return
    # Priority columns for table view
    priority = ["project", "board", "name", "description", "id", "list", "dueDate", "type"]
    keys = []
    seen = set()
    for col in priority:
        for row in data:
            if col in row and col not in seen:
                keys.append(col)
                seen.add(col)
    for row in data:
        for k in row:
            if k not in seen:
                keys.append(k)
                seen.add(k)
    table = Table(show_lines=False)
    for k in keys:
        table.add_column(str(k))
    for row in data:
        table.add_row(*[str(row.get(k, "")) for k in keys])
    console.print(table)

def output(data, args):
    data = apply_jq(data, args.jq)
    if args.output == "json":
        print(json.dumps(data, indent=2))
    elif args.output == "yaml":
        print(yaml.safe_dump(data, sort_keys=False))
    else:
        to_table(data)

def get_all_boards(client):
    data = client.get("/api/projects")
    return data.get("included", {}).get("boards", []) if isinstance(data, dict) else data

def resolve_board_id(client, board):
    for b in get_all_boards(client):
        if isinstance(b, dict) and (str(b.get("id")) == board or b.get("name") == board):
            return b["id"]
    raise SystemExit(f"Board not found: {board}")

def get_board_data(client, board_id):
    return client.get(f"/api/boards/{board_id}")

def resolve_list_id(client, board_id, list_name):
    data = get_board_data(client, board_id)
    lists = data.get("included", {}).get("lists", [])
    for l in lists:
        if isinstance(l, dict) and (str(l.get("id")) == list_name or l.get("name") == list_name):
            return l["id"]
    raise SystemExit(f"List not found: {list_name}")

def resolve_card(client, board_id, card_ref):
    data = get_board_data(client, board_id)
    cards = data.get("included", {}).get("cards", [])
    for c in cards:
        if str(c.get("id")) == card_ref or c.get("name") == card_ref:
            return c["id"]
    lower = card_ref.lower()
    for c in cards:
        if lower in c.get("name", "").lower():
            return c["id"]
    raise SystemExit(f"Card not found: {card_ref}")

def boards_list(client, args):
    data = client.get("/api/projects")
    if isinstance(data, dict):
        projects = data.get("items", [])
        boards = data.get("included", {}).get("boards", [])
        rows = [{"project": p["name"], "board": b["name"], "id": b["id"]}
                for p in projects for b in boards if b.get("projectId") == p["id"]]
        output(rows, args)
    else:
        output(data, args)

def boards_create(client, args):
    result = client.post("/api/projects", {"name": args.name})
    output([result.get("item", result)], args)

def lists_list(client, args):
    board_id = resolve_board_id(client, args.board)
    data = get_board_data(client, board_id)
    lists = [l for l in data.get("included", {}).get("lists", []) if l.get("name")]
    lists.sort(key=lambda x: x.get("position") or 0)
    output([{"name": l["name"], "id": l["id"]} for l in lists], args)

def lists_create(client, args):
    board_id = resolve_board_id(client, args.board)
    result = client.post(f"/api/boards/{board_id}/lists", {"name": args.name, "position": 65536})
    console.print(f"[green]✅ List '{args.name}' created[/green]")

def cards_list(client, args):
    board_id = resolve_board_id(client, args.board)
    list_id = resolve_list_id(client, board_id, args.list)
    cards = [c for c in get_board_data(client, board_id).get("included", {}).get("cards", []) if c.get("listId") == list_id]
    output([{"name": c["name"], "id": c["id"], "type": c.get("type", "")} for c in cards], args)

def cards_create(client, args):
    board_id = resolve_board_id(client, args.board)
    list_id = resolve_list_id(client, board_id, args.list)
    result = client.post(f"/api/lists/{list_id}/cards", {"name": args.name, "type": args.type, "position": 65536})
    output([result.get("item", result)], args)

def cards_update(client, args):
    board_id = resolve_board_id(client, args.board)
    card_id = resolve_card(client, board_id, args.card)
    payload = {k: v for k, v in vars(args).items() if v and k in ["name", "description"]}
    if args.due: payload["dueDate"] = args.due
    result = client.patch(f"/api/cards/{card_id}", payload)
    output([result.get("item", result)], args)

def cards_move(client, args):
    board_id = resolve_board_id(client, args.board)
    card_id = resolve_card(client, board_id, args.card)
    list_id = resolve_list_id(client, board_id, args.list)
    result = client.patch(f"/api/cards/{card_id}", {"listId": list_id, "position": 65535})
    output([result.get("item", result)], args)

def cards_delete(client, args):
    board_id = resolve_board_id(client, args.board)
    card_id = resolve_card(client, board_id, args.card)
    result = client.delete(f"/api/cards/{card_id}")
    console.print(f"[red]🗑️ Deleted card {card_id}[/red]")


# ── Labels ─────────────────────────────────────────────────

def resolve_label(client, board_id, label_ref):
    """Resolve label by ID or name (case-insensitive partial match)."""
    data = get_board_data(client, board_id)
    labels = data.get("included", {}).get("labels", [])
    for lb in labels:
        if str(lb.get("id")) == label_ref or lb.get("name") == label_ref:
            return lb
    lower = label_ref.lower()
    for lb in labels:
        if lower in lb.get("name", "").lower():
            return lb
    raise SystemExit(f"Label not found: {label_ref}")


def labels_list(client, args):
    board_id = resolve_board_id(client, args.board)
    data = get_board_data(client, board_id)
    labels = data.get("included", {}).get("labels", [])
    output([{"name": l["name"], "color": l.get("color", ""), "id": l["id"]}
            for l in sorted(labels, key=lambda x: x.get("position") or 0)], args)


def labels_create(client, args):
    board_id = resolve_board_id(client, args.board)
    colors = ["lagoon-blue", "berry-red", "egg-yellow", "modern-green", "morning-sky",
              "pumpkin-orange", "pink-tulip", "sweet-lilac", "midnight-blue", "antique-blue"]
    # Pick a color that's not yet used
    data = get_board_data(client, board_id)
    used = {l.get("color") for l in data.get("included", {}).get("labels", [])}
    color = args.color or next((c for c in colors if c not in used), "lagoon-blue")
    result = client.post(f"/api/boards/{board_id}/labels", {
        "name": args.name, "color": color, "position": 65536
    })
    item = result.get("item", result)
    console.print(f"[green]✅ Label '{item.get('name')}' created ({item.get('color')})[/green]")


def cards_tag(client, args):
    board_id = resolve_board_id(client, args.board)
    card_id = resolve_card(client, board_id, args.card)
    label = resolve_label(client, board_id, args.label)
    import requests as req
    try:
        result = client.post(f"/api/cards/{card_id}/card-labels", {"labelId": label["id"]})
        console.print(f"[green]🏷️ '{label['name']}' → Karte zugewiesen[/green]")
    except req.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            console.print(f"[yellow]🏷️ '{label['name']}' war bereits zugewiesen[/yellow]")
        else:
            raise


def cards_untag(client, args):
    board_id = resolve_board_id(client, args.board)
    card_id = resolve_card(client, board_id, args.card)
    label = resolve_label(client, board_id, args.label)
    # Planka route: DELETE /api/cards/:cardId/card-labels/labelId::labelId
    client.delete(f"/api/cards/{card_id}/card-labels/labelId:{label['id']}")
    console.print(f"[red]🏷️ '{label['name']}' von Karte entfernt[/red]")

def login(client, args):
    client.login()
    console.print("[green]✅ Login successful[/green]")

def main():
    parser = argparse.ArgumentParser(prog="planka", description="Planka CLI v4")
    sub = parser.add_subparsers(dest="resource")
    sub.add_parser("login").set_defaults(func=login)
    
    # Boards
    b = sub.add_parser("boards")
    bs = b.add_subparsers(dest="action")
    l = bs.add_parser("list")
    l.set_defaults(func=boards_list)
    add_flags(l)
    c = bs.add_parser("create")
    c.add_argument("name")
    c.set_defaults(func=boards_create)
    add_flags(c)

    # Lists
    lis = sub.add_parser("lists")
    liss = lis.add_subparsers(dest="action")
    ll = liss.add_parser("list")
    ll.add_argument("board")
    ll.set_defaults(func=lists_list)
    add_flags(ll)
    lc = liss.add_parser("create")
    lc.add_argument("board"); lc.add_argument("name"); lc.set_defaults(func=lists_create); add_flags(lc)

    # Cards
    cs = sub.add_parser("cards")
    css = cs.add_subparsers(dest="action")
    cl = css.add_parser("list")
    cl.add_argument("board"); cl.add_argument("list"); cl.set_defaults(func=cards_list); add_flags(cl)
    cc = css.add_parser("create")
    cc.add_argument("board"); cc.add_argument("list"); cc.add_argument("name")
    cc.add_argument("--type", default="project")
    cc.set_defaults(func=cards_create); add_flags(cc)
    
    # NEU: Update & Move registriert
    cu = css.add_parser("update")
    cu.add_argument("board"); cu.add_argument("card"); cu.set_defaults(func=cards_update); add_flags(cu)
    cu.add_argument("--name"); cu.add_argument("--description"); cu.add_argument("--due")

    cmd_mv = css.add_parser("move")
    cmd_mv.add_argument("card"); cmd_mv.add_argument("board"); cmd_mv.add_argument("list")
    cmd_mv.set_defaults(func=cards_move); add_flags(cmd_mv)

    cmd_del = css.add_parser("delete")
    cmd_del.add_argument("board"); cmd_del.add_argument("card")
    cmd_del.set_defaults(func=cards_delete); add_flags(cmd_del)

    cmd_tag = css.add_parser("tag")
    cmd_tag.add_argument("board"); cmd_tag.add_argument("card"); cmd_tag.add_argument("label")
    cmd_tag.set_defaults(func=cards_tag); add_flags(cmd_tag)

    cmd_untag = css.add_parser("untag")
    cmd_untag.add_argument("board"); cmd_untag.add_argument("card"); cmd_untag.add_argument("label")
    cmd_untag.set_defaults(func=cards_untag); add_flags(cmd_untag)

    # Labels
    lb = sub.add_parser("labels")
    lbs = lb.add_subparsers(dest="action")
    lb_list = lbs.add_parser("list")
    lb_list.add_argument("board"); lb_list.set_defaults(func=labels_list); add_flags(lb_list)
    lb_create = lbs.add_parser("create")
    lb_create.add_argument("board"); lb_create.add_argument("name")
    lb_create.add_argument("--color", default=None)
    lb_create.set_defaults(func=labels_create); add_flags(lb_create)

    args = parser.parse_args()
    client = PlankaClient()
    args.func(client, args)

def add_flags(p):
    p.add_argument("--output", "-o", choices=["table", "json", "yaml"], default="table")
    p.add_argument("--jq", help="jq filter")

if __name__ == "__main__":
    main()
