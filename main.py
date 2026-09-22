import sys
from datetime import datetime
from pathlib import Path

from models.research_state import (
    ResearchState,
    ResearchStatus,
)
from models.state_store import (
    load_state,
    save_state,
)

from workflow.cli import (
    parse_args,
)
from workflow.pipeline import (
    run_research_pipeline,
    save_run_outputs,
)


class Tee:
    """
    同时将输出写到终端和日志文件。
    """

    def __init__(
        self,
        *streams,
    ):
        self.streams = streams

    def write(
        self,
        data,
    ):
        for stream in (
            self.streams
        ):
            stream.write(data)
            stream.flush()

    def flush(
        self,
    ):
        for stream in (
            self.streams
        ):
            stream.flush()


def setup_logging(
    output_dir: Path,
    timestamp: str,
):
    """
    创建 Workflow 日志。
    """

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_path = (
        output_dir
        / f"workflow_{timestamp}.log"
    )

    log_file = (
        log_path.open(
            "w",
            encoding="utf-8",
        )
    )

    sys.stdout = Tee(
        sys.__stdout__,
        log_file,
    )

    sys.stderr = Tee(
        sys.__stderr__,
        log_file,
    )

    print(
        "[Workflow] 完整日志将保存到："
        f"{log_path}"
    )

    return log_path


def load_or_create_state(
    args,
    output_dir: Path,
    timestamp: str,
):
    """
    创建新任务或加载 Resume checkpoint。
    """

    if args.resume:

        state_path = Path(
            args.resume
        )

        state = load_state(
            state_path
        )

        print(
            "[Resume] 已加载 Research State："
            f"{state_path}"
        )

        print(
            "[Resume] 当前 Workflow status: "
            f"{state.status.value}"
        )

        print(
            "[Resume] Research round: "
            f"{state.research_round}"
        )

        return (
            state,
            state_path,
        )

    question = input(
        "请输入你的研究问题：\n"
    ).strip()

    if not question:

        raise ValueError(
            "研究问题不能为空"
        )

    state = ResearchState(
        question=question
    )

    state_path = (
        output_dir
        / f"state_{timestamp}.json"
    )

    save_state(
        state,
        state_path,
    )

    return (
        state,
        state_path,
    )


def main():

    args = parse_args()

    output_dir = Path(
        "outputs"
    )

    timestamp = (
        datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    setup_logging(
        output_dir,
        timestamp,
    )

    state, state_path = (
        load_or_create_state(
            args,
            output_dir,
            timestamp,
        )
    )

    # 已完成任务直接退出
    if (
        state.status
        == ResearchStatus.COMPLETED
    ):

        print(
            "[Resume] 当前任务已经完成，"
            "无需重新执行 Workflow。"
        )

        if state.final_report:

            print(
                "\n"
                + "=" * 60
            )

            print(
                "FINAL REPORT"
            )

            print(
                "=" * 60
            )

            print(
                state.final_report
            )

        return

    # ========================================================
    # Run Workflow
    # ========================================================

    state = run_research_pipeline(
        state=state,

        state_path=(
            state_path
        ),

        memory_path=(
            output_dir
            / "memory.json"
        ),
    )

    # ========================================================
    # Print Result
    # ========================================================

    print(
        "\n"
        + "=" * 60
    )

    print(
        "FINAL REPORT"
    )

    print(
        "=" * 60
    )

    print(
        state.final_report
        or ""
    )

    if (
        state.final_review
        is not None
    ):

        print(
            "\n"
            + "=" * 60
        )

        print(
            "FINAL CRITIC RESULT"
        )

        print(
            "=" * 60
        )

        print(
            "Verdict: "
            f"{state.final_review.verdict}"
        )

        print(
            "Needs Research: "
            f"{state.final_review.needs_research}"
        )

    # ========================================================
    # Save Output
    # ========================================================

    (
        report_path,
        critic_path,
    ) = save_run_outputs(
        state,
        output_dir,
        timestamp,
    )

    print(
        "\n[Workflow] 最终研究报告已保存到："
        f"{report_path}"
    )

    if critic_path:

        print(
            "[Workflow] 最终审核结果已保存到："
            f"{critic_path}"
        )

    print(
        "[State] Workflow status: "
        f"{state.status.value}"
    )

    print(
        "[Workflow] Research State 已保存到："
        f"{state_path}"
    )


if __name__ == "__main__":
    main()