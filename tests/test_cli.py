from workflow.cli import parse_args


def test_parse_args_without_resume():
    args = parse_args([])

    assert args.resume is None


def test_parse_args_with_resume():
    args = parse_args(
        [
            "--resume",
            "outputs/state_test.json",
        ]
    )

    assert args.resume == "outputs/state_test.json"