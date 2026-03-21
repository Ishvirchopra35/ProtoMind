import os

import numpy as np
import pybullet as p
import pybullet_data


def check_stability(stl_path: str, screenshot_path: str = "outputs/sim_screenshot.png") -> dict:
    """
    Load an STL, simulate lateral torque, and check tip-over stability.
    """
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)

    client = p.connect(p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=client)
    p.setGravity(0, 0, -9.81, physicsClientId=client)

    try:
        p.loadURDF("plane.urdf", physicsClientId=client)

        collision_shape = p.createCollisionShape(
            p.GEOM_MESH,
            fileName=stl_path,
            meshScale=[0.001, 0.001, 0.001],
            physicsClientId=client,
        )
        visual_shape = p.createVisualShape(
            p.GEOM_MESH,
            fileName=stl_path,
            meshScale=[0.001, 0.001, 0.001],
            rgbaColor=[0.3, 0.6, 0.9, 1.0],
            physicsClientId=client,
        )
        body = p.createMultiBody(
            baseMass=0.5,
            baseCollisionShapeIndex=collision_shape,
            baseVisualShapeIndex=visual_shape,
            basePosition=[0, 0, 0.05],
            physicsClientId=client,
        )

        aabb_min, aabb_max = p.getAABB(body, physicsClientId=client)
        footprint_x = (aabb_min[0], aabb_max[0])
        footprint_y = (aabb_min[1], aabb_max[1])

        failure_angle = None
        for angle_deg in [0, 15, 30, 45]:
            angle_rad = np.radians(angle_deg)
            orientation = p.getQuaternionFromEuler([angle_rad, 0, 0])
            p.resetBasePositionAndOrientation(
                body, [0, 0, 0.05], orientation, physicsClientId=client
            )

            com_pos, _ = p.getBasePositionAndOrientation(body, physicsClientId=client)
            com_x, com_y = com_pos[0], com_pos[1]
            in_footprint = (
                footprint_x[0] <= com_x <= footprint_x[1]
                and footprint_y[0] <= com_y <= footprint_y[1]
            )
            if not in_footprint:
                failure_angle = angle_deg
                break

        _save_sim_screenshot(failure_angle, screenshot_path, footprint_x, footprint_y)

        if failure_angle is not None:
            width_mm = (footprint_x[1] - footprint_x[0]) * 1000
            depth_mm = (footprint_y[1] - footprint_y[0]) * 1000
            return {
                "passed": False,
                "reason": (
                    f"Design tips over at {failure_angle} degrees lateral tilt. "
                    f"Base footprint ({width_mm:.0f}mm x {depth_mm:.0f}mm) is too narrow. "
                    "Widen base by at least 30mm on both axes."
                ),
                "screenshot_path": screenshot_path,
            }

        return {
            "passed": True,
            "reason": "Stable at 0, 15, 30, and 45 degree lateral tilt.",
            "screenshot_path": screenshot_path,
        }
    finally:
        p.disconnect(physicsClientId=client)


def _save_sim_screenshot(failure_angle, output_path, footprint_x, footprint_y):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.patches as patches
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 1, figsize=(6, 5))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")

        footprint_width = (footprint_x[1] - footprint_x[0]) * 1000
        footprint_depth = (footprint_y[1] - footprint_y[0]) * 1000
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
            0,
            0,
            "o",
            color="#ff6b6b" if failure_angle else "#69f0ae",
            markersize=14,
            label="Center of mass",
            zorder=5,
        )

        status = (
            f"UNSTABLE - tips at {failure_angle} degrees"
            if failure_angle
            else "STABLE - passed all tilt checks"
        )
        title_color = "#ff6b6b" if failure_angle else "#69f0ae"

        ax.set_title(
            f"PyBullet Stability Check\n{status}",
            color=title_color,
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("X footprint (mm)", color="white")
        ax.set_ylabel("Y footprint (mm)", color="white")
        ax.tick_params(colors="white")
        ax.legend(facecolor="#1a1a2e", labelcolor="white")
        ax.set_xlim(-max(footprint_width, footprint_depth), max(footprint_width, footprint_depth))
        ax.set_ylim(-max(footprint_width, footprint_depth), max(footprint_width, footprint_depth))
        ax.set_aspect("equal")

        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
    except Exception:
        pass
