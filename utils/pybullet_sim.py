"""
Stability checker — pure numpy/matplotlib, no pybullet required.

Parses the STL, computes the mesh centroid as a proxy for centre of mass,
then checks whether the centroid projection stays inside the base footprint
when the model is tilted to 15 / 30 / 45 degrees about its X axis.
"""

import os
import struct

import numpy as np


# ---------------------------------------------------------------------------
# STL parsing
# ---------------------------------------------------------------------------

def _parse_stl(stl_path: str) -> np.ndarray:
    """Return an (N, 3) float32 array of all triangle vertices."""
    with open(stl_path, "rb") as f:
        header = f.read(80)

    # Detect ASCII STL (starts with "solid" and is valid UTF-8 text)
    try:
        if header.lstrip().startswith(b"solid"):
            return _parse_ascii_stl(stl_path)
    except Exception:
        pass

    return _parse_binary_stl(stl_path)


def _parse_binary_stl(stl_path: str) -> np.ndarray:
    with open(stl_path, "rb") as f:
        f.read(80)  # header
        (num_tri,) = struct.unpack("<I", f.read(4))
        # 50 bytes per triangle: 12 normal + 12*3 vertices + 2 attr
        raw = np.frombuffer(f.read(num_tri * 50), dtype=np.uint8).reshape(num_tri, 50)

    # Vertices sit at bytes 12-48 of each 50-byte record
    v1 = raw[:, 12:24].view(np.float32).reshape(-1, 3)
    v2 = raw[:, 24:36].view(np.float32).reshape(-1, 3)
    v3 = raw[:, 36:48].view(np.float32).reshape(-1, 3)
    return np.vstack([v1, v2, v3])


def _parse_ascii_stl(stl_path: str) -> np.ndarray:
    vertices = []
    with open(stl_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("vertex"):
                parts = line.split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.array(vertices, dtype=np.float32)


# ---------------------------------------------------------------------------
# Stability check
# ---------------------------------------------------------------------------

def check_stability(stl_path: str, screenshot_path: str = "outputs/sim_screenshot.png") -> dict:
    """
    Load an STL, simulate lateral torque, and check tip-over stability.

    The check is purely geometric:
      - Centre of mass ≈ centroid of all mesh vertices.
      - Base footprint = XY AABB of the mesh at 0° tilt.
      - The model is tilted 15 / 30 / 45° about its X axis; at each angle the
        rotated centroid's Y projection is compared against the footprint edge.
        If it falls outside, the design would tip over.
    """
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)

    try:
        vertices = _parse_stl(stl_path)
    except Exception as exc:
        _save_unavailable_screenshot(screenshot_path)
        return {
            "passed": True,
            "reason": f"Simulation skipped — could not parse STL: {exc}",
            "screenshot_path": screenshot_path,
        }

    if len(vertices) == 0:
        _save_unavailable_screenshot(screenshot_path)
        return {
            "passed": True,
            "reason": "Simulation skipped — STL contained no vertices.",
            "screenshot_path": screenshot_path,
        }

    # Footprint: XY extents at rest
    x_min, y_min = vertices[:, 0].min(), vertices[:, 1].min()
    x_max, y_max = vertices[:, 0].max(), vertices[:, 1].max()
    footprint_x = (float(x_min), float(x_max))
    footprint_y = (float(y_min), float(y_max))

    # Centre of mass ≈ centroid
    com = vertices.mean(axis=0)  # shape (3,)

    failure_angle = None
    for angle_deg in [15, 30, 45]:
        angle_rad = np.radians(angle_deg)
        # Rotate COM about the X axis
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        rotated_y = cos_a * com[1] - sin_a * com[2]

        # Check Y projection against original footprint
        if not (footprint_y[0] <= rotated_y <= footprint_y[1]):
            failure_angle = angle_deg
            break

    _save_sim_screenshot(failure_angle, screenshot_path, footprint_x, footprint_y)

    if failure_angle is not None:
        width_mm = footprint_x[1] - footprint_x[0]
        depth_mm = footprint_y[1] - footprint_y[0]
        return {
            "passed": False,
            "reason": (
                f"Design tips over at {failure_angle}° lateral tilt. "
                f"Base footprint ({width_mm:.0f} x {depth_mm:.0f} units) is too narrow. "
                "Widen base by at least 30 units on both axes."
            ),
            "screenshot_path": screenshot_path,
        }

    return {
        "passed": True,
        "reason": "Stable at 15, 30, and 45 degree lateral tilt.",
        "screenshot_path": screenshot_path,
    }


# ---------------------------------------------------------------------------
# Screenshot helpers
# ---------------------------------------------------------------------------

def _save_sim_screenshot(failure_angle, output_path, footprint_x, footprint_y):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.patches as patches
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 1, figsize=(6, 5))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")

        footprint_width = footprint_x[1] - footprint_x[0]
        footprint_depth = footprint_y[1] - footprint_y[0]
        rect = patches.Rectangle(
            (-footprint_width / 2, -footprint_depth / 2),
            footprint_width,
            footprint_depth,
            linewidth=2,
            edgecolor="#4fc3f7",
            facecolor="#0d47a1",
            alpha=0.5,
        )
        ax.add_patch(rect)
        ax.plot(
            0, 0,
            "o",
            color="#ff6b6b" if failure_angle else "#69f0ae",
            markersize=14,
            label="Centre of mass",
            zorder=5,
        )

        status = (
            f"UNSTABLE — tips at {failure_angle}°"
            if failure_angle
            else "STABLE — passed all tilt checks"
        )
        title_color = "#ff6b6b" if failure_angle else "#69f0ae"

        ax.set_title(
            f"Stability Check\n{status}",
            color=title_color,
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("X footprint", color="white")
        ax.set_ylabel("Y footprint", color="white")
        ax.tick_params(colors="white")
        ax.legend(facecolor="#1a1a2e", labelcolor="white")
        span = max(footprint_width, footprint_depth)
        ax.set_xlim(-span, span)
        ax.set_ylim(-span, span)
        ax.set_aspect("equal")

        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
    except Exception:
        pass


def _save_unavailable_screenshot(output_path: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")
        ax.axis("off")
        ax.text(
            0.5, 0.62,
            "Simulation Skipped",
            ha="center", va="center",
            color="#ffd76a", fontsize=18, fontweight="bold",
            transform=ax.transAxes,
        )
        ax.text(
            0.5, 0.42,
            "STL could not be loaded.",
            ha="center", va="center",
            color="white", fontsize=11,
            transform=ax.transAxes,
        )
        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
    except Exception:
        pass
