import pytest

from interview_scheduler.models import (
    InterviewType,
    SchedulerConfig,
)
from interview_scheduler.solver import InterviewScheduler
from interview_scheduler.validate import validate_schedule


@pytest.fixture
def config():
    return SchedulerConfig(
        n_interviewees=1,
        horizon=200,
        break_time=5,
        travel_time=10,
        interview_types={
            "A": InterviewType(
                name="A",
                duration=30,
                ready=5,
                room_count=1,
                ready_occupies_room=True,
            ),
            "B": InterviewType(
                name="B",
                duration=20,
                ready=5,
                room_count=1,
                ready_occupies_room=False,
            ),
            "C": InterviewType(
                name="C",
                duration=40,
                ready=10,
                room_count=1,
                ready_occupies_room=True,
            ),
        },
    )


def test_solver_produces_valid_schedule(config):
    scheduler = InterviewScheduler(config)

    result = scheduler.solve()

    assert result.status in (
        "OPTIMAL",
        "FEASIBLE",
    )

    validate_schedule(
        result,
        config,
    )


def test_solver_finds_expected_optimal_stay(config):
    scheduler = InterviewScheduler(config)

    result = scheduler.solve()

    assert result.status == "OPTIMAL"

    # For one interviewee:
    #
    # A -> B -> C
    #
    # A:
    #   ready      0 ~ 5
    #   interview  5 ~ 35
    #
    # B:
    #   ready     50 ~ 55
    #   interview 55 ~ 75
    #
    # C:
    #   ready     90 ~ 100
    #   interview 100 ~ 140
    #
    # Therefore:
    #
    # first_start = 0
    # last_end    = 140
    # stay         = 140
    #
    # Other permutations are no better.
    assert result.objective == 140

    validate_schedule(
        result,
        config,
    )


def test_solver_schedule_contains_all_interviews(config):
    scheduler = InterviewScheduler(config)

    result = scheduler.solve()

    assert result.status in (
        "OPTIMAL",
        "FEASIBLE",
    )

    assert len(result.persons) == 1

    person = result.persons[0]

    assert person.interviewee == 0

    assert {
        interview.interview_type
        for interview in person.interviews
    } == {"A", "B", "C"}

    assert len(person.interviews) == 3

    validate_schedule(
        result,
        config,
    )


def test_solver_respects_room_capacity():
    config = SchedulerConfig(
        n_interviewees=4,
        horizon=300,
        break_time=5,
        travel_time=10,
        interview_types={
            "A": InterviewType(
                name="A",
                duration=30,
                ready=5,
                room_count=1,
                ready_occupies_room=True,
            ),
            "B": InterviewType(
                name="B",
                duration=20,
                ready=5,
                room_count=1,
                ready_occupies_room=False,
            ),
            "C": InterviewType(
                name="C",
                duration=40,
                ready=10,
                room_count=1,
                ready_occupies_room=True,
            ),
        },
    )

    scheduler = InterviewScheduler(config)

    result = scheduler.solve()

    assert result.status in (
        "OPTIMAL",
        "FEASIBLE",
    )

    validate_schedule(
        result,
        config,
    )

    # Each room has capacity 1.
    #
    # Therefore intervals assigned to the same room
    # must never overlap.
    for room_name in {
        room.room
        for room in result.rooms
    }:
        rooms = [
            room
            for room in result.rooms
            if room.room == room_name
        ]

        rooms.sort(
            key=lambda x: x.room_start
        )

        for previous, current in zip(
            rooms,
            rooms[1:],
        ):
            assert (
                previous.room_end
                <= current.room_start
            )


def test_ready_occupies_room_is_reflected_in_result(config):
    scheduler = InterviewScheduler(config)

    result = scheduler.solve()

    assert result.status in (
        "OPTIMAL",
        "FEASIBLE",
    )

    validate_schedule(
        result,
        config,
    )

    for room in result.rooms:

        interview = next(
            interview
            for person in result.persons
            for interview in person.interviews
            if (
                interview.interviewee
                == room.interviewee
                and interview.interview_type
                == room.interview_type
            )
        )

        interview_type = (
            config.interview_types[
                room.interview_type
            ]
        )

        if interview_type.ready_occupies_room:
            assert (
                room.room_start
                == interview.ready_start
            )
        else:
            assert (
                room.room_start
                == interview.start
            )


def test_ready_occupancy_changes_room_usage():
    """
    Verify that ready_occupies_room actually changes
    the room occupancy interval.

    We use two interviewees and only one interview type.
    """

    config = SchedulerConfig(
        n_interviewees=2,
        horizon=100,
        break_time=5,
        travel_time=0,
        interview_types={
            "A": InterviewType(
                name="A",
                duration=20,
                ready=10,
                room_count=1,
                ready_occupies_room=True,
            ),
        },
    )

    scheduler = InterviewScheduler(config)

    result = scheduler.solve()

    assert result.status in (
        "OPTIMAL",
        "FEASIBLE",
    )

    # The generic scheduler assumes every interviewee
    # must take every configured interview type.
    #
    # With only one type, there is no person-order
    # constraint between different interviews.
    #
    # Room capacity=1 and ready_occupies_room=True mean
    # the second person's room interval cannot overlap
    # the first person's ready + interview + break interval.
    validate_schedule(
        result,
        config,
    )

    rooms = sorted(
        result.rooms,
        key=lambda x: x.room_start,
    )

    assert len(rooms) == 2

    assert rooms[0].room_end <= rooms[1].room_start


