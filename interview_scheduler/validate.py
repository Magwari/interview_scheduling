from collections import defaultdict

from .models import (
    ScheduleResult,
    SchedulerConfig,
)


class ScheduleValidationError(Exception):
    """Raised when a schedule violates a scheduling constraint."""


def validate_schedule(
    result: ScheduleResult,
    config: SchedulerConfig,
) -> None:

    if result.status not in (
        "OPTIMAL",
        "FEASIBLE",
    ):
        raise ScheduleValidationError(
            f"Cannot validate schedule with status "
            f"{result.status}"
        )

    _validate_person_count(
        result,
        config,
    )

    _validate_interviews(
        result,
        config,
    )

    _validate_person_order(
        result,
        config,
    )

    _validate_stay(
        result,
        config,
    )

    _validate_rooms(
        result,
        config,
    )


def _validate_person_count(
    result: ScheduleResult,
    config: SchedulerConfig,
) -> None:

    if len(result.persons) != config.n_interviewees:
        raise ScheduleValidationError(
            "Invalid number of interviewees"
        )

    actual = {
        person.interviewee
        for person in result.persons
    }

    expected = set(
        range(config.n_interviewees)
    )

    if actual != expected:
        raise ScheduleValidationError(
            f"Invalid interviewee IDs: "
            f"expected={expected}, "
            f"actual={actual}"
        )


def _validate_interviews(
    result: ScheduleResult,
    config: SchedulerConfig,
) -> None:

    expected_types = set(
        config.interview_types.keys()
    )

    for person in result.persons:

        actual_types = [
            interview.interview_type
            for interview in person.interviews
        ]

        # 1. Interview count
        if len(actual_types) != len(expected_types):
            raise ScheduleValidationError(
                f"Person {person.interviewee}: "
                f"expected {len(expected_types)} interviews, "
                f"got {len(actual_types)}"
            )

        # 2. Duplicate interview type
        if len(actual_types) != len(set(actual_types)):
            raise ScheduleValidationError(
                f"Person {person.interviewee}: "
                "duplicate interview type"
            )

        # 3. Interview type set
        if set(actual_types) != expected_types:
            raise ScheduleValidationError(
                f"Person {person.interviewee}: "
                f"invalid interview types: "
                f"expected={expected_types}, "
                f"actual={set(actual_types)}"
            )

        for interview in person.interviews:

            interview_type = config.interview_types.get(
                interview.interview_type
            )

            if interview_type is None:
                raise ScheduleValidationError(
                    f"Unknown interview type: "
                    f"{interview.interview_type}"
                )

            # 4. Domain constraint
            if interview.ready_start < 0:
                raise ScheduleValidationError(
                    f"Person {person.interviewee}: "
                    "ready_start < 0"
                )

            # 5. Ready -> interview start
            expected_start = (
                interview.ready_start
                + interview_type.ready
            )

            if interview.start != expected_start:
                raise ScheduleValidationError(
                    f"Person {person.interviewee}, "
                    f"{interview.interview_type}: "
                    "ready/start mismatch"
                )

            # 6. Interview duration
            expected_end = (
                interview.start
                + interview_type.duration
            )

            if interview.end != expected_end:
                raise ScheduleValidationError(
                    f"Person {person.interviewee}, "
                    f"{interview.interview_type}: "
                    "duration mismatch"
                )

            # 7. Horizon
            if interview.end > config.horizon:
                raise ScheduleValidationError(
                    f"Person {person.interviewee}: "
                    f"{interview.interview_type} exceeds horizon"
                )


def _validate_person_order(
    result: ScheduleResult,
    config: SchedulerConfig,
) -> None:

    required_gap = (
        config.break_time
        + config.travel_time
    )

    for person in result.persons:

        interviews = sorted(
            person.interviews,
            key=lambda x: x.ready_start,
        )

        for previous, current in zip(
            interviews,
            interviews[1:],
        ):

            required_start = (
                previous.end
                + required_gap
            )

            if current.ready_start < required_start:
                raise ScheduleValidationError(
                    f"Person {person.interviewee}: "
                    f"insufficient gap between "
                    f"{previous.interview_type} and "
                    f"{current.interview_type}"
                )


def _validate_stay(
    result: ScheduleResult,
    config: SchedulerConfig,
) -> None:

    max_stay = 0

    for person in result.persons:

        first_start = min(
            interview.ready_start
            for interview in person.interviews
        )

        last_end = max(
            interview.end
            for interview in person.interviews
        )

        stay = last_end - first_start

        if person.first_start != first_start:
            raise ScheduleValidationError(
                f"Person {person.interviewee}: "
                "invalid first_start"
            )

        if person.last_end != last_end:
            raise ScheduleValidationError(
                f"Person {person.interviewee}: "
                "invalid last_end"
            )

        if person.stay != stay:
            raise ScheduleValidationError(
                f"Person {person.interviewee}: "
                "invalid stay"
            )

        max_stay = max(
            max_stay,
            stay,
        )

    if result.objective != max_stay:
        raise ScheduleValidationError(
            f"Invalid objective: "
            f"stored={result.objective}, "
            f"expected={max_stay}"
        )


def _validate_rooms(
    result: ScheduleResult,
    config: SchedulerConfig,
) -> None:

    room_groups = defaultdict(list)

    # --------------------------------------------------
    # Basic room validation
    # --------------------------------------------------

    for room in result.rooms:

        room_groups[room.room].append(room)

        interview_type = config.interview_types[
            room.interview_type
        ]

        expected_room_end = (
            room.interview_end
            + config.break_time
        )

        if room.room_end != expected_room_end:
            raise ScheduleValidationError(
                f"{room.room}: invalid room_end"
            )

        if (
            room.room_start
            > room.interview_start
        ):
            raise ScheduleValidationError(
                f"{room.room}: "
                "room starts after interview"
            )

        if (
            room.interview_start
            > room.interview_end
        ):
            raise ScheduleValidationError(
                f"{room.room}: "
                "invalid interview interval"
            )

        # Find corresponding interview
        person = next(
            p
            for p in result.persons
            if p.interviewee == room.interviewee
        )

        interview = next(
            i
            for i in person.interviews
            if i.interview_type
            == room.interview_type
        )

        expected_room_start = (
            interview.ready_start
            if interview_type.ready_occupies_room
            else interview.start
        )

        if room.room_start != expected_room_start:
            raise ScheduleValidationError(
                f"{room.room}: "
                "invalid room_start"
            )

        if room.interview_start != interview.start:
            raise ScheduleValidationError(
                f"{room.room}: "
                "interview_start mismatch"
            )

        if room.interview_end != interview.end:
            raise ScheduleValidationError(
                f"{room.room}: "
                "interview_end mismatch"
            )

    # --------------------------------------------------
    # Room overlap
    # --------------------------------------------------

    for room_name, rooms in room_groups.items():

        rooms.sort(
            key=lambda x: (
                x.room_start,
                x.room_end,
            )
        )

        for previous, current in zip(
            rooms,
            rooms[1:],
        ):

            if previous.room_end > current.room_start:
                raise ScheduleValidationError(
                    f"Room overlap: "
                    f"{room_name}: "
                    f"{previous.room_start}~"
                    f"{previous.room_end} "
                    f"vs "
                    f"{current.room_start}~"
                    f"{current.room_end}"
                )