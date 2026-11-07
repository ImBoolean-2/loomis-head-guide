# SPDX-FileCopyrightText: 2025 lm0ss
# SPDX-FileCopyrightText: 2026 Nedeljko Umjetnik
# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

import math
from collections.abc import Sequence
from typing import TypeAlias

from .euclid import Matrix4, Quaternion, Vector2, Vector3

Poly2: TypeAlias = list[Vector2]
Poly3: TypeAlias = list[Vector3]
Segments3: TypeAlias = list[Poly3]
Mat3: TypeAlias = list[list[float]]


def normalize(v: Vector3) -> Vector3:
    n = v.magnitude()
    return v if n == 0.0 else v / n


def q_identity() -> Quaternion:
    return Quaternion(1.0, 0.0, 0.0, 0.0)


def q_normalize(q: Quaternion) -> Quaternion:
    return q.normalized()


def q_mul(b: Quaternion, a: Quaternion) -> Quaternion:
    return b * a


def q_axis_angle(axis_xyz: Vector3 | Sequence[float], angle_rad: float) -> Quaternion:
    if isinstance(axis_xyz, Vector3):
        ax = normalize(axis_xyz)
    else:
        ax = normalize(Vector3(*axis_xyz))
    return Quaternion.new_rotate_axis(angle_rad, ax)


def q_to_mat3(q: Quaternion) -> Mat3:
    m4: Matrix4 = q.get_matrix()
    r0 = [m4.a, m4.b, m4.c]
    r1 = [m4.e, m4.f, m4.g]
    r2 = [m4.i, m4.j, m4.k]
    return [r0, r1, r2]


def mat3_mul_vec(m: Mat3, v: Vector3) -> Vector3:
    return Vector3(
        m[0][0] * v.x + m[0][1] * v.y + m[0][2] * v.z,
        m[1][0] * v.x + m[1][1] * v.y + m[1][2] * v.z,
        m[2][0] * v.x + m[2][1] * v.y + m[2][2] * v.z,
    )


def linspace(start: float, stop: float, n: int, endpoint: bool = False) -> list[float]:
    if n <= 0:
        return []
    if n == 1:
        return [start]
    if endpoint:
        step = (stop - start) / (n - 1)
        return [start + i * step for i in range(n)]
    step = (stop - start) / n
    return [start + i * step for i in range(n)]


def angles_from_quaternion(q: Quaternion) -> tuple[float, float, float]:
    """Descompone la rotacion del cabezal en yaw/pitch/roll del trackball."""
    qn = q_normalize(q)
    fwd = mat3_mul_vec(q_to_mat3(qn), Vector3(0.0, 0.0, 1.0))
    yaw = math.atan2(fwd.x, fwd.z)
    pitch = math.asin(max(-1.0, min(1.0, -fwd.y)))
    q_turn = q_mul(
        q_axis_angle([0.0, 1.0, 0.0], yaw),
        q_axis_angle([1.0, 0.0, 0.0], pitch),
    )
    q_roll = q_mul(qn, q_turn.conjugated())
    angle, axis = q_roll.get_angle_axis()
    dot = axis.x * fwd.x + axis.y * fwd.y + axis.z * fwd.z
    return yaw, pitch, angle if dot >= 0 else -angle


def quaternion_from_angles(yaw: float, pitch: float, roll: float) -> Quaternion:
    """Compone la rotacion en el mismo orden que angles_from_quaternion."""
    q_turn = q_mul(
        q_axis_angle([0.0, 1.0, 0.0], yaw),
        q_axis_angle([1.0, 0.0, 0.0], pitch),
    )
    fwd = mat3_mul_vec(q_to_mat3(q_turn), Vector3(0.0, 0.0, 1.0))
    return q_normalize(q_mul(q_axis_angle(fwd, roll), q_turn))