def test_solver_returns_infeasible_for_too_small_horizon():
    config = SchedulerConfig(
        n_interviewees=1,
        horizon=120,
        break_time=5,
        travel_time=10,
        interview_types={
            "A": InterviewType(
                name="A",
                duration=30,
                ready=5,
                room_count=1,
                ready_occupies_room=True,
            ),
            "B": InterviewType(
                name="B",
                duration=20,
                ready=5,
                room_count=1,
                ready_occupies_room=False,
            ),
            "C": InterviewType(
                name="C",
                duration=40,
                ready=10,
                room_count=1,
                ready_occupies_room=True,
            ),
        },
    )

    scheduler = InterviewScheduler(config)

    result = scheduler.solve()

    assert result.status == "INFEASIBLE"

    assert result.objective is None
    assert result.persons == []
    assert result.rooms == []


def test_room_count_two_allows_parallel_execution():
    config = SchedulerConfig(
        n_interviewees=2,
        horizon=100,
        break_time=5,
        travel_time=0,
        interview_types={
            "A": InterviewType(
                name="A",
                duration=20,
                ready=10,
                room_count=2,
                ready_occupies_room=True,
            ),
        },
    )

    scheduler = InterviewScheduler(config)
    result = scheduler.solve()

    assert result.status in ("OPTIMAL", "FEASIBLE")

    validate_schedule(result, config)

    assert len(result.rooms) == 2

    # 두 면접이 같은 시간에 시작할 수 있어야 한다.
    room_starts = [
        room.room_start
        for room in result.rooms
    ]

    assert len(set(room_starts)) == 1

    # 서로 다른 room이 배정되어야 한다.
    assert len({
        room.room
        for room in result.rooms
    }) == 2


def test_room_count_two_never_exceeds_capacity():
    config = SchedulerConfig(
        n_interviewees=5,
        horizon=150,
        break_time=5,
        travel_time=0,
        interview_types={
            "A": InterviewType(
                name="A",
                duration=20,
                ready=10,
                room_count=2,
                ready_occupies_room=True,
            ),
        },
    )

    scheduler = InterviewScheduler(config)
    result = scheduler.solve()

    assert result.status in ("OPTIMAL", "FEASIBLE")

    validate_schedule(result, config)

    # 어떤 시점에서도 동시에 2개를 초과해서 room을
    # 사용할 수 없어야 한다.
    events = []

    for room in result.rooms:
        events.append(
            (room.room_start, +1)
        )
        events.append(
            (room.room_end, -1)
        )

    # 종료 이벤트를 시작 이벤트보다 먼저 처리한다.
    events.sort(
        key=lambda event: (
            event[0],
            event[1],
        )
    )

    active = 0

    for _, delta in events:
        active += delta

        assert active <= 2


def test_increasing_room_count_enables_parallel_execution():
    base_interview_type = dict(
        name="A",
        duration=20,
        ready=10,
        ready_occupies_room=True,
    )

    config_one_room = SchedulerConfig(
        n_interviewees=2,
        horizon=100,
        break_time=5,
        travel_time=0,
        interview_types={
            "A": InterviewType(
                **base_interview_type,
                room_count=1,
            ),
        },
    )

    config_two_rooms = SchedulerConfig(
        n_interviewees=2,
        horizon=100,
        break_time=5,
        travel_time=0,
        interview_types={
            "A": InterviewType(
                **base_interview_type,
                room_count=2,
            ),
        },
    )

    result_one_room = InterviewScheduler(
        config_one_room
    ).solve()

    result_two_rooms = InterviewScheduler(
        config_two_rooms
    ).solve()

    assert result_one_room.status == "OPTIMAL"
    assert result_two_rooms.status == "OPTIMAL"

    validate_schedule(
        result_one_room,
        config_one_room,
    )

    validate_schedule(
        result_two_rooms,
        config_two_rooms,
    )

    # room_count=1에서는 두 사람이 같은 room을 사용하므로
    # room occupancy가 겹칠 수 없다.
    one_room_starts = sorted(
        room.room_start
        for room in result_one_room.rooms
    )

    assert len(one_room_starts) == 2
    assert one_room_starts[0] < one_room_starts[1]

    # room_count=2에서는 두 room을 동시에 사용할 수 있으므로
    # 두 면접이 같은 시각에 시작할 수 있다.
    two_room_starts = [
        room.room_start
        for room in result_two_rooms.rooms
    ]

    assert len(two_room_starts) == 2
    assert len(set(two_room_starts)) == 1

    # 실제로 서로 다른 room이 배정되어야 한다.
    assert len({
        room.room
        for room in result_two_rooms.rooms
    }) == 2

