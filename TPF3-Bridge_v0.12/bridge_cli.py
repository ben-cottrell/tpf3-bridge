"""Local corridor design and optional in-memory mock execution; no game writes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import bridge_app


def emit(summary):
    compact = json.dumps(summary, separators=(',', ':'), ensure_ascii=True)
    if len(compact.encode('utf-8')) >= 4096:
        summary = {**summary, 'paths': {name: name for name in summary['paths']},
                   'paths_relative_to': 'caller-selected output directory'}
        compact = json.dumps(summary, separators=(',', ':'), ensure_ascii=True)
    print(compact)
    return 0 if summary['status'] in (*bridge_app.SUCCESS, 'integrity_verified') else 1


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
        design = commands.add_parser('design')
        design.add_argument('--fixture', required=True, type=Path)
        design.add_argument('--output', required=True, type=Path)
        design.add_argument('--mock-execute', action='store_true')
        connect = commands.add_parser('connect')
        connect.add_argument('--input', required=True, type=Path)
        connect.add_argument('--output', required=True, type=Path)
        pair = commands.add_parser('connect-pair')
        pair.add_argument('--input', required=True, type=Path)
        pair.add_argument('--output', required=True, type=Path)
        pair.add_argument('--mock-execute', action='store_true')
        pair.add_argument('--snapshot', type=Path)
        status = commands.add_parser('status')
        status.add_argument('--run', required=True, type=Path)
        verify = commands.add_parser('verify')
        verify.add_argument('--run', required=True, type=Path)
        args = parser.parse_args(argv)
    except ValueError as exc:
        summary = bridge_app.initial_summary()
        summary['blockers'] = [str(exc)[:400]]
    else:
        if args.command == 'design':
            summary = bridge_app.design(args.fixture, args.output, args.mock_execute)
        elif args.command == 'connect':
            summary = bridge_app.connect(args.input, args.output)
        elif args.command == 'connect-pair':
            summary = bridge_app.connect_pair(args.input, args.output, args.mock_execute, args.snapshot)
        elif args.command == 'status':
            summary = bridge_app.status(args.run)
        else:
            summary = bridge_app.verify(args.run)
    return emit(summary)


if __name__ == '__main__':
    raise SystemExit(main())
