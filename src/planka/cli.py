#!/usr/bin/env python3
import argparse
import json
import sys
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


def resolve_card(client, board_id, card_ref, scope_list=None, board_data=None):
    """Resolve card by ID, exact name, or unique partial name match.

    Raises SystemExit with a list of candidates if the partial match is ambiguous,
    preventing silent wrong-card edits (issue #4).

    scope_list: if set, only search within that list name (further disambiguation).
    board_data: pre-fetched board data to avoid re-fetching in bulk ops.
    """
    data = board_data if board_data is not None else get_board_data(client, board_id)
    cards = data.get("included", {}).get("cards", [])
    lists = {l["id"]: l["name"] for l in data.get("included", {}).get("lists", [])}

    if scope_list:
        scope_list_id = None
        for lid, lname in lists.items():
            if lname == scope_list or str(lid) == scope_list:
                scope_list_id = lid
                break
        if not scope_list_id:
            raise SystemExit(f"List not found (for --in scope): {scope_list}")
        cards = [c for c in cards if c.get("listId") == scope_list_id]

    # 1. Exact match by ID or full name
    for c in cards:
        if str(c.get("id")) == card_ref or c.get("name") == card_ref:
            return c["id"]

    # 2. Partial match (case-insensitive)
    lower = card_ref.lower()
    matches = [c for c in cards if lower in c.get("name", "").lower()]

    if not matches:
        raise SystemExit(f"Card not found: {card_ref}")
    if len(matches) > 1:
        lines = [f"  [{c['id']}] {c['name']}  ({lists.get(c.get('listId'), '?')})"
                 for c in matches]
        raise SystemExit(
            f"Ambiguous match: {len(matches)} cards found for '{card_ref}'\n"
            + "\n".join(lines)
            + "\nRefine the substring, pass the full id, or use --in <list> to scope."
        )
    return matches[0]["id"]


def _resolve_label_in(board_data, label_ref):
    """Resolve label against pre-fetched board data."""
    labels = board_data.get("included", {}).get("labels", [])
    for lb in labels:
        if str(lb.get("id")) == label_ref or lb.get("name") == label_ref:
            return lb

    lower = label_ref.lower()
    matches = [lb for lb in labels if lower in lb.get("name", "").lower()]

    if not matches:
        raise SystemExit(f"Label not found: {label_ref}")
    if len(matches) > 1:
        lines = [f"  [{lb['id']}] {lb['name']}" for lb in matches]
        raise SystemExit(
            f"Ambiguous match: {len(matches)} labels found for '{label_ref}'\n"
            + "\n".join(lines)
            + "\nUse the exact label name."
        )
    return matches[0]


def resolve_label(client, board_id, label_ref):
    """Resolve label by ID, exact name, or unique partial name match.

    Raises SystemExit with candidates on ambiguous match (issue #4).
    """
    return _resolve_label_in(get_board_data(client, board_id), label_ref)


def read_stdin_refs():
    """Read card refs from stdin. Accepts:
    - One ref per line (id or name)
    - JSON array of strings: ["id1", "id2"]
    - JSON array of objects with .id field: [{"id":"1"}, {"id":"2"}]
    Empty stdin returns [].
    """
    if sys.stdin.isatty():
        return []
    text = sys.stdin.read().strip()
    if not text:
        return []
    if text.lstrip().startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(item.get("id") if isinstance(item, dict) else item)
                        for item in data]
        except json.JSONDecodeError:
            pass
    return [line.strip() for line in text.splitlines() if line.strip()]


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
    client.post(f"/api/boards/{board_id}/lists", {"name": args.name, "position": 65536})
    console.print(f"[green]✅ List '{args.name}' created[/green]")


def cards_list(client, args):
    board_id = resolve_board_id(client, args.board)
    list_id = resolve_list_id(client, board_id, args.list)
    cards = [c for c in get_board_data(client, board_id).get("included", {}).get("cards", [])
             if c.get("listId") == list_id]
    output([{"name": c["name"], "id": c["id"], "type": c.get("type", "")} for c in cards], args)


def cards_create(client, args):
    board_id = resolve_board_id(client, args.board)
    list_id = resolve_list_id(client, board_id, args.list)
    result = client.post(f"/api/lists/{list_id}/cards",
                         {"name": args.name, "type": args.type, "position": 65536})
    output([result.get("item", result)], args)


