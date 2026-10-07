import pytest

from interview_scheduler.models import (
    InterviewSchedule,
    InterviewType,
    PersonSchedule,
    RoomSchedule,
    ScheduleResult,
    SchedulerConfig,
)
from interview_scheduler.validate import (
    ScheduleValidationError,
    validate_schedule,
)
from datetime import datetime

@pytest.fixture
def config():
    return SchedulerConfig(
        n_interviewees=1,
        start_time=datetime(
            2026, 10, 10, 9, 0
        ),
        end_time=datetime(
            2026, 10, 10, 12, 20
        ),
        travel_time=10,
        interview_types={
            "A": InterviewType(
                duration=30,
                ready=5,
                room_count=1,
                break_time=5,
                ready_occupies_room=True,
            ),
            "B": InterviewType(
                duration=20,
                ready=5,
                room_count=1,
                break_time=5,
                ready_occupies_room=False,
            ),
            "C": InterviewType(
                duration=40,
                ready=10,
                room_count=1,
                break_time=5,
                ready_occupies_room=True,
            ),
        },
    )


def make_valid_result():
    interviews = [
        InterviewSchedule(
            interviewee=0,
            interview_type="A",
            ready_start=0,
            start=5,
            end=35,
            room="A-1",
        ),
        InterviewSchedule(
            interviewee=0,
            interview_type="B",
            ready_start=50,
            start=55,
            end=75,
            room="B-1",
        ),
        InterviewSchedule(
            interviewee=0,
            interview_type="C",
            ready_start=90,
            start=100,
            end=140,
            room="C-1",
        ),
    ]

    person = PersonSchedule(
        interviewee=0,
        interviews=interviews,
        first_start=0,
        last_end=140,
        stay=140,
    )

    rooms = [
        RoomSchedule(
            room="A-1",
            interview_type="A",
            interviewee=0,
            room_start=0,
            interview_start=5,
            interview_end=35,
            room_end=40,
        ),
        RoomSchedule(
            room="B-1",
            interview_type="B",
            interviewee=0,
            room_start=55,
            interview_start=55,
            interview_end=75,
            room_end=80,
        ),
        RoomSchedule(
            room="C-1",
            interview_type="C",
            interviewee=0,
            room_start=90,
            interview_start=100,
            interview_end=140,
            room_end=145,
        ),
    ]

    return ScheduleResult(
        status="OPTIMAL",
        objective=140,
        persons=[person],
        rooms=rooms,
    )


# ---------------------------------------------------------------------------
# Basic validity
# ---------------------------------------------------------------------------


def test_valid_schedule_passes(config):
    result = make_valid_result()

    validate_schedule(result, config)


# ---------------------------------------------------------------------------
# Person / interview structure
# ---------------------------------------------------------------------------


def test_wrong_number_of_interviewees(config):
    result = make_valid_result()

    result.persons = []

    with pytest.raises(
        ScheduleValidationError,
        match="Invalid number of interviewees",
    ):
        validate_schedule(result, config)


def test_invalid_interviewee_id(config):
    result = make_valid_result()

    result.persons[0].interviewee = 99

    with pytest.raises(
        ScheduleValidationError,
        match="Invalid interviewee IDs",
    ):
        validate_schedule(result, config)


def test_missing_interview_type(config):
    result = make_valid_result()

    result.persons[0].interviews.pop()

    with pytest.raises(
        ScheduleValidationError,
        match="expected 3 interviews, got 2",
    ):
        validate_schedule(result, config)


def test_duplicate_interview_type(config):
    result = make_valid_result()

    interviews = result.persons[0].interviews

    interviews[2].interview_type = "A"

    with pytest.raises(
        ScheduleValidationError,
        match="duplicate interview type",
    ):
        validate_schedule(result, config)


def test_unknown_interview_type(config):
    result = make_valid_result()

    result.persons[0].interviews[0].interview_type = "D"

    with pytest.raises(
        ScheduleValidationError,
        match="invalid interview types",
    ):
        validate_schedule(result, config)


# ---------------------------------------------------------------------------
# Interview timing
# ---------------------------------------------------------------------------


def test_ready_start_mismatch(config):
    result = make_valid_result()

    interview = result.persons[0].interviews[0]

    # A.ready = 5
    # ready_start = 0
    # Therefore start must be 5.
    interview.start = 6

    with pytest.raises(
        ScheduleValidationError,
        match="ready/start mismatch",
    ):
        validate_schedule(result, config)


def test_duration_mismatch(config):
    result = make_valid_result()

    interview = result.persons[0].interviews[0]

    # A.duration = 30
    # start = 5
    # Therefore end must be 35.
    interview.end = 36

    with pytest.raises(
        ScheduleValidationError,
        match="duration mismatch",
    ):
        validate_schedule(result, config)


