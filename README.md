# interview-scheduler

[OR-Tools](https://developers.google.com/optimization) 기반 면접 스케줄링 패키지입니다.
여러 면접자·면접 유형·면접실 제약 조건을 만족하면서 모든 지원자의 최대 체류 시간(stay)을 최소화하는
시간표 배정을 Constraint Programming으로 풀고, 결과를 검증·시각화합니다.

## 주요 기능

- `InterviewScheduler`: CP-SAT 기반 스케줄링 솔버
- `SchedulerConfig` / `InterviewType`: 제약·파라미터 모델
- `validate_schedule`: 결과 일관성 검증 (person/room/stay/horizon)
- `plot_gantt`: 면접자·면접실 기준 Gantt chart 시각화
- `save_json` / `result_to_dict`: 결과를 JSON 파일로 저장

## 요구 사항

- Python 3.10 이상
- `ortools`, `matplotlib`

## 설치

개발/테스트 포함 설치(권장):

```bash
pip install -e ".[dev]"
```

runtime만 설치:

```bash
pip install -e .
```

## 사용 예

```python
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
        "A": InterviewType(name="A", duration=30, ready=5, room_count=1),
    },
)

result = InterviewScheduler(config).solve(time_limit=10.0)
validate_schedule(result, config)
print(result.status, result.objective)
```

### Gantt chart 저장

```python
from interview_scheduler import plot_gantt

plot_gantt(result, config, output_path="output/schedule.png", show=False)
```

### JSON 저장

```python
from interview_scheduler import save_json, result_to_dict

# 파일로 저장
save_json(result, config, output_path="output/schedule.json")

# dict로 변환 (직렬화)
data = result_to_dict(result, config)
```

### CLI 실행

`example.py`의 데모를 실행:

```bash
interview-scheduler
```

## 테스트

```bash
python -m pytest
```

## 패키지 구조

```
interview_scheduler/
├── __init__.py      # public API 재-export
├── models.py        # 데이터 모델
├── solver.py        # CP-SAT 모델 & solve
├── assignment.py    # room 배정
├── validate.py      # 결과 검증
├── gantt.py         # 시각화
├── export.py        # JSON 직렬화/저장
└── example.py       # 데모 / CLI 진입점
```
