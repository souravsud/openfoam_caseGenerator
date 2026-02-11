from pathlib import Path
from shutil import copytree, ignore_patterns
from jinja2 import Template
import json
import os
import subprocess


class OpenFOAMCaseGenerator:

    def __init__(self, template_path, input_dir, output_dir):
        self.template_path = Path(template_path)
        self.input_root = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Centralized HPC defaults
        self.hpc_defaults = {
            "account": "eehpc-ben-2026b02-011x",
            "partition": "normal-x86",
            "nodes": 1,
            "ntasks": 128,
            "walltime": "10:00:00"
        }

    # --------------------------------------------------
    # CASE DISCOVERY
    # --------------------------------------------------

    def find_cases(self):
        case_info = []

        for root, dirs, files in os.walk(self.input_root):
            if 'pipeline_metadata.json' in files:
                metadata_path = Path(root) / 'pipeline_metadata.json'
                with open(metadata_path) as f:
                    metadata = json.load(f)

                path_parts = root.split(os.sep)

                if len(path_parts) >= 2:
                    rotation_folder = path_parts[-1]
                    terrain_folder = path_parts[-2]

                    terrain_index = None
                    location = None

                    if terrain_folder.startswith('terrain_'):
                        parts = terrain_folder.split('_')
                        if len(parts) >= 2:
                            terrain_index = parts[1]
                            if len(parts) >= 6:
                                location = f"{parts[2]}.{parts[3]} {parts[4]}.{parts[5]}"

                    rotation_degree = None
                    if rotation_folder.startswith('rotatedTerrain_') and rotation_folder.endswith('_deg'):
                        degree_part = rotation_folder[len('rotatedTerrain_'):-len('_deg')]
                        if degree_part.isdigit():
                            rotation_degree = int(degree_part)

                    case_info.append({
                        'case_dir': root,
                        'terrain_index': terrain_index,
                        'location': location,
                        'rotation_degree': rotation_degree,
                        'metadata': metadata
                    })

        return case_info

    # --------------------------------------------------
    # FILE RENDERING
    # --------------------------------------------------

    def render_file(self, file_path, context):
        with open(file_path, 'r') as f:
            template = Template(f.read())
        rendered = template.render(context)
        with open(file_path, 'w') as f:
            f.write(rendered)

    # --------------------------------------------------
    # CASE SETUP
    # --------------------------------------------------

    def setup_case(self, case_info):
        case_name = f"case_{case_info['terrain_index']}_{case_info['rotation_degree']:03d}deg"
        output_case = self.output_dir / case_name

        context = {
            'terrain_index': case_info['terrain_index'],
            'rotation_degree': case_info['rotation_degree'],
            'location': case_info['location'],
            'end_time': 20000,
            'write_interval': 5000,
            'n_procs': self.hpc_defaults["ntasks"],
            'wind_direction': case_info['metadata'].get('wind_direction_deg', 0),
            **case_info['metadata']
        }

        # Copy template
        copytree(self.template_path, output_case, dirs_exist_ok=True)

        # Render OpenFOAM dictionary files
        files_to_render = [
            output_case / 'system' / 'controlDict',
            output_case / 'system' / 'decomposeDict',
        ]

        for file in files_to_render:
            if file.exists():
                self.render_file(file, context)

        # Render openfoam.sh from template
        self.render_hpc_script(output_case, case_name)

        # Copy metadata
        metadata_dest = output_case / 'pipeline_metadata.json'
        with open(metadata_dest, 'w') as f:
            json.dump(case_info['metadata'], f, indent=2)

        # Merge geometry / input files
        copytree(
            case_info['case_dir'],
            output_case,
            dirs_exist_ok=True,
            ignore=ignore_patterns('*.png', '*.vtk', 'pipeline_metadata.json')
        )

        # Initialize status file
        self.initialize_case_status(output_case)

        return output_case

    # --------------------------------------------------
    # STATUS MANAGEMENT
    # --------------------------------------------------

    def initialize_case_status(self, case_path):
        status_file = case_path / "case_status.json"

        if not status_file.exists():
            status = {
                "mesh_status": "NOT_RUN",
                "mesh_ok": False,
                "submitted": False,
                "job_id": None
            }
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=2)

    def update_status(self, case_path, updates):
        status_file = case_path / "case_status.json"
        with open(status_file) as f:
            status = json.load(f)

        status.update(updates)

        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)

    # --------------------------------------------------
    # LOCAL MESHING
    # --------------------------------------------------

    def mesh_case(self, case_path):
        print(f"Meshing: {case_path.name}")

        env = os.environ.copy()
        env["RUN_STAGE"] = "mesh"

        subprocess.run(
            ["bash", "Allrun"],
            cwd=case_path,
            env=env,
            check=True
        )

        # Check mesh log
        log_file = case_path / "log.checkMesh"

        if log_file.exists():
            with open(log_file) as f:
                content = f.read()

            if "Mesh OK" in content:
                print("Mesh OK.")
                self.update_status(case_path, {
                    "mesh_status": "DONE",
                    "mesh_ok": True
                })
            else:
                print("Mesh FAILED.")
                self.update_status(case_path, {
                    "mesh_status": "FAILED",
                    "mesh_ok": False
                })

    # --------------------------------------------------
    # HPC SCRIPT RENDERING
    # --------------------------------------------------

    def render_hpc_script(self, case_path, case_name):

        template_file = case_path / "openfoam.sh.j2"
        output_file = case_path / "openfoam.sh"

        context = {
            "job_name": f"of_{case_name}",
            **self.hpc_defaults
        }

        if template_file.exists():
            with open(template_file) as f:
                template = Template(f.read())

            rendered = template.render(context)

            with open(output_file, 'w') as f:
                f.write(rendered)

            os.remove(template_file)
            os.chmod(output_file, 0o755)

    # --------------------------------------------------
    # READY CASE LISTING
    # --------------------------------------------------

    def list_ready_cases(self, limit=None):
        ready = []

        for case_dir in self.output_dir.iterdir():
            status_file = case_dir / "case_status.json"
            if not status_file.exists():
                continue

            with open(status_file) as f:
                status = json.load(f)

            if status["mesh_ok"] and not status["submitted"]:
                ready.append(case_dir)

        if limit:
            return ready[:limit]

        return ready

    def mark_submitted(self, case_path, job_id):
        self.update_status(case_path, {
            "submitted": True,
            "job_id": job_id
        })

    # --------------------------------------------------
    # BULK GENERATION
    # --------------------------------------------------

    def generate_all_cases(self):
        cases = self.find_cases()
        print(f"Found {len(cases)} cases")

        for case_info in cases:
            print(f"Processing terrain_{case_info['terrain_index']} @ {case_info['rotation_degree']}°")
            output = self.setup_case(case_info)
            print(f"  → {output}")


# --------------------------------------------------
# USAGE
# --------------------------------------------------

if __name__ == "__main__":

    generator = OpenFOAMCaseGenerator(
        template_path="/home/sourav/CFD_Dataset/openfoam_caseGenerator/template",
        input_dir="/home/sourav/CFD_Dataset/generateInputs/Data_test/downloads",
        output_dir="/home/sourav/CFD_Dataset/openFoamCases"
    )

    generator.generate_all_cases()

    # Example manual flow:
    # ready = generator.list_ready_cases(limit=2)
    # for case in ready:
    #     generator.mesh_case(case)
    #     # After manual sbatch:
    #     generator.mark_submitted(case, job_id=123456)