def test_negative_ready_start(config):
    result = make_valid_result()

    interview = result.persons[0].interviews[0]

    # Keep ready/start arithmetic valid:
    #
    # ready_start = -1
    # ready       = 5
    # start       = 4
    #
    # Only the negative ready_start constraint is violated.
    interview.ready_start = -1
    interview.start = 4

    with pytest.raises(
        ScheduleValidationError,
        match="ready_start < 0",
    ):
        validate_schedule(result, config)


def test_interview_exceeds_horizon(config):
    result = make_valid_result()

    interview = result.persons[0].interviews[2]

    # C:
    # ready = 10
    # duration = 40
    #
    # Keep all arithmetic valid:
    # ready_start = 160
    # start       = 170
    # end         = 210
    #
    # Only horizon=200 is violated.
    interview.ready_start = 160
    interview.start = 170
    interview.end = 210

    with pytest.raises(
        ScheduleValidationError,
        match="exceeds horizon",
    ):
        validate_schedule(result, config)


# ---------------------------------------------------------------------------
# Person ordering / spacing
# ---------------------------------------------------------------------------


def test_insufficient_break_and_travel(config):
    result = make_valid_result()

    interview = result.persons[0].interviews[1]

    # A ends at 35.
    #
    # Required gap:
    # break  = 5
    # travel = 10
    # total  = 15
    #
    # Therefore B.ready_start must be >= 50.
    #
    # Set B.ready_start to 49 while keeping:
    # start = 49 + 5 = 54
    # end   = 54 + 20 = 74
    interview.ready_start = 49
    interview.start = 54
    interview.end = 74

    with pytest.raises(
        ScheduleValidationError,
        match="insufficient gap",
    ):
        validate_schedule(result, config)


def make_per_type_break_config():
    # A.break_time=15, B.break_time=5, travel_time=5.
    # A.end=35이면 B.ready_start는
    # 35 + 15(A의 break) + 5(travel) = 55 이상이어야 한다.
    return SchedulerConfig(
        n_interviewees=1,
        start_time=datetime(
            2026, 10, 10, 9, 0
        ),
        end_time=datetime(
            2026, 10, 10, 13, 0
        ),
        travel_time=5,
        interview_types={
            "A": InterviewType(
                duration=30,
                ready=5,
                room_count=1,
                break_time=15,
                ready_occupies_room=True,
            ),
            "B": InterviewType(
                duration=20,
                ready=5,
                room_count=1,
                break_time=5,
                ready_occupies_room=False,
            ),
        },
    )


def test_gap_between_types_uses_previous_type_break():
    config = make_per_type_break_config()

    # B.ready_start=54는
    # (잘못된) B.break_time=5 기준으로는 충분(35+5+5=45)하지만
    # 올바른 A.break_time=15 기준으로는 부족하다(35+15+5=55).
    result = ScheduleResult(
        status="FEASIBLE",
        objective=79,
        persons=[
            PersonSchedule(
                interviewee=0,
                interviews=[
                    InterviewSchedule(
                        interviewee=0,
                        interview_type="A",
                        ready_start=0,
                        start=5,
                        end=35,
                        room="A-1",
                    ),
                    InterviewSchedule(
                        interviewee=0,
                        interview_type="B",
                        ready_start=54,
                        start=59,
                        end=79,
                        room="B-1",
                    ),
                ],
                first_start=0,
                last_end=79,
                stay=79,
            ),
        ],
        rooms=[
            RoomSchedule(
                room="A-1",
                interview_type="A",
                interviewee=0,
                room_start=0,
                interview_start=5,
                interview_end=35,
                room_end=50,
            ),
            RoomSchedule(
                room="B-1",
                interview_type="B",
                interviewee=0,
                room_start=59,
                interview_start=59,
                interview_end=79,
                room_end=84,
            ),
        ],
    )

    with pytest.raises(
        ScheduleValidationError,
        match="insufficient gap",
    ):
        validate_schedule(result, config)


def test_gap_between_types_satisfied_with_previous_type_break():
    config = make_per_type_break_config()

    # B.ready_start=55는 A.break_time=15 + travel_time=5를
    # 정확히 만족한다.
    result = ScheduleResult(
        status="FEASIBLE",
        objective=80,
        persons=[
            PersonSchedule(
                interviewee=0,
                interviews=[
                    InterviewSchedule(
                        interviewee=0,
                        interview_type="A",
                        ready_start=0,
                        start=5,
                        end=35,
                        room="A-1",
                    ),
                    InterviewSchedule(
                        interviewee=0,
                        interview_type="B",
                        ready_start=55,
                        start=60,
                        end=80,
                        room="B-1",
                    ),
                ],
                first_start=0,
                last_end=80,
                stay=80,
            ),
        ],
        rooms=[
            RoomSchedule(
                room="A-1",
                interview_type="A",
                interviewee=0,
                room_start=0,
                interview_start=5,
                interview_end=35,
                room_end=50,
            ),
            RoomSchedule(
                room="B-1",
                interview_type="B",
                interviewee=0,
                room_start=60,
                interview_start=60,
                interview_end=80,
                room_end=85,
            ),
        ],
    )

    validate_schedule(result, config)


