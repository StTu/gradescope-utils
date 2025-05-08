from dataclasses import dataclass

import yaml


@dataclass
class SubmissionInfo:
    submission_dir: str
    id: str
    name: str
    email: str


def parse_metadata(metadata_file):
    """
    Parses the metadata file and returns a dictionary of metadata.

    Args:
        metadata_file (str): Path to the metadata file.

    Returns:
        dict: Dictionary containing the parsed metadata.
    """
    with open(metadata_file, "r") as file:
        metadata = yaml.safe_load(file)
    return metadata


def extract_info(metadata):
    """
    Extracts student information from the metadata.

    Args:
        metadata (dict): Dictionary containing the parsed metadata.

    Yields:
        SubmissionInfo objects.
    """
    for submission_dir, info in metadata.items():
        if ":submitters" not in info:
            raise ValueError(
                f"Missing submitters in {submission_dir}: {info}"
            )
        elif len(info[":submitters"]) == 0 or len(info[":submitters"]) > 1:
            raise ValueError(
                f"Invalid number of submitters in {submission_dir}: {info}"
            )
        student = info[":submitters"][0]
        yield SubmissionInfo(
            submission_dir=submission_dir,
            id=student[":sid"],
            name=student[":name"],
            email=student[":email"],
        )
