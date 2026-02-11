import re
import matplotlib.pyplot as plt

def plot_residuals(log_file_path):
    # Dictionary to store the extracted data
    data = {
        'time': [],
        'Ux_final': [],
        'Uy_final': [],
        'Uz_final': [],
        'p_final': [],
        'epsilon_final': [],
        'k_final': []
    }

    # UPDATED: Removed the 's' requirement and added flexibility for leading spaces
    time_pattern = re.compile(r'^\s*Time = (\d+)')
    # Added flexibility for solver names (smoothSolver, GAMG, etc.)
    residual_pattern = re.compile(r'Solving for (Ux|Uy|Uz|p|epsilon|k),.*Final residual = ([\d\.e-]+)')

    try:
        with open(log_file_path, 'r') as f:
            current_time = None
            for line in f:
                # 1. Find the current time step
                time_match = time_pattern.search(line)
                if time_match:
                    current_time = int(time_match.group(1))
                    data['time'].append(current_time)
                    
                    # Ensure all residual lists grow by 1 to stay synced with 'time'
                    for key in data:
                        if key != 'time':
                            data[key].append(None)

                # 2. Find the final residual
                residual_match = residual_pattern.search(line)
                if residual_match and current_time is not None:
                    variable = residual_match.group(1)
                    residual_value = float(residual_match.group(2))
                    
                    key = f"{variable}_final"
                    idx = len(data['time']) - 1
                    
                    # Update the placeholder for this time step
                    # This correctly captures the LAST 'p' residual in the loop
                    data[key][idx] = residual_value

    except FileNotFoundError:
        print(f"Error: The file '{log_file_path}' was not found.")
        return

    # Filter out entries where no data was found to prevent plotting empty lists
    if not data['time']:
        print("Error: No residual data was found. Check your log file format.")
        return

    # Create the plot
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except:
        plt.style.use('ggplot') # Fallback style

    plt.figure(figsize=(12, 8))

    for key in data:
        if key != 'time' and any(v is not None for v in data[key]):
            plt.plot(data['time'], data[key], label=key.replace('_', ' '), marker='o', markersize=4)

    plt.title('OpenFOAM Final Residuals vs. Time', fontsize=16)
    plt.xlabel('Time (Iteration)', fontsize=12)
    plt.ylabel('Final Residual', fontsize=12)
    plt.yscale('log')
    plt.legend()
    plt.grid(True, which="both", ls="--", alpha=0.5)
    
    output_filename = 'Residuals_plot.png'
    plt.savefig(output_filename)
    print(f"Success! Residual plot saved to '{output_filename}'")

if __name__ == "__main__":
    # Ensure this matches your filename
    plot_residuals('log.simpleFoam')