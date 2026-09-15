import argparse


def parse_args(
    args=None,
):
    parser = argparse.ArgumentParser(
        description="DeepResearch-Agent"
    )

    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="从已有 ResearchState JSON checkpoint 恢复任务",
    )

    return parser.parse_args(
        args
    )