from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class InterviewType:
    name: str
    duration: int
    ready: int
    room_count: int
    ready_occupies_room: bool = False


@dataclass(frozen=True)
class SchedulerConfig:
    n_interviewees: int
    horizon: int
    break_time: int
    travel_time: int
    interview_types: Dict[str, InterviewType]


@dataclass
class InterviewSchedule:
    interviewee: int
    interview_type: str

    ready_start: int
    start: int
    end: int

    room: str | None = None


@dataclass
class PersonSchedule:
    interviewee: int
    interviews: List[InterviewSchedule]

    first_start: int
    last_end: int
    stay: int


@dataclass
class RoomSchedule:
    room: str
    interview_type: str
    interviewee: int

    room_start: int
    interview_start: int
    interview_end: int
    room_end: int


@dataclass
class ScheduleResult:
    status: str
    objective: int | None
    persons: List[PersonSchedule]
    rooms: List[RoomSchedule]

def validate_result(result: ScheduleResult, config: SchedulerConfig):
    if result.status not in ("OPTIMAL", "FEASIBLE"):
        return

    assert len(result.persons) == config.n_interviewees

    expected_types = set(config.interview_types.keys())

    for person in result.persons:
        actual_types = {
            interview.interview_type
            for interview in person.interviews
        }

        assert actual_types == expected_types

        # Person overlap check
        interviews = sorted(
            person.interviews,
            key=lambda x: x.start,
        )

        for prev, curr in zip(interviews, interviews[1:]):
            assert prev.end <= curr.start, (
                f"Person {person.interviewee} has "
                f"overlapping interviews"
            )

        # Horizon check
        for interview in interviews:
            assert 0 <= interview.start
            assert interview.end <= config.horizon

        # Stay check
        first_start = min(
            x.start for x in interviews
        )
        last_end = max(
            x.end for x in interviews
        )

        assert person.first_start == first_start
        assert person.last_end == last_end
        assert person.stay == last_end - first_start
