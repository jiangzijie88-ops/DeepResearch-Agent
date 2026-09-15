from pathlib import Path

from models.research_state import ResearchState


def save_state(
    state: ResearchState,
    path: str | Path,
) -> None:
    """
    将 ResearchState 保存为 JSON 文件。
    """

    state_path = Path(path)

    state_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    state_path.write_text(
        state.model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )


def load_state(
    path: str | Path,
) -> ResearchState:
    """
    从 JSON 文件恢复 ResearchState。
    """

    state_path = Path(path)

    state_json = state_path.read_text(
        encoding="utf-8"
    )

    return ResearchState.model_validate_json(
        state_json
    )