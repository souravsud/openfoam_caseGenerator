from taskManager import OpenFOAMCaseGenerator

generator = OpenFOAMCaseGenerator(
    template_path="/home/sourav/CFD_Dataset/openfoam_caseGenerator/template",
    input_dir="/home/sourav/CFD_Dataset/generateInputs/Data_test/downloads",
    output_dir="/home/sourav/CFD_Dataset/openFoamCases"
)

generator.generate_all_cases()