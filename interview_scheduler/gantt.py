from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from .models import ScheduleResult, SchedulerConfig


def plot_gantt(
    result: ScheduleResult,
    config: SchedulerConfig,
    output_path: str | Path | None = None,
    show: bool = True,
) -> None:
    """
    ScheduleResult를 interviewee / room 기준 Gantt chart로 출력한다.

    위쪽:
        Interviewee별 일정

    아래쪽:
        Room별 일정

    Parameters
    ----------
    result:
        Scheduler.solve()의 결과

    config:
        SchedulerConfig

    output_path:
        PNG 등의 파일로 저장할 경로.
        None이면 파일로 저장하지 않는다.

    show:
        True이면 matplotlib window를 표시한다.
    """

    if not result.persons:
        raise ValueError("ScheduleResult contains no person schedules.")

    if not result.rooms:
        raise ValueError("ScheduleResult contains no room schedules.")

    fig, (ax_person, ax_room) = plt.subplots(
        2,
        1,
        figsize=(14, 8),
        gridspec_kw={
            "height_ratios": [2, 1],
        },
    )

    _plot_person_gantt(
        ax_person,
        result,
        config,
    )

    _plot_room_gantt(
        ax_room,
        result,
        config,
    )

    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        fig.savefig(
            output_path,
            dpi=150,
            bbox_inches="tight",
        )

    if show:
        plt.show()
    else:
        plt.close(fig)


def _plot_person_gantt(
    ax,
    result: ScheduleResult,
    config: SchedulerConfig,
) -> None:
    y_positions = {
        person.interviewee: index
        for index, person in enumerate(result.persons)
    }

    for person in result.persons:
        y = y_positions[person.interviewee]

        for interview in person.interviews:
            interview_type = config.interview_types[
                interview.interview_type
            ]

            # Ready 구간
            if interview_type.ready > 0:
                ax.barh(
                    y,
                    interview_type.ready,
                    left=interview.ready_start,
                    height=0.55,
                    alpha=0.3,
                )

            # 실제 Interview 구간
            ax.barh(
                y,
                interview_type.duration,
                left=interview.start,
                height=0.55,
            )

            # 실제 면접 구간 중앙에 Type 표시
            center = (
                interview.start
                + interview_type.duration / 2
            )

            ax.text(
                center,
                y,
                interview.interview_type,
                ha="center",
                va="center",
            )

        ax.text(
            person.first_start - 1,
            y,
            f"P{person.interviewee}",
            ha="right",
            va="center",
        )

    ax.set_yticks(
        list(y_positions.values())
    )

    ax.set_yticklabels(
        [
            f"Interviewee {person.interviewee}"
            for person in result.persons
        ]
    )

    ax.set_xlim(
        0,
        config.horizon,
    )

    ax.set_ylabel("Interviewee")
    ax.set_title("Interview Schedule")

    ax.grid(
        axis="x",
        alpha=0.3,
    )

    ax.legend(
        handles=[
            Patch(
                alpha=0.3,
                label="Ready",
            ),
            Patch(
                label="Interview",
            ),
        ],
        loc="upper right",
    )


def _plot_room_gantt(
    ax,
    result: ScheduleResult,
    config: SchedulerConfig,
) -> None:
    room_names = sorted({
        room.room
        for room in result.rooms
    })

    y_positions = {
        room_name: index
        for index, room_name in enumerate(room_names)
    }

    for room in result.rooms:
        y = y_positions[room.room]

        interview_type = config.interview_types[
            room.interview_type
        ]

        # Room occupancy 전체
        room_duration = (
            room.room_end
            - room.room_start
        )

        ax.barh(
            y,
            room_duration,
            left=room.room_start,
            height=0.55,
            alpha=0.35,
        )

        # 실제 interview 구간
        interview_duration = (
            room.interview_end
            - room.interview_start
        )

        ax.barh(
            y,
            interview_duration,
            left=room.interview_start,
            height=0.55,
        )

        center = (
            room.interview_start
            + interview_duration / 2
        )

        ax.text(
            center,
            y,
            (
                f"{room.interview_type}"
                f" / P{room.interviewee}"
            ),
            ha="center",
            va="center",
        )

    ax.set_yticks(
        list(y_positions.values())
    )

    ax.set_yticklabels(
        room_names
    )

    ax.set_xlim(
        0,
        config.horizon + config.break_time,
    )

    ax.set_xlabel("Time")
    ax.set_ylabel("Room")
    ax.set_title("Room Usage")

    ax.grid(
        axis="x",
        alpha=0.3,
    )

    ax.legend(
        handles=[
            Patch(
                alpha=0.35,
                label="Room Occupancy",
            ),
            Patch(
                label="Interview",
            ),
        ],
        loc="upper right",
    )
