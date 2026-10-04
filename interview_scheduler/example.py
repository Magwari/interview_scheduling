from .models import (
    InterviewType,
    SchedulerConfig,
)
from .solver import InterviewScheduler
from .validate import validate_schedule
from .gantt import plot_gantt
from .solver import InterviewScheduler

def main():

    config = SchedulerConfig(
        n_interviewees=60,
        horizon=240,

        break_time=5,
        travel_time=5,

        interview_types={
            "A": InterviewType(
                name="A",
                duration=25,
                ready=0,
                room_count=8,
                ready_occupies_room=True,
            ),
            "B": InterviewType(
                name="B",
                duration=10,
                ready=20,
                room_count=6,
                ready_occupies_room=False,
            ),
            "C": InterviewType(
                name="C",
                duration=15,
                ready=0,
                room_count=5,
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
        plot_gantt(
            result,
            config,
            output_path="output/interview_schedule.png",
            show=True,
        )

if __name__ == "__main__":
    main()