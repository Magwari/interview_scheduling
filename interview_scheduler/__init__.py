"""
interview_scheduler

OR-Tools 기반 면접 스케줄링 패키지.

주요 사용 예:

    from datetime import datetime

    from interview_scheduler import (
        InterviewScheduler,
        InterviewType,
        SchedulerConfig,
        validate_schedule,
    )

    config = SchedulerConfig(
        n_interviewees=2,
        start_time=datetime(2026, 10, 10, 9, 0),
        end_time=datetime(2026, 10, 10, 12, 0),
        break_time=5,
        travel_time=5,
        interview_types={
            "A": InterviewType(
                name="A",
                duration=30,
                ready=5,
                room_count=1,
            ),
        },
    )

    result = InterviewScheduler(config).solve()
    validate_schedule(result, config)
"""

from .models import (
    InterviewSchedule,
    InterviewType,
    PersonSchedule,
    RoomSchedule,
    ScheduleResult,
    SchedulerConfig,
)
from .assignment import assign_rooms
from .solver import InterviewScheduler
from .validate import (
    ScheduleValidationError,
    validate_schedule,
)
from .gantt import plot_gantt
from .export import save_json, result_to_dict

__version__ = "0.1.0"

__all__ = [
    "InterviewScheduler",
    "InterviewSchedule",
    "InterviewType",
    "PersonSchedule",
    "RoomSchedule",
    "ScheduleResult",
    "SchedulerConfig",
    "ScheduleValidationError",
    "assign_rooms",
    "validate_schedule",
    "plot_gantt",
    "save_json",
    "result_to_dict",
    "__version__",
]
