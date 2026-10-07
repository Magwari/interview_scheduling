from datetime import datetime

from .models import (
    InterviewType,
    SchedulerConfig,
)
from .solver import InterviewScheduler
from .validate import validate_schedule
from .gantt import plot_gantt
from .export import save_json


def main() -> None:

    config = SchedulerConfig(
        n_interviewees=60,
        start_time=datetime(
            2026, 10, 10, 8, 30
        ),

        end_time=datetime(
            2026, 10, 10, 12, 30
        ),

        travel_time=5,

        interview_types={
            "면접 A": InterviewType(
                duration=30,
                ready=0,
                room_count=9,
                break_time=5,
                ready_occupies_room=True,
            ),
            "면접 B": InterviewType(
                duration=10,
                ready=20,
                room_count=6,
                break_time=0,
                ready_occupies_room=False,
            ),
            "면접 C": InterviewType(
                duration=15,
                ready=0,
                room_count=5,
                break_time=5,
                ready_occupies_room=True,
            ),
        },
    )

    scheduler = InterviewScheduler(config)

    result = scheduler.solve(
        time_limit=10.0
    )

    validate_schedule(
        result,
        config,
    )

    print("Validation : OK")

    print("Status :", result.status)
    print("Max stay :", result.objective)

    for person in result.persons:

        print(
            f"\nPerson {person.interviewee}: "
            f"stay={person.stay}"
        )

        for interview in person.interviews:

            print(
                f"  {interview.interview_type}: "
                f"ready={interview.ready_start:3d} "
                f"interview="
                f"{interview.start:3d} ~ "
                f"{interview.end:3d}"
            )

    print()
    print("=== Room Schedule ===")

    current_room = None

    for room in result.rooms:

        if room.room != current_room:
            current_room = room.room

            print()
            print(
                f"[{room.room}]"
            )

        print(
            f"  Person {room.interviewee}: "
            f"room={room.room_start:3d} ~ "
            f"{room.room_end:3d}, "
            f"interview="
            f"{room.interview_start:3d} ~ "
            f"{room.interview_end:3d}"
        )

    # config는 기존 SchedulerConfig 사용

    result = scheduler.solve()

    if result.status in ("OPTIMAL", "FEASIBLE"):
        save_json(
            result,
            config,
            output_path="output/interview_schedule.json",
        )

        plot_gantt(
            result,
            config,
            output_path="output/interview_schedule.png",
            show=True,
        )

if __name__ == "__main__":
    main()