#!/usr/bin/env python3
"""Generate summary table from evaluation results.

Usage:
    python src/mjlab/scripts/generate_summary_table.py
"""

import json
import math
from pathlib import Path


def load_all_results(results_dir: Path) -> dict:
  """Load all evaluation results from the results directory.

  Args:
      results_dir: Path to evaluation_results/comprehensive.

  Returns:
      Dictionary of all results.
  """
  all_results = {}

  if not results_dir.exists():
    print(f"Results directory not found: {results_dir}")
    return all_results

  for config_dir in results_dir.iterdir():
    if not config_dir.is_dir():
      continue

    # Find all JSON result files
    for result_file in config_dir.glob("eval_*.json"):
      with open(result_file) as f:
        data = json.load(f)

      task = data["config"]["task"]
      checkpoint = data["config"]["checkpoint"]
      checkpoint_name = data["config"]["checkpoint_name"]

      key = (task, checkpoint_name)
      all_results[key] = data

  return all_results


def format_metric(value: float, std: float, unit: str = "", decimals: int = 3) -> str:
  """Format a metric as 'mean ± std'."""
  return f"{value:.{decimals}f} ± {std:.{decimals}f} {unit}".strip()


def generate_table(all_results: dict) -> str:
  """Generate formatted summary table.

  Args:
      all_results: Dictionary of all results.

  Returns:
      Formatted table string.
  """
  lines = []

  # Title
  lines.append("\n" + "=" * 140)
  lines.append(" " * 40 + "COMPREHENSIVE EVALUATION RESULTS")
  lines.append("=" * 140)

  # Table header
  header = (
    f"{'Configuration':<35} "
    f"{'Command':<12} "
    f"{'Vel Error (m/s)':<18} "
    f"{'Roll (°)':<14} "
    f"{'Pitch (°)':<14} "
    f"{'CoT':<12} "
    f"{'Recovery':<15}"
  )
  lines.append("")
  lines.append(header)
  lines.append("-" * 140)

  # Group results by task
  by_task = {}
  for (task, checkpoint), data in all_results.items():
    if task not in by_task:
      by_task[task] = []
    by_task[task].append((checkpoint, data))

  for task, configs in by_task.items():
    lines.append(f"\n### {task}")

    for checkpoint, data in configs:
      # Extract task type from task name
      if "Flat" in task:
        task_type = "Flat"
      elif "Slope" in task:
        task_type = "Slope"
      else:
        task_type = "Unknown"

      checkpoint_short = checkpoint.replace("model_", "").replace(".pt", "")
      config_name = f"[{task_type}] {checkpoint_short}"

      for cmd_key, cmd_results in data["results"].items():
        metrics = cmd_results["metrics"]
        n = metrics.get("num_trials", 0)

        # Velocity error
        vel_err = format_metric(
          metrics["velocity_tracking_error_mean"],
          metrics["velocity_tracking_error_std"],
          decimals=3,
        )

        # Roll in degrees
        roll_mean_deg = math.degrees(metrics["roll_rms_mean"])
        roll_std_deg = math.degrees(metrics["roll_rms_std"])
        roll = format_metric(roll_mean_deg, roll_std_deg, "°", decimals=2)

        # Pitch in degrees
        pitch_mean_deg = math.degrees(metrics["pitch_rms_mean"])
        pitch_std_deg = math.degrees(metrics["pitch_rms_std"])
        pitch = format_metric(pitch_mean_deg, pitch_std_deg, "°", decimals=2)

        # Cost of Transport
        cot = format_metric(
          metrics["cost_of_transport_mean"],
          metrics["cost_of_transport_std"],
          decimals=4,
        )

        # Recovery rate
        recovery_rate = metrics["push_recovery_rate"]
        recovery_count = metrics["push_recovery_count"]
        recovery = f"{recovery_rate:.0%} ({recovery_count}/{n})"

        line = (
          f"{config_name:<35} "
          f"{cmd_key:<12} "
          f"{vel_err:<18} "
          f"{roll:<14} "
          f"{pitch:<14} "
          f"{cot:<12} "
          f"{recovery:<15}"
        )
        lines.append(line)

  lines.append("\n" + "=" * 140)

  # Add legend
  lines.append("\nMETRICS EXPLANATION:")
  lines.append("  - Vel Error: RMS velocity tracking error (m/s)")
  lines.append("  - Roll/Pitch: RMS body orientation stability (degrees)")
  lines.append("  - CoT: Cost of Transport = total_energy / (mass * g * distance)")
  lines.append("  - Recovery: Push recovery success rate (lateral push test)")
  lines.append("\nCONFIGURATION EXPLANATION:")
  lines.append("  - Flat: Trained on flat terrain (100 iterations)")
  lines.append("  - Slope: Trained on slope terrain (300 iterations)")
  lines.append("  - Command: (vx, vy) in m/s")
  lines.append("=" * 140)

  return "\n".join(lines)