def test_interviews_overlap(config):
    result = make_valid_result()

    # Put B before A and overlap them.
    #
    # B:
    # ready_start = 20
    # start       = 25
    # end         = 45
    #
    # A:
    # end = 35
    #
    # This violates the person ordering constraint.
    interview = result.persons[0].interviews[1]

    interview.ready_start = 20
    interview.start = 25
    interview.end = 45

    with pytest.raises(
        ScheduleValidationError,
        match="insufficient gap",
    ):
        validate_schedule(result, config)


# ---------------------------------------------------------------------------
# Stay calculation
# ---------------------------------------------------------------------------


def test_invalid_first_start(config):
    result = make_valid_result()

    result.persons[0].first_start = 1

    with pytest.raises(
        ScheduleValidationError,
        match="invalid first_start",
    ):
        validate_schedule(result, config)


def test_invalid_last_end(config):
    result = make_valid_result()

    result.persons[0].last_end = 139

    with pytest.raises(
        ScheduleValidationError,
        match="invalid last_end",
    ):
        validate_schedule(result, config)


def test_invalid_stay(config):
    result = make_valid_result()

    result.persons[0].stay = 139

    with pytest.raises(
        ScheduleValidationError,
        match="invalid stay",
    ):
        validate_schedule(result, config)


def test_invalid_objective(config):
    result = make_valid_result()

    result.objective = 139

    with pytest.raises(
        ScheduleValidationError,
        match="Invalid objective",
    ):
        validate_schedule(result, config)


# ---------------------------------------------------------------------------
# Room schedule
# ---------------------------------------------------------------------------


def test_invalid_room_end(config):
    result = make_valid_result()

    room = result.rooms[0]

    # A interview_end = 35
    # break_time = 5
    # Therefore room_end must be 40.
    room.room_end = 41

    with pytest.raises(
        ScheduleValidationError,
        match="invalid room_end",
    ):
        validate_schedule(result, config)


def test_room_starts_after_interview(config):
    result = make_valid_result()

    room = result.rooms[0]

    # Keep room_start independent from the person schedule
    # so that this specific constraint is the first violation.
    room.room_start = 10

    with pytest.raises(
        ScheduleValidationError,
        match="room starts after interview",
    ):
        validate_schedule(result, config)


def test_invalid_interview_interval_in_room_schedule(config):
    result = make_valid_result()

    room = result.rooms[0]

    # Keep room_start valid:
    # room_start = 0
    #
    # But make interview_start > interview_end.
    #
    # This should be caught by:
    #     invalid interview interval
    #
    # before comparing against the person's interview.
    room.interview_start = 36
    room.interview_end = 35

    with pytest.raises(
        ScheduleValidationError,
        match="invalid interview interval",
    ):
        validate_schedule(result, config)


def test_room_start_mismatch_when_ready_occupies_room(config):
    result = make_valid_result()

    room = result.rooms[0]

    # A.ready_occupies_room = True.
    #
    # Therefore:
    # room_start must equal ready_start = 0.
    room.room_start = 1

    with pytest.raises(
        ScheduleValidationError,
        match="invalid room_start",
    ):
        validate_schedule(result, config)


def test_room_start_mismatch_when_ready_does_not_occupy_room(config):
    result = make_valid_result()

    room = result.rooms[1]

    # B.ready_occupies_room = False.
    #
    # Therefore:
    # room_start must equal interview.start = 55.
    room.room_start = 50

    with pytest.raises(
        ScheduleValidationError,
        match="invalid room_start",
    ):
        validate_schedule(result, config)


def test_room_interview_end_mismatch(config):
    result = make_valid_result()

    room = result.rooms[0]

    # Person's A interview:
    # start = 5
    # end   = 35
    #
    # Change only room.interview_end.
    #
    # room_end remains 40, which is intentionally consistent
    # with the *new* room.interview_end:
    #
    # room.interview_end = 40
    # room_end          = 45
    #
    # But then room_end would trigger first.
    #
    # Therefore use a value that preserves room_end relation
    # while breaking the person/room relation.
    room.interview_end = 36
    room.room_end = 41

    with pytest.raises(
        ScheduleValidationError,
        match="interview_end mismatch",
    ):
        validate_schedule(result, config)


def test_room_overlap(config):
    result = make_valid_result()

    # Add another completely valid A room interval for the same room.
    #
    # It is intentionally a duplicate of the existing valid interval:
    #
    # A-1: 0 ~ 40
    #
    # All room/person consistency checks pass.
    # Only the room overlap check fails.
    result.rooms.append(
        RoomSchedule(
            room="A-1",
            interview_type="A",
            interviewee=0,
            room_start=0,
            interview_start=5,
            interview_end=35,
            room_end=40,
        )
    )

    with pytest.raises(
        ScheduleValidationError,
        match="Room overlap",
    ):
        validate_schedule(result, config)
