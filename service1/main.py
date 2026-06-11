"""
main.py
Single entry point that runs the full ML pipeline end-to-end.

Usage:
  python main.py                  <- full pipeline
  python main.py --skip-fetch     <- use existing raw data
  python main.py --skip-train     <- use saved models (skip fetch + preprocess + train)
  python main.py --synthetic      <- generate synthetic data (no internet needed)
"""

import argparse
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(__file__)


def run(script: str, extra_args: list = None):
    """Run a Python script in the same interpreter."""
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, script)]
    if extra_args:
        cmd.extend(extra_args)
    print(f"\n{'='*60}")
    print(f" Running: {script}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, check=True)
    return result


def main():
    parser = argparse.ArgumentParser(description="PM2.5 forecasting pipeline")
    parser.add_argument("--skip-fetch",  action="store_true",
                        help="Skip data fetching, use existing raw CSV")
    parser.add_argument("--skip-train",  action="store_true",
                        help="Skip fetch + preprocess + train (use saved models)")
    parser.add_argument("--synthetic",   action="store_true",
                        help="Generate synthetic data instead of fetching from API")
    parser.add_argument("--model",       choices=["xgb", "rf", "lstm"], default="xgb",
                        help="Model to use for 24h forecast (default: xgb)")
    args = parser.parse_args()

    if args.skip_train:
        # Only re-evaluate and forecast with existing models
        run("evaluate.py")
        run("predict.py", ["--model", args.model])
        print("\n[Main] Pipeline complete (evaluation + forecast only).")
        return

    # Step 1: Data collection
    if not args.skip_fetch:
        if args.synthetic:
            run("generate_synthetic.py")
        else:
            try:
                run("fetch_data.py")
                # Check if data was actually fetched
                data_file = os.path.join(SCRIPT_DIR, "data", "tashkent_pm25_weather.csv")
                if not os.path.exists(data_file) or os.path.getsize(data_file) < 1000:
                    print("\n[Main] Real data fetch produced empty file. "
                          "Falling back to synthetic data …")
                    run("generate_synthetic.py")
            except subprocess.CalledProcessError:
                print("\n[Main] fetch_data.py failed. Falling back to synthetic data …")
                run("generate_synthetic.py")

    # Step 2: Preprocessing + feature engineering
    run("preprocess.py")

    # Step 3: Model training
    run("train_models.py")

    # Step 4: Evaluation + build predictions.json
    run("evaluate.py")

    # Step 5: 24h forecast
    run("predict.py", ["--model", args.model])

    print("\n" + "="*60)
    print(" PIPELINE COMPLETE")
    print("="*60)
    print(f" outputs/predictions.json is ready for the dashboard.")
    print(f" Start the API:  cd ../service2_api && uvicorn main:app --reload --port 8000")
    print(f" Start React:    cd ../dashboard    && npm run dev")


if __name__ == "__main__":
    main()
