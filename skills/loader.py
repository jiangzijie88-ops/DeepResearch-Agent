from pathlib import Path


def load_skill(skill_name: str) -> str:
    """
    Load a skill from skills/<skill_name>/SKILL.md.
    """

    skill_path = (
        Path(__file__).parent
        / skill_name
        / "SKILL.md"
    )

    if not skill_path.exists():
        raise FileNotFoundError(
            f"Skill not found: {skill_path}"
        )

    # 把整个 SKILL.md 读取成字符串
    return skill_path.read_text(
        encoding="utf-8"
    )