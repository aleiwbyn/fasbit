"""
Pruebas unitarias de la capa de programación funcional pura.
Verifica combinadores, inmutabilidad y agregaciones sin efectos secundarios.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from fasbit.domain.models import hhmm_to_minutes, minutes_to_hhmm
from fasbit.functional.pipeline import compose, pipe


def test_functional_pipe_and_compose() -> None:
    double = lambda x: x * 2
    inc = lambda x: x + 3
    square = lambda x: x * x

    # pipe: ((4 * 2) + 3)^2 = 121
    assert pipe(4, double, inc, square) == 121

    # compose: double(inc(square(4))) = double(inc(16)) = double(19) = 38
    fn = compose(double, inc, square)
    assert fn(4) == 38


def test_time_conversion_helpers() -> None:
    assert hhmm_to_minutes("07:15") == 435
    assert minutes_to_hhmm(435) == "07:15"
    assert minutes_to_hhmm(493.72) == "08:14"

    with pytest.raises(ValueError):
        hhmm_to_minutes("25:00")


def test_domain_models_are_immutable() -> None:
    from fasbit.services.planner_service import PlannerService

    task = PlannerService().generate_schedule()["tareas"][0]
    with pytest.raises(FrozenInstanceError):
        task.zona_asignada = "zona_modificada"  # type: ignore[misc]

