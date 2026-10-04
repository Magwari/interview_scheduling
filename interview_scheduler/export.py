"""
ScheduleResult / SchedulerConfig를 JSON 파일로 저장하는 모듈.
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    PersonSchedule,
    RoomSchedule,
    ScheduleResult,
    SchedulerConfig,
)

__version__ = "0.1.0"


def _datetime_to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _interview_schedule_to_dict(schedule) -> dict[str, Any]:
    return {
        "type": schedule.interview_type,
        "ready_start": schedule.ready_start,
        "start": schedule.start,
        "end": schedule.end,
        "room": schedule.room,
    }


def _person_to_dict(person: PersonSchedule) -> dict[str, Any]:
    return {
        "interviewee": person.interviewee,
        "first_start": person.first_start,
        "last_end": person.last_end,
        "stay": person.stay,
        "interviews": [
            _interview_schedule_to_dict(iv)
            for iv in person.interviews
        ],
    }


def _room_to_dict(room: RoomSchedule) -> dict[str, Any]:
    return {
        "room": room.room,
        "type": room.interview_type,
        "interviewee": room.interviewee,
        "room_start": room.room_start,
        "interview_start": room.interview_start,
        "interview_end": room.interview_end,
        "room_end": room.room_end,
    }


def _config_to_dict(config: SchedulerConfig) -> dict[str, Any]:
    return {
        "n_interviewees": config.n_interviewees,
        "start_time": _datetime_to_iso(config.start_time),
        "end_time": _datetime_to_iso(config.end_time),
        "break_time": config.break_time,
        "travel_time": config.travel_time,
        "interview_types": {
            name: {
                "name": it.name,
                "duration": it.duration,
                "ready": it.ready,
                "room_count": it.room_count,
                "ready_occupies_room": it.ready_occupies_room,
            }
            for name, it in config.interview_types.items()
        },
    }


def result_to_dict(
    result: ScheduleResult,
    config: SchedulerConfig,
) -> dict[str, Any]:
    """
    ScheduleResult와 SchedulerConfig를 JSON-serializable dict로 변환한다.
    """
    return {
        "meta": {
            "version": __version__,
            "solved_at": datetime.now().isoformat(),
            **_config_to_dict(config),
        },
        "status": result.status,
        "objective": result.objective,
        "persons": [
            _person_to_dict(p) for p in result.persons
        ],
        "rooms": [
            _room_to_dict(r) for r in result.rooms
        ],
    }


def save_json(
    result: ScheduleResult,
    config: SchedulerConfig,
    output_path: str | Path,
) -> Path:
    """
    ScheduleResult를 JSON 파일로 저장한다.

    Parameters
    ----------
    result :
        InterviewScheduler.solve()의 결과
    config :
        SchedulerConfig
    output_path :
        저장할 JSON 파일 경로.
        디렉터리가 없으면 자동 생성된다.

    Returns
    -------
    Path :
        저장된 파일의 경로
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = result_to_dict(result, config)

    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path