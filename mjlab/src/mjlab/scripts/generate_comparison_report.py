"""Generate comparison report between RL and CPG baseline."""

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tyro


def load_results(result_file: Path) -> dict:
  """Load evaluation results from JSON file."""
  with open(result_file) as f:
    return json.load(f)


def create_comparison_plots(rl_results: dict, cpg_results: dict, output_dir: Path):
  """Create comparison plots."""
  fig, axes = plt.subplots(2, 2, figsize=(12, 10))
  fig.suptitle("RL Policy vs CPG Baseline Comparison", fontsize=16, fontweight="bold")

  metrics = [
    ("velocity_tracking_error", "Velocity Tracking Error (m/s)", axes[0, 0]),
    ("roll_rms", "Roll RMS (degrees)", axes[0, 1]),
    ("pitch_rms", "Pitch RMS (degrees)", axes[1, 0]),
    ("cost_of_transport", "Cost of Transport", axes[1, 1]),
  ]

  for metric_key, ylabel, ax in metrics:
    rl_data = rl_results["raw_data"][metric_key]
    cpg_data = cpg_results["raw_data"][metric_key]

    # Convert radians to degrees for roll/pitch
    if "rms" in metric_key:
      rl_data = [math.degrees(x) for x in rl_data]
      cpg_data = [math.degrees(x) for x in cpg_data]

    positions = [1, 2]
    data = [rl_data, cpg_data]
    labels = ["RL Policy", "CPG Baseline"]

    bp = ax.boxplot(data, positions=positions, labels=labels, patch_artist=True)

    # Color boxes
    colors = ["#3498db", "#e74c3c"]
    for patch, color in zip(bp["boxes"], colors):
      patch.set_facecolor(color)
      patch.set_alpha(0.7)

    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    # Add mean values as text
    for i, (pos, d) in enumerate(zip(positions, data)):
      mean_val = np.mean(d)
      ax.text(
        pos,
        ax.get_ylim()[1] * 0.95,
        f"μ={mean_val:.3f}",
        ha="center",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=colors[i], alpha=0.3),
      )

  plt.tight_layout()
  plt.savefig(output_dir / "comparison_plots.png", dpi=300, bbox_inches="tight")
  print(f"Saved comparison plots to {output_dir / 'comparison_plots.png'}")


def create_recovery_plot(rl_results: dict, cpg_results: dict, output_dir: Path):
  """Create push recovery comparison plot."""
  fig, ax = plt.subplots(figsize=(8, 6))

  rl_rate = rl_results["summary"]["push_recovery_rate"] * 100
  cpg_rate = cpg_results["summary"]["push_recovery_rate"] * 100

  bars = ax.bar(
    ["RL Policy", "CPG Baseline"],
    [rl_rate, cpg_rate],
    color=["#3498db", "#e74c3c"],
    alpha=0.7,
    edgecolor="black",
    linewidth=1.5,
  )

  ax.set_ylabel("Recovery Success Rate (%)", fontsize=12)
  ax.set_title("Push Recovery Robustness", fontsize=14, fontweight="bold")
  ax.set_ylim(0, 105)
  ax.grid(axis="y", alpha=0.3)

  # Add value labels on bars
  for bar, rate in zip(bars, [rl_rate, cpg_rate]):
    height = bar.get_height()
    ax.text(
      bar.get_x() + bar.get_width() / 2.0,
      height + 2,
      f"{rate:.1f}%",
      ha="center",
      va="bottom",
      fontsize=12,
      fontweight="bold",
    )

  plt.tight_layout()
  plt.savefig(output_dir / "recovery_comparison.png", dpi=300, bbox_inches="tight")
  print(f"Saved recovery plot to {output_dir / 'recovery_comparison.png'}")