def cards_get(client, args):
    """Fetch a single card with full detail: description, labels, members, due date.

    Resolves labels/members against board data (the card endpoint only returns
    ids), so the output is human-readable (issue #8).
    """
    board_id = resolve_board_id(client, args.board)
    board_data = get_board_data(client, board_id)
    card_id = resolve_card(client, board_id, args.card,
                           scope_list=getattr(args, "in_list", None), board_data=board_data)

    detail = client.get(f"/api/cards/{card_id}")
    item = detail.get("item", {})
    included = detail.get("included", {})

    label_names = {l["id"]: l.get("name", "") for l in board_data.get("included", {}).get("labels", [])}
    list_names = {l["id"]: l.get("name", "") for l in board_data.get("included", {}).get("lists", [])}
    labels = [label_names.get(cl.get("labelId"), cl.get("labelId"))
              for cl in included.get("cardLabels", [])]

    users = {u["id"]: (u.get("name") or u.get("username") or u["id"])
             for u in included.get("users", [])}
    members = [users.get(m.get("userId"), m.get("userId"))
               for m in included.get("cardMemberships", [])]

    result = {
        "name": item.get("name", ""),
        "id": item.get("id", ""),
        "list": list_names.get(item.get("listId"), item.get("listId", "")),
        "type": item.get("type", ""),
        "dueDate": item.get("dueDate") or "",
        "labels": ", ".join(labels),
        "members": ", ".join(members),
        "description": item.get("description") or "",
    }
    output([result], args)


def cards_update(client, args):
    board_id = resolve_board_id(client, args.board)
    card_id = resolve_card(client, board_id, args.card, scope_list=getattr(args, "in_list", None))
    payload = {k: v for k, v in vars(args).items() if v and k in ["name", "description"]}
    if args.due:
        payload["dueDate"] = args.due
    result = client.patch(f"/api/cards/{card_id}", payload)
    output([result.get("item", result)], args)


def _resolve_card_refs(args):
    """Return list of card refs from either stdin or positional arg."""
    if getattr(args, "stdin", False):
        refs = read_stdin_refs()
        if not refs:
            raise SystemExit("--stdin given but no card refs found on stdin")
        return refs
    if not getattr(args, "card", None):
        raise SystemExit("Card required (positional arg or --stdin)")
    return [args.card]


def _foreach(refs, op, *, on_error="continue"):
    """Run op(ref) for each ref. on_error='continue' logs and proceeds,
    'stop' raises after the first failure."""
    failures = 0
    for ref in refs:
        try:
            op(ref)
        except SystemExit as e:
            failures += 1
            console.print(f"[red]✗ {ref}: {e}[/red]")
            if on_error == "stop":
                raise
        except Exception as e:
            failures += 1
            console.print(f"[red]✗ {ref}: {e}[/red]")
            if on_error == "stop":
                raise
    if failures:
        console.print(f"[yellow]Completed with {failures} failures[/yellow]")
        sys.exit(1)


def _resolve_label_arg(args):
    """Resolve label reference from positional or --label flag. --stdin requires --label."""
    label_ref = getattr(args, "label_flag", None) or getattr(args, "label", None)
    if not label_ref:
        if getattr(args, "stdin", False):
            raise SystemExit("--stdin mode requires --label <name> (positional label is ambiguous in stdin mode)")
        raise SystemExit("Label required (positional arg or --label)")
    return label_ref


def _resolve_list_arg(args):
    """Resolve target list reference from positional or --to flag. --stdin requires --to."""
    list_ref = getattr(args, "to_list", None) or getattr(args, "list", None)
    if not list_ref:
        if getattr(args, "stdin", False):
            raise SystemExit("--stdin mode requires --to <list> for move")
        raise SystemExit("List required (positional arg or --to)")
    return list_ref


def cards_move(client, args):
    board_id = resolve_board_id(client, args.board)
    board_data = get_board_data(client, board_id)
    list_id = resolve_list_id(client, board_id, _resolve_list_arg(args))
    refs = _resolve_card_refs(args)
    in_list = getattr(args, "in_list", None)

    def op(ref):
        card_id = resolve_card(client, board_id, ref, scope_list=in_list, board_data=board_data)
        client.patch(f"/api/cards/{card_id}", {"listId": list_id, "position": 65535})
        console.print(f"[green]→ {ref} moved[/green]")
    _foreach(refs, op)


def cards_delete(client, args):
    board_id = resolve_board_id(client, args.board)
    board_data = get_board_data(client, board_id)
    refs = _resolve_card_refs(args)
    in_list = getattr(args, "in_list", None)

    def op(ref):
        card_id = resolve_card(client, board_id, ref, scope_list=in_list, board_data=board_data)
        client.delete(f"/api/cards/{card_id}")
        console.print(f"[red]🗑️ {ref} deleted[/red]")
    _foreach(refs, op)


