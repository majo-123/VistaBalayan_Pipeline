#!/usr/bin/env python3
"""Main entry point for the VistaBalayan ETL pipeline.

Stage 1 workflow:
1. Test the Supabase connection.
2. Extract the four source tables in batches and save CSV files.
3. Build the local SQLite staging database from those CSV files.
4. Validate record counts, columns, and relationships.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.database import DEFAULT_TABLES, create_client
from pipeline.extract import export_all_tables
from pipeline.staging import run as build_sqlite
from pipeline.validate import validate_sqlite


def command_test_connection(args: argparse.Namespace) -> dict:
    client = create_client(args.env)
    return client.test_connection(args.table)


def command_extract_csv(args: argparse.Namespace) -> dict:
    client = create_client(args.env)
    tables = tuple(args.tables) if args.tables else DEFAULT_TABLES
    return export_all_tables(
        client=client,
        output_dir=args.output_dir,
        tables=tables,
        batch_size=args.batch_size,
        log_dir=args.log_dir,
    )


def command_build_sqlite(args: argparse.Namespace) -> dict:
    return build_sqlite(args.config, raw_dir=args.raw_dir, sqlite_output=args.sqlite_output, log_dir=args.log_dir)


def command_validate(args: argparse.Namespace) -> dict:
    return validate_sqlite(args.config, sqlite_path=args.sqlite_output, log_dir=args.log_dir)


def command_all(args: argparse.Namespace) -> dict:
    client = create_client(args.env)
    extraction = export_all_tables(
        client=client,
        output_dir=args.raw_dir,
        tables=tuple(args.tables) if args.tables else DEFAULT_TABLES,
        batch_size=args.batch_size,
        log_dir=args.log_dir,
    )
    if extraction["overall_status"] != "PASS":
        return {"overall_status": "FAIL", "stage": "extract_csv", "extraction": extraction}
    sqlite_result = build_sqlite(args.config, raw_dir=args.raw_dir, sqlite_output=args.sqlite_output, log_dir=args.log_dir)
    if sqlite_result["overall_status"] != "PASS":
        return {"overall_status": "FAIL", "stage": "build_sqlite", "extraction": extraction, "sqlite": sqlite_result}
    validation = validate_sqlite(args.config, sqlite_path=args.sqlite_output, log_dir=args.log_dir)
    return {
        "overall_status": validation["overall_status"],
        "stage": "complete",
        "extraction": extraction,
        "sqlite": sqlite_result,
        "validation": validation,
    }


def add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=Path("pipeline/pipeline_config.json"), type=Path)
    parser.add_argument("--raw-dir", default=Path("pipeline/raw"), type=Path)
    parser.add_argument("--sqlite-output", default=Path("pipeline/processed/vistabalayan_staging.sqlite"), type=Path)
    parser.add_argument("--log-dir", default=Path("documentation/logs"), type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VistaBalayan ETL pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    test_parser = subparsers.add_parser("test-connection", help="Test Supabase/PostgREST connection")
    test_parser.add_argument("--env", default=Path(".env"), type=Path)
    test_parser.add_argument("--table", default="establishments")
    test_parser.set_defaults(func=command_test_connection)

    extract_parser = subparsers.add_parser("extract-csv", help="Extract Supabase tables to pipeline/raw CSV files")
    extract_parser.add_argument("--env", default=Path(".env"), type=Path)
    extract_parser.add_argument("--output-dir", default=Path("pipeline/raw"), type=Path)
    extract_parser.add_argument("--log-dir", default=Path("documentation/logs"), type=Path)
    extract_parser.add_argument("--batch-size", type=int)
    extract_parser.add_argument("--tables", nargs="*")
    extract_parser.set_defaults(func=command_extract_csv)

    sqlite_parser = subparsers.add_parser("build-sqlite", help="Build SQLite staging DB from pipeline/raw CSV files")
    add_common_paths(sqlite_parser)
    sqlite_parser.set_defaults(func=command_build_sqlite)

    validate_parser = subparsers.add_parser("validate", help="Validate SQLite metadata and relationships")
    add_common_paths(validate_parser)
    validate_parser.set_defaults(func=command_validate)

    all_parser = subparsers.add_parser("all", help="Run test/extract/build/validate pipeline")
    all_parser.add_argument("--env", default=Path(".env"), type=Path)
    all_parser.add_argument("--batch-size", type=int)
    all_parser.add_argument("--tables", nargs="*")
    add_common_paths(all_parser)
    all_parser.set_defaults(func=command_all)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, indent=2))
    return 0 if result.get("overall_status", result.get("status")) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