def generate_markdown_report(
  rl_results: dict,
  cpg_results: dict,
  output_dir: Path,
  terrain: str,
  velocities: list[float],
):
  """Generate markdown comparison report."""
  report = f"""# Locomotion Controller Comparison Report

## Experimental Setup

- **Terrain**: {terrain}
- **Test Velocities**: {", ".join(f"{v} m/s" for v in velocities)}
- **Number of Trials**: {rl_results["summary"]["num_trials"]} per condition
- **Push Test**: {rl_results["config"]["push_force"]} N lateral force for 0.1s

## Results Summary

### Velocity Tracking Error (RMS)

| Controller | Mean (m/s) | Std Dev | Improvement |
|-----------|-----------|---------|-------------|
| **RL Policy** | {rl_results["summary"]["velocity_tracking_error_mean"]:.4f} | {rl_results["summary"]["velocity_tracking_error_std"]:.4f} | - |
| **CPG Baseline** | {cpg_results["summary"]["velocity_tracking_error_mean"]:.4f} | {cpg_results["summary"]["velocity_tracking_error_std"]:.4f} | {(1 - rl_results["summary"]["velocity_tracking_error_mean"] / cpg_results["summary"]["velocity_tracking_error_mean"]) * 100:.1f}% |

**Winner**: {"✅ RL Policy" if rl_results["summary"]["velocity_tracking_error_mean"] < cpg_results["summary"]["velocity_tracking_error_mean"] else "✅ CPG Baseline"}

### Body Stability

#### Roll RMS

| Controller | Mean (rad) | Mean (deg) | Std Dev |
|-----------|-----------|-----------|---------|
| **RL Policy** | {rl_results["summary"]["roll_rms_mean"]:.4f} | {math.degrees(rl_results["summary"]["roll_rms_mean"]):.2f}° | {rl_results["summary"]["roll_rms_std"]:.4f} |
| **CPG Baseline** | {cpg_results["summary"]["roll_rms_mean"]:.4f} | {math.degrees(cpg_results["summary"]["roll_rms_mean"]):.2f}° | {cpg_results["summary"]["roll_rms_std"]:.4f} |

#### Pitch RMS

| Controller | Mean (rad) | Mean (deg) | Std Dev |
|-----------|-----------|-----------|---------|
| **RL Policy** | {rl_results["summary"]["pitch_rms_mean"]:.4f} | {math.degrees(rl_results["summary"]["pitch_rms_mean"]):.2f}° | {rl_results["summary"]["pitch_rms_std"]:.4f} |
| **CPG Baseline** | {cpg_results["summary"]["pitch_rms_mean"]:.4f} | {math.degrees(cpg_results["summary"]["pitch_rms_mean"]):.2f}° | {cpg_results["summary"]["pitch_rms_std"]:.4f} |

**Winner**: {"✅ RL Policy" if (rl_results["summary"]["roll_rms_mean"] + rl_results["summary"]["pitch_rms_mean"]) < (cpg_results["summary"]["roll_rms_mean"] + cpg_results["summary"]["pitch_rms_mean"]) else "✅ CPG Baseline"}

### Energy Efficiency (Cost of Transport)

| Controller | Mean CoT | Std Dev | Improvement |
|-----------|---------|---------|-------------|
| **RL Policy** | {rl_results["summary"]["cost_of_transport_mean"]:.4f} | {rl_results["summary"]["cost_of_transport_std"]:.4f} | - |
| **CPG Baseline** | {cpg_results["summary"]["cost_of_transport_mean"]:.4f} | {cpg_results["summary"]["cost_of_transport_std"]:.4f} | {(1 - rl_results["summary"]["cost_of_transport_mean"] / cpg_results["summary"]["cost_of_transport_mean"]) * 100:.1f}% |

**Winner**: {"✅ RL Policy" if rl_results["summary"]["cost_of_transport_mean"] < cpg_results["summary"]["cost_of_transport_mean"] else "✅ CPG Baseline"}

*Lower CoT is better (less energy per unit distance)*

### Robustness (Push Recovery)

| Controller | Success Rate | Failures |
|-----------|-------------|----------|
| **RL Policy** | {rl_results["summary"]["push_recovery_rate"] * 100:.1f}% | {int((1 - rl_results["summary"]["push_recovery_rate"]) * rl_results["summary"]["num_trials"])} / {rl_results["summary"]["num_trials"]} |
| **CPG Baseline** | {cpg_results["summary"]["push_recovery_rate"] * 100:.1f}% | {int((1 - cpg_results["summary"]["push_recovery_rate"]) * cpg_results["summary"]["num_trials"])} / {cpg_results["summary"]["num_trials"]} |

**Winner**: {"✅ RL Policy" if rl_results["summary"]["push_recovery_rate"] > cpg_results["summary"]["push_recovery_rate"] else "✅ CPG Baseline"}

## Discussion

### RL Policy Strengths
"""

  # Analyze strengths
  rl_wins = 0
  if (
    rl_results["summary"]["velocity_tracking_error_mean"]
    < cpg_results["summary"]["velocity_tracking_error_mean"]
  ):
    report += "\n- **Better velocity tracking**: The RL policy learned to follow commanded velocities more accurately through reward shaping.\n"
    rl_wins += 1

  if (
    rl_results["summary"]["roll_rms_mean"] + rl_results["summary"]["pitch_rms_mean"]
  ) < (
    cpg_results["summary"]["roll_rms_mean"] + cpg_results["summary"]["pitch_rms_mean"]
  ):
    report += "\n- **Improved stability**: The policy maintains better body orientation, likely due to explicit stability rewards during training.\n"
    rl_wins += 1

  if (
    rl_results["summary"]["cost_of_transport_mean"]
    < cpg_results["summary"]["cost_of_transport_mean"]
  ):
    report += "\n- **Energy efficiency**: The learned gait is more energy-efficient, optimizing joint trajectories for minimal power consumption.\n"
    rl_wins += 1

  if (
    rl_results["summary"]["push_recovery_rate"]
    > cpg_results["summary"]["push_recovery_rate"]
  ):
    report += "\n- **Robustness**: Better disturbance rejection through learned feedback control and dynamic balance strategies.\n"
    rl_wins += 1

  report += """
### RL Policy Failure Modes

- **Sim-to-real gap**: Policy trained in simulation may not transfer perfectly to real hardware due to unmodeled dynamics.
- **Out-of-distribution behavior**: May fail on terrains or conditions not seen during training.
- **Computational requirements**: Requires neural network inference, which may be slower than simple CPG.

### CPG Baseline Strengths

- **Simplicity**: No training required, easy to implement and tune.
- **Predictability**: Deterministic behavior makes debugging easier.
- **Low computational cost**: Simple sinusoidal functions are fast to compute.
"""

  if (
    cpg_results["summary"]["velocity_tracking_error_mean"]
    < rl_results["summary"]["velocity_tracking_error_mean"]
  ):
    report += "- **Velocity tracking**: Open-loop trajectory may be well-tuned for specific speeds.\n"

  report += """
### CPG Baseline Failure Modes

- **No feedback**: Open-loop control cannot adapt to disturbances or terrain changes.
- **Manual tuning**: Requires hand-tuning of many parameters (frequency, amplitude, phase).
- **Limited adaptability**: Cannot adjust gait based on terrain or commanded velocity.
- **Poor disturbance rejection**: No feedback mechanism to recover from pushes or obstacles.

## Conclusion

"""

  if rl_wins >= 3:
    report += f"""The **RL policy significantly outperforms** the CPG baseline, winning in {rl_wins}/4 metrics.
The learned policy demonstrates superior velocity tracking, stability, energy efficiency, and robustness.
This validates the effectiveness of reinforcement learning for quadruped locomotion control.

**Recommendation**: Deploy the RL policy for real-world applications, with careful sim-to-real transfer validation.
"""
  elif rl_wins >= 2:
    report += f"""The **RL policy shows moderate improvement** over the CPG baseline, winning in {rl_wins}/4 metrics.
While the learned policy has advantages in some areas, the CPG baseline remains competitive.

**Recommendation**: Use RL policy for complex terrains and dynamic tasks; CPG may suffice for simple flat-ground locomotion.
"""
  else:
    report += f"""The **CPG baseline is competitive** with the RL policy, with RL winning only {rl_wins}/4 metrics.
This suggests either the RL training needs improvement or the CPG is well-tuned for this task.

**Recommendation**: Investigate RL training (reward shaping, hyperparameters) or consider hybrid approaches.
"""

  report += """
## Visualizations

![Comparison Plots](comparison_plots.png)

![Recovery Comparison](recovery_comparison.png)

---

*Report generated automatically from evaluation results*
"""

  report_file = output_dir / "comparison_report.md"
  with open(report_file, "w") as f:
    f.write(report)

  print(f"Generated report: {report_file}")


def main(
  rl_result: str,
  cpg_result: str,
  output_dir: str = "evaluation_results",
  terrain: str = "flat",
  velocities: str = "1.0,1.5",
):
  """Generate comparison report from evaluation results.

  Args:
    rl_result: Path to RL evaluation JSON file.
    cpg_result: Path to CPG evaluation JSON file.
    output_dir: Output directory for report.
    terrain: Terrain type tested.
    velocities: Comma-separated list of test velocities.
  """
  output_path = Path(output_dir)
  output_path.mkdir(parents=True, exist_ok=True)

  # Load results
  rl_results = load_results(Path(rl_result))
  cpg_results = load_results(Path(cpg_result))

  # Parse velocities
  vel_list = [float(v.strip()) for v in velocities.split(",")]

  # Generate plots
  create_comparison_plots(rl_results, cpg_results, output_path)
  create_recovery_plot(rl_results, cpg_results, output_path)

  # Generate markdown report
  generate_markdown_report(rl_results, cpg_results, output_path, terrain, vel_list)

  print("\n✅ Comparison report generated successfully!")
  print(f"📁 Output directory: {output_path}")
  print(f"📄 Report: {output_path / 'comparison_report.md'}")


if __name__ == "__main__":
  tyro.cli(main)
