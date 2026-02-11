from pathlib import Path
from taskManager import OpenFOAMCaseGenerator


# ============================
# USER SETTINGS
# ============================

N_CASES_TO_MESH = 1


# ============================
# MAIN
# ============================

if __name__ == "__main__":

    generator = OpenFOAMCaseGenerator(
        template_path="/home/sourav/CFD_Dataset/openfoam_caseGenerator/template",
        input_dir="/home/sourav/CFD_Dataset/generateInputs/Data_test/downloads",
        output_dir="/home/sourav/CFD_Dataset/openFoamCases"
    )

    all_cases = sorted(generator.output_dir.iterdir())

    meshed_count = 0

    for case in all_cases:
        status_file = case / "case_status.json"

        if not status_file.exists():
            continue

        with open(status_file) as f:
            import json
            status = json.load(f)

        # Only mesh cases that haven't been meshed yet
        if status["mesh_status"] == "NOT_RUN":

            generator.mesh_case(case)
            meshed_count += 1

            if meshed_count >= N_CASES_TO_MESH:
                break

    print("\n--- Ready for Submission ---")

    ready = generator.list_ready_cases()

    for case in ready:
        print(case.name)

    print(f"\nTotal ready cases: {len(ready)}")
