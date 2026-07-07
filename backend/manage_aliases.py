#!/usr/bin/env python3
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.services.player_service import PlayerService
from app.models import PlayerAlias, Player


def add_alias(args):
    db = SessionLocal()
    try:
        alias = PlayerService.add_alias(
            db,
            args.source,
            args.target,
            exclude_1v1=not args.allow_1v1,
            min_players=args.min_players,
        )
        print(f"✅ Added alias: {alias.source_name} -> {args.target}")
        print(
            f"   Settings: exclude_1v1={bool(alias.exclude_1v1)}, min_players={alias.min_players}"
        )
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


def list_aliases(args):
    db = SessionLocal()
    try:
        aliases = db.query(PlayerAlias).all()
        if not aliases:
            print("No aliases found.")
            return

        print(
            f"{'Source Name':<20} | {'Target Player':<20} | {'Exclude 1v1':<12} | {'Min Players':<12}"
        )
        print("-" * 75)
        for a in aliases:
            target_name = a.target_player.name if a.target_player else "Unknown"
            print(
                f"{a.source_name:<20} | {target_name:<20} | {bool(a.exclude_1v1):<12} | {a.min_players:<12}"
            )
    finally:
        db.close()


def delete_alias(args):
    db = SessionLocal()
    try:
        alias = (
            db.query(PlayerAlias).filter(PlayerAlias.source_name == args.source).first()
        )
        if not alias:
            print(f"❌ Alias '{args.source}' not found.")
            return

        db.delete(alias)
        db.commit()
        print(f"✅ Deleted alias for '{args.source}'.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Manage Player Aliases")
    subparsers = parser.add_subparsers(dest="command")

    add_p = subparsers.add_parser("add", help="Add a new alias")
    add_p.add_argument("source", help="The name appearing in replays (e.g. barcode)")
    add_p.add_argument("target", help="The canonical player name in the system")
    add_p.add_argument(
        "--allow-1v1", action="store_true", help="Allow mapping even for 1v1 games"
    )
    add_p.add_argument(
        "--min-players",
        type=int,
        default=4,
        help="Minimum players required for mapping (default 4)",
    )

    subparsers.add_parser("list", help="List all aliases")

    del_p = subparsers.add_parser("delete", help="Delete an alias")
    del_p.add_argument("source", help="The source name to remove")

    args = parser.parse_args()

    if args.command == "add":
        add_alias(args)
    elif args.command == "list":
        list_aliases(args)
    elif args.command == "delete":
        delete_alias(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
