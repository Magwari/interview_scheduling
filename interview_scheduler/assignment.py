from .models import (
    InterviewSchedule,
    RoomSchedule,
    SchedulerConfig,
)


def assign_rooms(
    persons: list,
    config: SchedulerConfig,
) -> list[RoomSchedule]:

    room_schedules = []

    for type_name, interview_type in config.interview_types.items():

        interviews: list[InterviewSchedule] = []

        for person in persons:
            for interview in person.interviews:
                if interview.interview_type == type_name:
                    interviews.append(interview)

        interviews.sort(
            key=lambda x: (
                x.ready_start
                if interview_type.ready_occupies_room
                else x.start,
                x.end,
                x.interviewee,
            )
        )

        room_last_end = [
            None
            for _ in range(interview_type.room_count)
        ]

        for interview in interviews:

            room_start = (
                interview.ready_start
                if interview_type.ready_occupies_room
                else interview.start
            )

            room_end = (
                interview.end
                + config.break_time
            )

            assigned_room = None

            for room_index in range(
                interview_type.room_count
            ):
                last_end = room_last_end[room_index]

                if (
                    last_end is None
                    or last_end <= room_start
                ):
                    assigned_room = room_index
                    break

            if assigned_room is None:
                raise RuntimeError(
                    f"Failed to assign room for "
                    f"{type_name}, "
                    f"interviewee={interview.interviewee}, "
                    f"room={room_start}~{room_end}"
                )

            room_name = (
                f"{type_name}-{assigned_room + 1}"
            )

            interview.room = room_name

            room_last_end[assigned_room] = room_end

            room_schedules.append(
                RoomSchedule(
                    room=room_name,
                    interview_type=type_name,
                    interviewee=interview.interviewee,
                    room_start=room_start,
                    interview_start=interview.start,
                    interview_end=interview.end,
                    room_end=room_end,
                )
            )

    room_schedules.sort(
        key=lambda x: (
            x.room,
            x.room_start,
            x.room_end,
        )
    )

    return room_schedules