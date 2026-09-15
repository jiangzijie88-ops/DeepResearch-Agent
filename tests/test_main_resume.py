import os
import subprocess
import sys
from pathlib import Path

from models.research_state import (
    ResearchState,
    ResearchStatus,
)
from models.state_store import save_state


def test_completed_checkpoint_exits_without_running_planner(
    tmp_path,
):
    state_path = tmp_path / "completed_state.json"

    state = ResearchState(
        question="completed resume test",
        status=ResearchStatus.COMPLETED,
        final_report="Already finished report.",
    )

    save_state(
        state,
        state_path,
    )

    project_root = Path(__file__).resolve().parents[1]

    env = os.environ.copy()

    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--resume",
            str(state_path),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )

    print(result.stdout)
    print(result.stderr)

    assert result.returncode == 0

    assert (
        "[Resume] 当前任务已经完成"
        in result.stdout
    )

    assert (
        "Already finished report."
        in result.stdout
    )

    assert (
        "[Planner] 正在生成研究计划"
        not in result.stdout
    )