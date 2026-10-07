from datetime import timedelta
from pathlib import Path

import matplotlib.dates as mdates
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
    ScheduleResult를 Interviewee / Room 기준 Gantt chart로 출력한다.

    시간은 SchedulerConfig.start_time을 기준으로
    ScheduleResult 내부의 minute offset을 실제 datetime으로 변환한다.

    Parameters
    ----------
    result:
        InterviewScheduler.solve()의 결과

    config:
        SchedulerConfig

    output_path:
        PNG 등의 파일로 저장할 경로.
        None이면 파일로 저장하지 않는다.

    show:
        True이면 matplotlib window를 표시한다.
    """

    if not result.persons:
        raise ValueError(
            "ScheduleResult contains no person schedules."
        )

    if not result.rooms:
        raise ValueError(
            "ScheduleResult contains no room schedules."
        )

    # ---------------------------------------------------------
    # Person 정렬
    #
    # 실제 첫 시작 시간이 빠른 사람부터 표시한다.
    # 동일한 시간이라면 interviewee 번호를 기준으로 정렬한다.
    # ---------------------------------------------------------
    persons = sorted(
        result.persons,
        key=lambda person: (
            person.first_start,
            person.interviewee,
        ),
    )

    # ---------------------------------------------------------
    # Room 정렬
    # ---------------------------------------------------------
    rooms = sorted(
        result.rooms,
        key=lambda room: (
            room.room,
            room.room_start,
            room.interviewee,
        ),
    )

    fig, (ax_person, ax_room) = plt.subplots(
        2,
        1,
        figsize=(16, 10),
        gridspec_kw={
            "height_ratios": [2, 1],
        },
    )

    _plot_person_gantt(
        ax_person,
        persons,
        config,
    )

    _plot_room_gantt(
        ax_room,
        rooms,
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
    persons,
    config: SchedulerConfig,
) -> None:
    """
    Interviewee 기준 Gantt chart.

    X축:
        실제 datetime

    Y축:
        first_start가 빠른 Interviewee 순
    """

    y_positions = {
        person.interviewee: index
        for index, person in enumerate(persons)
    }

    for person in persons:
        y = y_positions[person.interviewee]

        for interview in person.interviews:
            interview_type = config.interview_types[
                interview.interview_type
            ]

            # -------------------------------------------------
            # 실제 datetime 계산
            # -------------------------------------------------

            ready_start = (
                config.start_time
                + timedelta(
                    minutes=interview.ready_start
                )
            )

            interview_start = (
                config.start_time
                + timedelta(
                    minutes=interview.start
                )
            )

            interview_end = (
                config.start_time
                + timedelta(
                    minutes=interview.end
                )
            )

            # -------------------------------------------------
            # Ready
            # -------------------------------------------------

            if ready_start < interview_start:
                ax.barh(
                    y,
                    interview_start - ready_start,
                    left=ready_start,
                    height=0.55,
                    alpha=0.3,
                )

            # -------------------------------------------------
            # Interview
            # -------------------------------------------------

            ax.barh(
                y,
                interview_end - interview_start,
                left=interview_start,
                height=0.55,
            )

            # -------------------------------------------------
            # Interview Type 표시
            # -------------------------------------------------

            center = (
                interview_start
                + (
                    interview_end
                    - interview_start
                ) / 2
            )

            ax.text(
                center,
                y,
                interview.interview_type,
                ha="center",
                va="center",
            )

        # -----------------------------------------------------
        # Person 번호
        # -----------------------------------------------------

        person_start = (
            config.start_time
            + timedelta(
                minutes=person.first_start
            )
        )

        ax.text(
            person_start,
            y,
            f"P{person.interviewee}",
            ha="right",
            va="center",
        )

    # ---------------------------------------------------------
    # Y축
    # ---------------------------------------------------------

    ax.set_yticks(
        list(y_positions.values())
    )

    ax.set_yticklabels(
        [
            f"Interviewee {person.interviewee}"
            for person in persons
        ]
    )

    # ---------------------------------------------------------
    # X축 범위
    # ---------------------------------------------------------

    start_time = config.start_time
    end_time = config.end_time

    ax.set_xlim(
        start_time,
        end_time,
    )

    # ---------------------------------------------------------
    # X축: 10분 단위
    # ---------------------------------------------------------

    _configure_time_axis(ax)

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
    rooms,
    config: SchedulerConfig,
) -> None:
    """
    Room 기준 Gantt chart.

    X축:
        실제 datetime

    Y축:
        Room
    """

    room_names = sorted({
        room.room
        for room in rooms
    })

    y_positions = {
        room_name: index
        for index, room_name in enumerate(room_names)
    }

    for room in rooms:
        y = y_positions[room.room]

        # -----------------------------------------------------
        # 실제 datetime 계산
        # -----------------------------------------------------

        room_start = (
            config.start_time
            + timedelta(
                minutes=room.room_start
            )
        )

        interview_start = (
            config.start_time
            + timedelta(
                minutes=room.interview_start
            )
        )

        interview_end = (
            config.start_time
            + timedelta(
                minutes=room.interview_end
            )
        )

        room_end = (
            config.start_time
            + timedelta(
                minutes=room.room_end
            )
        )

        # -----------------------------------------------------
        # Ready / Preparation
        # -----------------------------------------------------

        if room_start < interview_start:
            ax.barh(
                y,
                interview_start - room_start,
                left=room_start,
                height=0.55,
                alpha=0.3,
            )

        # -----------------------------------------------------
        # 실제 Interview
        # -----------------------------------------------------

        ax.barh(
            y,
            interview_end - interview_start,
            left=interview_start,
            height=0.55,
        )

        # -----------------------------------------------------
        # Break / Cooldown
        #
        # 현재 RoomSchedule의 room_end는
        # interview_end + break_time을 의미한다.
        # -----------------------------------------------------

        if interview_end < room_end:
            ax.barh(
                y,
                room_end - interview_end,
                left=interview_end,
                height=0.55,
                alpha=0.15,
            )

        # -----------------------------------------------------
        # Interview Type / Person
        # -----------------------------------------------------

        center = (
            interview_start
            + (
                interview_end
                - interview_start
            ) / 2
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

    # ---------------------------------------------------------
    # Y축
    # ---------------------------------------------------------

    ax.set_yticks(
        list(y_positions.values())
    )

    ax.set_yticklabels(
        room_names
    )

    # ---------------------------------------------------------
    # X축
    # ---------------------------------------------------------

    start_time = config.start_time

    # 현재 solver에서는 room_end가
    # horizon + break_time까지 갈 수 있으므로
    # Gantt에도 이를 반영한다.
    # break_time은 면접 타입별 값이므로 최대값을 사용한다.
    max_break_time = max(
        (
            interview_type.break_time
            for interview_type in config.interview_types.values()
        ),
        default=0,
    )

    end_time = (
        config.end_time
        + timedelta(
            minutes=max_break_time
        )
    )

    ax.set_xlim(
        start_time,
        end_time,
    )

    _configure_time_axis(ax)

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
                alpha=0.3,
                label="Ready / Preparation",
            ),
            Patch(
                label="Interview",
            ),
            Patch(
                alpha=0.15,
                label="Break",
            ),
        ],
        loc="upper right",
    )


def _configure_time_axis(
    ax,
) -> None:
    """
    X축을 실제 datetime 기준 10분 단위로 설정한다.
    """

    ax.xaxis.set_major_locator(
        mdates.MinuteLocator(
            interval=10,
        )
    )

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%H:%M",
        )
    )

    ax.tick_params(
        axis="x",
        rotation=45,
    )
