from ortools.sat.python import cp_model

from .assignment import assign_rooms
from .models import (
    InterviewSchedule,
    PersonSchedule,
    ScheduleResult,
    SchedulerConfig,
)


class InterviewScheduler:
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self.model = cp_model.CpModel()

        self.types = list(config.interview_types.keys())
        self.n = config.n_interviewees

        # --------------------------------------------------
        # Interview variables
        # --------------------------------------------------

        self.ready_start = {}
        self.start = {}
        self.end = {}

        self.intervals = {}
        self.room_intervals = {}

        # --------------------------------------------------
        # Person objective variables
        # --------------------------------------------------

        self.first_start = {}
        self.last_end = {}
        self.stay = {}

        self.max_stay = None

        # --------------------------------------------------
        # Build
        # --------------------------------------------------

        self._build_model()

    def _build_model(self):
        self._create_interview_variables()
        self._add_room_constraints()
        self._add_person_constraints()
        self._add_stay_objective()

    # ======================================================
    # Interview variables
    # ======================================================
    def _create_interview_variables(self):
        for i in range(self.n):
            for type_name in self.types:
                interview_type = self.config.interview_types[type_name]

                ready = interview_type.ready
                duration = interview_type.duration
                break_time = interview_type.break_time

                # --------------------------------------------------
                # Ready start
                # --------------------------------------------------

                ready_start = self.model.new_int_var(
                    0,
                    self.config.horizon - ready,
                    f"ready_start_{i}_{type_name}",
                )

                # --------------------------------------------------
                # Actual interview start
                # --------------------------------------------------

                start = self.model.new_int_var(
                    0,
                    self.config.horizon - duration,
                    f"start_{i}_{type_name}",
                )

                self.model.add(
                    start == ready_start + ready
                )

                # --------------------------------------------------
                # Actual interview end
                # --------------------------------------------------

                end = self.model.new_int_var(
                    0,
                    self.config.horizon,
                    f"end_{i}_{type_name}",
                )

                interval = self.model.new_interval_var(
                    start,
                    duration,
                    end,
                    f"interval_{i}_{type_name}",
                )

                # --------------------------------------------------
                # Room occupancy
                # --------------------------------------------------

                if interview_type.ready_occupies_room:
                    room_start = ready_start
                else:
                    room_start = start

                # Room occupancy duration:
                #
                #   ready_occupies_room=True
                #       ready + interview + break
                #
                #   ready_occupies_room=False
                #       interview + break
                #
                if interview_type.ready_occupies_room:
                    room_duration = (
                        ready
                        + duration
                        + break_time
                    )
                else:
                    room_duration = (
                        duration
                        + break_time
                    )

                room_end = self.model.new_int_var(
                    0,
                    self.config.horizon + break_time,
                    f"room_end_{i}_{type_name}",
                )

                self.model.add(
                    room_end == room_start + room_duration
                )

                room_interval = self.model.new_interval_var(
                    room_start,
                    room_duration,
                    room_end,
                    f"room_interval_{i}_{type_name}",
                )

                # --------------------------------------------------
                # Store variables
                # --------------------------------------------------

                self.ready_start[i, type_name] = ready_start
                self.start[i, type_name] = start
                self.end[i, type_name] = end

                self.intervals[i, type_name] = interval
                self.room_intervals[i, type_name] = room_interval

    # ======================================================
    # Room constraints
    #
    # 아직 ready_occupies_room은 적용하지 않는다.
    # 현재는 실제 interview duration만 room을 점유한다.
    # ======================================================

    def _add_room_constraints(self):
        for type_name in self.types:
            interview_type = self.config.interview_types[type_name]

            intervals = [
                self.room_intervals[i, type_name]
                for i in range(self.n)
            ]

            self.model.add_cumulative(
                intervals,
                [1] * self.n,
                interview_type.room_count,
            )

    # ======================================================
    # Person constraints
    # ======================================================

    def _add_person_constraints(self):
        for i in range(self.n):

            for index_a in range(len(self.types)):
                for index_b in range(
                    index_a + 1,
                    len(self.types),
                ):
                    type_a = self.types[index_a]
                    type_b = self.types[index_b]

                    # True:
                    #   A -> B
                    #
                    # False:
                    #   B -> A
                    a_before_b = self.model.new_bool_var(
                        f"{i}_{type_a}_before_{type_b}"
                    )

                    # break는 끝난(이전) 면접 타입에 속한다.
                    break_a = (
                        self.config.interview_types[type_a].break_time
                    )
                    break_b = (
                        self.config.interview_types[type_b].break_time
                    )

                    # --------------------------------------------------
                    # A -> B
                    #
                    # B의 ready 시작은
                    #
                    # A 종료
                    # + break
                    # + travel
                    #
                    # 이후
                    # --------------------------------------------------

                    self.model.add(
                        self.ready_start[i, type_b]
                        >=
                        self.end[i, type_a]
                        + break_a
                        + self.config.travel_time
                    ).only_enforce_if(a_before_b)

                    # --------------------------------------------------
                    # B -> A
                    # --------------------------------------------------

                    self.model.add(
                        self.ready_start[i, type_a]
                        >=
                        self.end[i, type_b]
                        + break_b
                        + self.config.travel_time
                    ).only_enforce_if(
                        a_before_b.Not()
                    )

    # ======================================================
    # Stay objective
    # ======================================================

    def _add_stay_objective(self):
        for i in range(self.n):

            first_start = self.model.new_int_var(
                0,
                self.config.horizon,
                f"first_start_{i}",
            )

            last_end = self.model.new_int_var(
                0,
                self.config.horizon,
                f"last_end_{i}",
            )

            stay = self.model.new_int_var(
                0,
                self.config.horizon,
                f"stay_{i}",
            )

            # 이제 first_start는 실제 면접 시작이 아니라
            # ready 시작이다.
            self.model.add_min_equality(
                first_start,
                [
                    self.ready_start[i, type_name]
                    for type_name in self.types
                ],
            )

            self.model.add_max_equality(
                last_end,
                [
                    self.end[i, type_name]
                    for type_name in self.types
                ],
            )

            self.model.add(
                stay == last_end - first_start
            )

            self.first_start[i] = first_start
            self.last_end[i] = last_end
            self.stay[i] = stay

        self.max_stay = self.model.new_int_var(
            0,
            self.config.horizon,
            "max_stay",
        )

        for i in range(self.n):
            self.model.add(
                self.max_stay >= self.stay[i]
            )

        self.model.minimize(self.max_stay)

    # ======================================================
    # Solve
    # ======================================================

    def solve(
        self,
        time_limit: float = 30.0,
    ) -> ScheduleResult:

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit

        status = solver.solve(self.model)

        if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        ):
            return ScheduleResult(
                status=solver.status_name(status),
                objective=None,
                persons=[],
                rooms=[],
            )

        persons = []

        for i in range(self.n):

            interviews = []

            for type_name in self.types:

                interviews.append(
                    InterviewSchedule(
                        interviewee=i,
                        interview_type=type_name,
                        ready_start=solver.value(
                            self.ready_start[i, type_name]
                        ),
                        start=solver.value(
                            self.start[i, type_name]
                        ),
                        end=solver.value(
                            self.end[i, type_name]
                        ),
                    )
                )

            interviews.sort(
                key=lambda x: x.ready_start
            )

            persons.append(
                PersonSchedule(
                    interviewee=i,
                    interviews=interviews,
                    first_start=solver.value(
                        self.first_start[i]
                    ),
                    last_end=solver.value(
                        self.last_end[i]
                    ),
                    stay=solver.value(
                        self.stay[i]
                    ),
                )
            )

        # 현재 room assignment는
        # 실제 interview interval만 고려한다.
        room_schedules = assign_rooms(
            persons,
            self.config,
        )

        return ScheduleResult(
            status=solver.status_name(status),
            objective=solver.value(
                self.max_stay
            ),
            persons=persons,
            rooms=room_schedules,
        )