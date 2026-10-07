# interview-scheduler

[OR-Tools](https://developers.google.com/optimization) 기반 면접 스케줄링 패키지입니다.
여러 면접자·면접 유형·면접실 제약 조건을 만족하면서 모든 지원자의 최대 체류 시간(stay)을 최소화하는
시간표 배정을 Constraint Programming으로 풀고, 결과를 검증·시각화합니다.

## 주요 기능

- `InterviewScheduler`: CP-SAT 기반 스케줄링 솔버
- `SchedulerConfig` / `InterviewType`: 제약·파라미터 모델
- `validate_schedule`: 결과 일관성 검증 (person/room/stay/horizon)
- `plot_gantt`: 면접자·면접실 기준 Gantt chart 시각화 (matplotlib)
- `save_json` / `result_to_dict`: 결과를 JSON 파일로 저장
- `visualization/`: 브라우저 기반 인터랙티브 시각화 페이지 (HTML/CSS/JS)

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

## 옵션 및 파라미터 설명

### `SchedulerConfig`

| 옵션 | 유형 | 설명 |
|------|------|------|
| `n_interviewees` | `int` | 지원자(면접자) 수. 각 지원자는 모든 면접 유형을 정확히 1회씩 받습니다. |
| `start_time` | `datetime` | 스케줄 시작 시각. 모든 시간 offset은 이 시각을 기준(0분)으로 계산됩니다. |
| `end_time` | `datetime` | 스케줄 종료 시각. `end_time - start_time`이 전체 시간 창(horizon)을 정의합니다. (분 단위 정수여야 함) |
| `travel_time` | `int` | **이동 시간(분)**. 지원자 기준, 하나의 면접이 끝나고 다음 면접(ready)을 시작하기까지 최소 이만큼의 이동 시간이 필요합니다. |
| `interview_types` | `Dict[str, InterviewType]` | 사용할 면접 유형들의 매핑. 키는 유형 이름(예: "A", "B", "C")입니다. |

### `InterviewType`

| 옵션 | 유형 | 설명 |
|------|------|------|
| `duration` | `int` | **면접 진행 시간(분)**. 실제 면접이 진행되는 시간입니다. |
| `ready` | `int` | **준비 시간(분)**. 면접 시작 전에 필요한 준비(예: 입장 대기, 서류 확인) 시간입니다. `ready_start + ready = start`가 성립합니다. |
| `room_count` | `int` | **면접실 수**. 동시에 이 유형의 면접을 진행할 수 있는 면접실의 최대 수입니다. (Cumulative constraint) |
| `break_time` | `int` | **면접 후 휴식 시간(분)**. 이 유형의 면접이 끝나면 다음 면접 시작까지 최소 이만큼의 휴식이 필요합니다. 면접실 기준으로는 interview 종료 후 break_time만큼 추가 점유(cooldown)됩니다. |
| `ready_occupies_room` | `bool` | **ready 구간이 면접실을 점유하는지 여부**. `True`이면 ready 시작부터 면접실 점유 시작, `False`이면 실제 면접(start)부터 점유 시작. |

### 시간 관계 예시

```
ready_start ──ready──▶ start ──────duration──────▶ end
|<── 준비 시간 ──>|<──────── 면접 진행 ──────────>|

break_time:  end ──▶ (해당 면접 타입의 break_time, 다음 면접 시작까지 휴식)
travel_time: end + break + travel ──▶ (다음 면접 ready 시작 가능)
```

### `ready_occupies_room` 동작

| 값 | 면접실 점유 구간 |
|----|----------------|
| `True` | `ready_start` ~ `end + break_time` (ready + 면접 + break) |
| `False` | `start` ~ `end + break_time` (면접 + break) |

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
    travel_time=5,
    interview_types={
        "면접 A": InterviewType(duration=30, ready=5, room_count=1, break_time=5),
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

## 시각화 (Visualization)

`visualization/` 폴더에 브라우저 기반 인터랙티브 시각화 페이지가 제공됩니다.
외부 라이브러리 없이 순수 HTML/CSS/JS로 작성되어, 브라우저에서 즉시 열 수 있습니다.

### 사용 방법

1. `output/` 폴더의 `interview_schedule.json`을 생성 (CLI 또는 Python API 사용)
2. `visualization/index.html`을 브라우저로 열기
3. JSON 파일을 드래그하거나 클릭하여 업로드
4. 통계 카드 + 지원자별/면접실별 Gantt 타임라인이 자동 렌더링

```bash
# Windows
start visualization\index.html

# macOS / Linux
open visualization/index.html
# 또는
xdg-open visualization/index.html
```

### 표시 내용

| 영역 | 내용 |
|------|------|
| **통계 카드** | Status, 지원자 수, 면접실 수, 총 면접 수, 평균 체류 시간, Objective |
| **타입별 통계** | 각 유형별 면접 수, 면접실 수, 총 사용 시간 |
| **지원자별 타임라인** | Interviewee 0~N, first_start 순 정렬, 타입별 색상 바 (A=파랑, B=초록, C=주황), Ready 구간 연색 표시 |
| **면접실별 타임라인** | 실명 순 정렬, Prep/Interview/Break 구간 구분, 각 바에 면접자 ID 표시 |


### 파일 구조

```
visualization/
├── index.html   # 메인 페이지 (업로드 UI + 통계 + Gantt 컨테이너)
├── style.css    # 스타일 (색상 체계, Gantt 바, 통계 카드, 반응형)
└── app.js       # JSON 파싱, 통계 렌더링, Gantt DOM 생성
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
├── gantt.py         # matplotlib 시각화
├── export.py        # JSON 직렬화/저장
└── example.py       # 데모 / CLI 진입점

visualization/
├── index.html       # 브라우저 시각화 페이지
├── style.css        # 스타일
└── app.js           # 렌더링 로직
```
