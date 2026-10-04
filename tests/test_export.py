import json
from datetime import datetime
from pathlib import Path

import pytest

from interview_scheduler.models import (
    InterviewSchedule,
    InterviewType,
    PersonSchedule,
    RoomSchedule,
    ScheduleResult,
    SchedulerConfig,
)
from interview_scheduler.export import result_to_dict, save_json


@pytest.fixture
def config():
    return SchedulerConfig(
        n_interviewees=2,
        start_time=datetime(2026, 10, 10, 9, 0),
        end_time=datetime(2026, 10, 10, 12, 0),
        break_time=5,
        travel_time=5,
        interview_types={
            "A": InterviewType(
                name="A", duration=30, ready=5, room_count=1
            ),
            "B": InterviewType(
                name="B", duration=20, ready=5, room_count=2
            ),
        },
    )


@pytest.fixture
def result(config):
    persons = [
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
                    ready_start=45,
                    start=50,
                    end=70,
                    room="B-1",
                ),
            ],
            first_start=0,
            last_end=70,
            stay=70,
        ),
        PersonSchedule(
            interviewee=1,
            interviews=[
                InterviewSchedule(
                    interviewee=1,
                    interview_type="A",
                    ready_start=40,
                    start=45,
                    end=75,
                    room="A-1",
                ),
                InterviewSchedule(
                    interviewee=1,
                    interview_type="B",
                    ready_start=85,
                    start=90,
                    end=110,
                    room="B-2",
                ),
            ],
            first_start=40,
            last_end=110,
            stay=70,
        ),
    ]

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
            room="A-1",
            interview_type="A",
            interviewee=1,
            room_start=40,
            interview_start=45,
            interview_end=75,
            room_end=80,
        ),
        RoomSchedule(
            room="B-1",
            interview_type="B",
            interviewee=0,
            room_start=50,
            interview_start=50,
            interview_end=70,
            room_end=75,
        ),
        RoomSchedule(
            room="B-2",
            interview_type="B",
            interviewee=1,
            room_start=90,
            interview_start=90,
            interview_end=110,
            room_end=115,
        ),
    ]

    return ScheduleResult(
        status="OPTIMAL",
        objective=70,
        persons=persons,
        rooms=rooms,
    )


class TestResultToDict:
    def test_top_level_keys(self, result, config):
        data = result_to_dict(result, config)
        assert set(data.keys()) == {"meta", "status", "objective", "persons", "rooms"}

    def test_meta_contains_config(self, result, config):
        data = result_to_dict(result, config)
        meta = data["meta"]
        assert meta["n_interviewees"] == 2
        assert meta["start_time"] == "2026-10-10T09:00:00"
        assert meta["end_time"] == "2026-10-10T12:00:00"
        assert meta["break_time"] == 5
        assert meta["travel_time"] == 5
        assert "version" in meta
        assert "solved_at" in meta

    def test_meta_interview_types(self, result, config):
        data = result_to_dict(result, config)
        types = data["meta"]["interview_types"]
        assert "A" in types
        assert "B" in types
        assert types["A"]["duration"] == 30
        assert types["A"]["ready"] == 5
        assert types["A"]["room_count"] == 1
        assert types["B"]["ready_occupies_room"] is False

    def test_status_and_objective(self, result, config):
        data = result_to_dict(result, config)
        assert data["status"] == "OPTIMAL"
        assert data["objective"] == 70

    def test_persons_structure(self, result, config):
        data = result_to_dict(result, config)
        persons = data["persons"]
        assert len(persons) == 2
        p0 = persons[0]
        assert p0["interviewee"] == 0
        assert p0["first_start"] == 0
        assert p0["last_end"] == 70
        assert p0["stay"] == 70
        assert len(p0["interviews"]) == 2

    def test_interview_fields(self, result, config):
        data = result_to_dict(result, config)
        iv = data["persons"][0]["interviews"][0]
        assert iv["type"] == "A"
        assert iv["ready_start"] == 0
        assert iv["start"] == 5
        assert iv["end"] == 35
        assert iv["room"] == "A-1"

    def test_rooms_structure(self, result, config):
        data = result_to_dict(result, config)
        rooms = data["rooms"]
        assert len(rooms) == 4
        r0 = rooms[0]
        assert r0["room"] == "A-1"
        assert r0["type"] == "A"
        assert r0["interviewee"] == 0
        assert r0["room_start"] == 0
        assert r0["interview_start"] == 5
        assert r0["interview_end"] == 35
        assert r0["room_end"] == 40

    def test_json_serializable(self, result, config):
        data = result_to_dict(result, config)
        # Must not raise
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

    def test_infeasible_result(self, config):
        result = ScheduleResult(
            status="INFEASIBLE",
            objective=None,
            persons=[],
            rooms=[],
        )
        data = result_to_dict(result, config)
        assert data["status"] == "INFEASIBLE"
        assert data["objective"] is None
        assert data["persons"] == []
        assert data["rooms"] == []


class TestSaveJson:
    def test_creates_file(self, result, config, tmp_path):
        output = tmp_path / "sub" / "schedule.json"
        saved = save_json(result, config, output)
        assert saved == output
        assert saved.exists()

    def test_file_content_valid_json(self, result, config, tmp_path):
        output = tmp_path / "schedule.json"
        save_json(result, config, output)
        with open(output, encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "OPTIMAL"
        assert len(data["persons"]) == 2
        assert len(data["rooms"]) == 4

    def test_roundtrip_matches_dict(self, result, config, tmp_path):
        output = tmp_path / "schedule.json"
        save_json(result, config, output)
        with open(output, encoding="utf-8") as f:
            file_data = json.load(f)
        # Compare structural fields (excluding volatile solved_at)
        dict_data = result_to_dict(result, config)
        assert file_data["status"] == dict_data["status"]
        assert file_data["objective"] == dict_data["objective"]
        assert file_data["persons"] == dict_data["persons"]
        assert file_data["rooms"] == dict_data["rooms"]

    def test_accepts_string_path(self, result, config, tmp_path):
        path_str = str(tmp_path / "out.json")
        saved = save_json(result, config, path_str)
        assert saved == Path(path_str)
        assert saved.exists()