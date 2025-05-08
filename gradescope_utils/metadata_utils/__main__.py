import argparse
from pathlib import Path

from gradescope_utils.metadata_utils import parse_metadata, SubmissionInfo, extract_info

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metadata utilities")
    parser.add_argument("metadata_file", type=Path, help="Path to the metadata file")

    subcommands = parser.add_subparsers(dest="command", required=True)

    lookup = subcommands.add_parser("lookup", help="Look up a student")
    lookup.add_argument("query", type=str, help="Query like sid=whatever or email=whatever")
    lookup.add_argument(
        "output",
        type=str,
        choices=["submission_dir", "id", "name", "email"],
        default="submission_dir",
    )

    args = parser.parse_args()

    data = parse_metadata(args.metadata_file)
    if args.command == "lookup":
        query_key, query_value = args.query.split("=")
        for submission in extract_info(data):
            if getattr(submission, query_key) == query_value:
                break
        else:
            print(f"No submission found for {args.query}")
            exit(1)

        print(getattr(submission, args.output))
