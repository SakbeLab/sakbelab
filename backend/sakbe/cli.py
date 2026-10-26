"""`sakbe` command line interface (placeholder for Phase 1)."""

import argparse

from sakbe import __version__


def main() -> None:
    parser = argparse.ArgumentParser(prog="sakbe", description="SakbeLab CLI")
    parser.add_argument("--version", action="version", version=f"sakbe {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("deploy", help="Create and start a lab from a YAML or .sakbe file")
    sub.add_parser("destroy", help="Stop and delete a lab")
    sub.add_parser("export", help="Export a lab as a .sakbe file")
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
    else:
        print(f"'{args.command}' is not implemented yet (planned for MVP 0.1).")


if __name__ == "__main__":
    main()
