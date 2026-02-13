from pathlib import Path
from taskManager import OpenFOAMCaseGenerator
import time
import sys

# ============================
# USER SETTINGS
# ============================
CHECK_INTERVAL_MINUTES = 120  # Check every 2 hours
MAX_ITERATIONS = None  # None = run forever, or set number (e.g., 10)

# ============================
# MAIN
# ============================
if __name__ == "__main__":
    generator = OpenFOAMCaseGenerator(
        template_path="/home/sourav/CFD_Dataset/openfoam_caseGenerator/template",
        input_dir="/home/sourav/CFD_Dataset/generateInputs/Data_test/downloads",
        output_dir="/home/sourav/CFD_Dataset/openFoamCases",
        deucalion_path="/projects/EEHPC-BEN-2026B02-011/cfd_data"
    )

    iteration = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"Job Status Check - Iteration {iteration}")
            print(f"{'='*60}\n")

            # Get all submitted cases
            submitted_cases = generator.list_cases_by_status(submitted=True)

            if not submitted_cases:
                print("No submitted jobs to monitor.")
            else:
                active_jobs = []
                completed_jobs = []
                failed_jobs = []

                for case in submitted_cases:
                    case_name = case.name
                    job_status = generator.update_job_status(case)
                    
                    status_obj = generator.get_status(case)
                    job_id = status_obj.get("job_id", "N/A")
                    
                    print(f"{case_name}: Job {job_id} -> {job_status}")

                    if job_status in ["PENDING", "RUNNING"]:
                        active_jobs.append((case_name, job_id, job_status))
                    elif job_status in ["COMPLETED"]:
                        completed_jobs.append((case_name, job_id))
                    elif job_status in ["FAILED", "CANCELLED", "TIMEOUT"]:
                        failed_jobs.append((case_name, job_id, job_status))

                # Summary
                print(f"\n--- Summary ---")
                print(f"Active: {len(active_jobs)}")
                print(f"Completed: {len(completed_jobs)}")
                print(f"Failed: {len(failed_jobs)}")

                if failed_jobs:
                    print(f"\n⚠️  Failed jobs (needs investigation):")
                    for case_name, job_id, status in failed_jobs:
                        print(f"  - {case_name}: Job {job_id} [{status}]")

            # Exit if max iterations reached
            if MAX_ITERATIONS and iteration >= MAX_ITERATIONS:
                print(f"\nReached max iterations ({MAX_ITERATIONS}). Exiting.")
                break

            # Sleep until next check
            print(f"\nNext check in {CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user (Ctrl+C).")
        sys.exit(0)