def cards_tag(client, args):
    board_id = resolve_board_id(client, args.board)
    board_data = get_board_data(client, board_id)
    label = _resolve_label_in(board_data, _resolve_label_arg(args))
    refs = _resolve_card_refs(args)
    in_list = getattr(args, "in_list", None)
    import requests as req

    def op(ref):
        card_id = resolve_card(client, board_id, ref, scope_list=in_list, board_data=board_data)
        try:
            client.post(f"/api/cards/{card_id}/card-labels", {"labelId": label["id"]})
            console.print(f"[green]🏷️ '{label['name']}' → {ref}[/green]")
        except req.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                console.print(f"[yellow]🏷️ '{label['name']}' already on {ref}[/yellow]")
            else:
                raise
    _foreach(refs, op)


def cards_untag(client, args):
    board_id = resolve_board_id(client, args.board)
    board_data = get_board_data(client, board_id)
    label = _resolve_label_in(board_data, _resolve_label_arg(args))
    refs = _resolve_card_refs(args)
    in_list = getattr(args, "in_list", None)

    def op(ref):
        card_id = resolve_card(client, board_id, ref, scope_list=in_list, board_data=board_data)
        # Planka route: DELETE /api/cards/:cardId/card-labels/labelId::labelId
        client.delete(f"/api/cards/{card_id}/card-labels/labelId:{label['id']}")
        console.print(f"[red]🏷️ '{label['name']}' off {ref}[/red]")
    _foreach(refs, op)


def cards_comment(client, args):
    """Post a comment on a card. Text from arg, --file, or stdin."""
    board_id = resolve_board_id(client, args.board)
    card_id = resolve_card(client, board_id, args.card, scope_list=getattr(args, "in_list", None))

    text = args.text
    if args.file:
        with open(args.file) as f:
            text = f.read()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read()
    if not text:
        raise SystemExit("No comment text. Pass as positional arg, --file <path>, or pipe via stdin.")

    result = client.post(f"/api/cards/{card_id}/comments", {"text": text})
    item = result.get("item", result)
    console.print(f"[green]💬 Comment posted (id={item.get('id')})[/green]")


def cards_comments(client, args):
    """List comments on a card."""
    board_id = resolve_board_id(client, args.board)
    card_id = resolve_card(client, board_id, args.card, scope_list=getattr(args, "in_list", None))
    data = client.get(f"/api/cards/{card_id}/comments")
    comments = data.get("items", [])
    comments.sort(key=lambda c: c.get("createdAt") or "")
    rows = [{
        "id": c["id"],
        "createdAt": c.get("createdAt", ""),
        "text": (c.get("text") or "").replace("\n", " ")[:120]
    } for c in comments]
    output(rows, args)


def login(client, args):
    client.login()
    console.print("[green]✅ Login successful[/green]")


def add_flags(p):
    p.add_argument("--output", "-o", choices=["table", "json", "yaml"], default="table")
    p.add_argument("--jq", help="jq filter")


def add_scope_flag(p):
    """Add --in <list> for card-resolution scoping (issue #4)."""
    p.add_argument("--in", dest="in_list", metavar="LIST",
                   help="Scope card name lookup to this list (helps disambiguate)")


def add_bulk_flag(p):
    """Add --stdin for bulk operations reading card refs from stdin (issue #3)."""
    p.add_argument("--stdin", action="store_true",
                   help="Read card refs from stdin (one per line or JSON array)")


