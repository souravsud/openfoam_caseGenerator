from pathlib import Path
from shutil import copytree, ignore_patterns
from jinja2 import Environment, FileSystemLoader, Template
import json

class OpenFOAMCaseGenerator:
    def __init__(self, template_path, input_dir, output_dir):
        self.template_path = Path(template_path)
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_metadata(self, case_path):
        """Load metadata.json from case folder"""
        metadata_file = case_path / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def render_template_file(self, template_file, context):
        """Render a single file with jinja2"""
        with open(template_file, 'r') as f:
            template = Template(f.read())
        return template.render(context)
    
    def process_case(self, case_folder):
        """Process a single case folder"""
        case_name = case_folder.name
        output_case = self.output_dir / case_name
        
        # Load metadata
        metadata = self.load_metadata(case_folder)
        
        # Step 1: Copy template
        copytree(self.template_path, output_case, 
                 dirs_exist_ok=True)
        
        # Step 2: Render jinja2 templates (specify files here)
        # TODO: Add file paths that need jinja2 rendering
        
        # Step 3: Copy/merge input files
        copytree(case_folder, output_case,
                 dirs_exist_ok=True, 
                 ignore=ignore_patterns('*.png', '.vtk', 'metadata.json'))
        
        return output_case
    
    def generate_all_cases(self):
        """Process all case folders"""
        case_folders = [f for f in self.input_dir.iterdir() 
                       if f.is_dir()]  # Add naming filter if needed
        
        for case_folder in case_folders:
            print(f"Processing: {case_folder.name}")
            output_case = self.process_case(case_folder)
            print(f"Created: {output_case}")

# Usage
if __name__ == "__main__":
    generator = OpenFOAMCaseGenerator(
        template_path="path/to/template",
        input_dir="path/to/input/folders",
        output_dir="path/to/output/cases"
    )
    generator.generate_all_cases()