def generate_latex_table(all_results: dict) -> str:
  """Generate LaTeX table for the results.

  Args:
      all_results: Dictionary of all results.

  Returns:
      LaTeX table string.
  """
  lines = []

  lines.append("\\begin{table}[h]")
  lines.append("\\centering")
  lines.append("\\caption{Comprehensive Evaluation Results}")
  lines.append("\\begin{tabular}{l|c|c|c|c|c}")
  lines.append("\\hline")
  lines.append("Config & Command & Vel Error & Roll & Pitch & CoT & Recovery \\\\")
  lines.append(" & (m/s) & (°) & (°) & & \\\\")
  lines.append("\\hline")

  for (task, checkpoint), data in all_results.items():
    for cmd_key, cmd_results in data["results"].items():
      metrics = cmd_results["metrics"]

      if "Flat" in task:
        task_type = "Flat"
      elif "Slope" in task:
        task_type = "Slope"
      else:
        task_type = "Unknown"

      checkpoint_short = checkpoint.replace("model_", "").replace(".pt", "")
      config = f"{task_type}"
      cmd = cmd_key
      vel_err = f"${metrics['velocity_tracking_error_mean']:.3f} \\pm {metrics['velocity_tracking_error_std']:.3f}$"
      roll = f"${math.degrees(metrics['roll_rms_mean']):.2f} \\pm {math.degrees(metrics['roll_rms_std']):.2f}$"
      pitch = f"${math.degrees(metrics['pitch_rms_mean']):.2f} \\pm {math.degrees(metrics['pitch_rms_std']):.2f}$"
      cot = f"${metrics['cost_of_transport_mean']:.4f} \\pm {metrics['cost_of_transport_std']:.4f}$"
      recovery = f"${metrics['push_recovery_rate']:.0%}$"

      line = (
        f"{config} & {cmd} & {vel_err} & {roll} & {pitch} & {cot} & {recovery} \\\\"
      )
      lines.append(line)

  lines.append("\\hline")
  lines.append("\\end{tabular}")
  lines.append("\\end{table}")

  return "\n".join(lines)


def main():
  results_dir = Path("evaluation_results/comprehensive")

  print("Loading results...")
  all_results = load_all_results(results_dir)

  if not all_results:
    print("No results found. Run evaluation first:")
    print("  uv run python src/mjlab/scripts/run_comprehensive_eval.py")
    return

  print(f"Found {len(all_results)} configurations")

  # Generate ASCII table
  table = generate_table(all_results)
  print(table)

  # Save to file
  output_file = results_dir / "summary_table.txt"
  with open(output_file, "w") as f:
    f.write(table)
  print(f"\nTable saved to: {output_file}")

  # Generate LaTeX table
  latex_table = generate_latex_table(all_results)
  latex_file = results_dir / "summary_table.tex"
  with open(latex_file, "w") as f:
    f.write(latex_table)
  print(f"LaTeX table saved to: {latex_file}")


if __name__ == "__main__":
  main()