def main():
    parser = argparse.ArgumentParser(prog="planka", description="Planka CLI v4.4")
    sub = parser.add_subparsers(dest="resource")
    sub.add_parser("login").set_defaults(func=login)

    # Boards
    b = sub.add_parser("boards")
    bs = b.add_subparsers(dest="action")
    l = bs.add_parser("list"); l.set_defaults(func=boards_list); add_flags(l)
    c = bs.add_parser("create"); c.add_argument("name"); c.set_defaults(func=boards_create); add_flags(c)

    # Lists
    lis = sub.add_parser("lists")
    liss = lis.add_subparsers(dest="action")
    ll = liss.add_parser("list"); ll.add_argument("board")
    ll.set_defaults(func=lists_list); add_flags(ll)
    lc = liss.add_parser("create"); lc.add_argument("board"); lc.add_argument("name")
    lc.set_defaults(func=lists_create); add_flags(lc)

    # Cards
    cs = sub.add_parser("cards")
    css = cs.add_subparsers(dest="action")

    cl = css.add_parser("list")
    cl.add_argument("board"); cl.add_argument("list")
    cl.set_defaults(func=cards_list); add_flags(cl)

    cc = css.add_parser("create")
    cc.add_argument("board"); cc.add_argument("list"); cc.add_argument("name")
    cc.add_argument("--type", default="project")
    cc.set_defaults(func=cards_create); add_flags(cc)

    cg = css.add_parser("get", help="Show a single card's full detail (description, labels, members)")
    cg.add_argument("board"); cg.add_argument("card")
    cg.set_defaults(func=cards_get); add_flags(cg); add_scope_flag(cg)

    cu = css.add_parser("update")
    cu.add_argument("board"); cu.add_argument("card")
    cu.add_argument("--name"); cu.add_argument("--description"); cu.add_argument("--due")
    cu.set_defaults(func=cards_update); add_flags(cu); add_scope_flag(cu)

    cmd_mv = css.add_parser("move")
    cmd_mv.add_argument("card", nargs="?", help="card ref (omit with --stdin)")
    cmd_mv.add_argument("board")
    cmd_mv.add_argument("list", nargs="?", help="target list (or use --to with --stdin)")
    cmd_mv.add_argument("--to", dest="to_list", help="Target list (alternative to positional; required with --stdin)")
    cmd_mv.set_defaults(func=cards_move); add_flags(cmd_mv); add_scope_flag(cmd_mv); add_bulk_flag(cmd_mv)

    cmd_del = css.add_parser("delete")
    cmd_del.add_argument("board"); cmd_del.add_argument("card", nargs="?")
    cmd_del.set_defaults(func=cards_delete); add_flags(cmd_del); add_scope_flag(cmd_del); add_bulk_flag(cmd_del)

    cmd_tag = css.add_parser("tag")
    cmd_tag.add_argument("board")
    cmd_tag.add_argument("card", nargs="?", help="card ref (omit with --stdin)")
    cmd_tag.add_argument("label", nargs="?", help="label name (or use --label with --stdin)")
    cmd_tag.add_argument("--label", dest="label_flag", help="Label name (required with --stdin)")
    cmd_tag.set_defaults(func=cards_tag); add_flags(cmd_tag); add_scope_flag(cmd_tag); add_bulk_flag(cmd_tag)

    cmd_untag = css.add_parser("untag")
    cmd_untag.add_argument("board")
    cmd_untag.add_argument("card", nargs="?", help="card ref (omit with --stdin)")
    cmd_untag.add_argument("label", nargs="?", help="label name (or use --label with --stdin)")
    cmd_untag.add_argument("--label", dest="label_flag", help="Label name (required with --stdin)")
    cmd_untag.set_defaults(func=cards_untag); add_flags(cmd_untag); add_scope_flag(cmd_untag); add_bulk_flag(cmd_untag)

    cmd_cmt = css.add_parser("comment", help="Post a comment on a card")
    cmd_cmt.add_argument("board"); cmd_cmt.add_argument("card")
    cmd_cmt.add_argument("text", nargs="?", default=None,
                         help="Comment text (omit to read from --file or stdin)")
    cmd_cmt.add_argument("--file", help="Read comment text from this file")
    cmd_cmt.set_defaults(func=cards_comment); add_flags(cmd_cmt); add_scope_flag(cmd_cmt)

    cmd_cmts = css.add_parser("comments", help="List comments on a card")
    cmd_cmts.add_argument("board"); cmd_cmts.add_argument("card")
    cmd_cmts.set_defaults(func=cards_comments); add_flags(cmd_cmts); add_scope_flag(cmd_cmts)

    # Labels
    lb = sub.add_parser("labels")
    lbs = lb.add_subparsers(dest="action")
    lb_list = lbs.add_parser("list"); lb_list.add_argument("board")
    lb_list.set_defaults(func=labels_list); add_flags(lb_list)
    lb_create = lbs.add_parser("create")
    lb_create.add_argument("board"); lb_create.add_argument("name")
    lb_create.add_argument("--color", default=None)
    lb_create.set_defaults(func=labels_create); add_flags(lb_create)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    client = PlankaClient()
    args.func(client, args)


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
    data = get_board_data(client, board_id)
    used = {l.get("color") for l in data.get("included", {}).get("labels", [])}
    color = args.color or next((c for c in colors if c not in used), "lagoon-blue")
    result = client.post(f"/api/boards/{board_id}/labels", {
        "name": args.name, "color": color, "position": 65536
    })
    item = result.get("item", result)
    console.print(f"[green]✅ Label '{item.get('name')}' created ({item.get('color')})[/green]")


if __name__ == "__main__":
    main()
