# Individual Algorithm Run Scripts

This folder contains individual run scripts for each MDVRP solving algorithm:

- `run_hga.py` - Hybrid Genetic Algorithm (HGA)
- `run_greedy.py` - Greedy Cheapest Insertion Algorithm  
- `run_milp.py` - Mixed Integer Linear Programming (MILP)

## Quick Start

Each script can be run independently:

```bash
# Run HGA algorithm
python individual_runs/run_hga.py

# Run Greedy algorithm
python individual_runs/run_greedy.py

# Run MILP algorithm
python individual_runs/run_milp.py
```

## Algorithm Details

### HGA (Hybrid Genetic Algorithm)
- **Framework**: DEAP with NumPy optimization
- **Best for**: Large-scale problems, good quality solutions
- **Runtime**: Medium (depends on generations/population)
- **Configuration**: 
  - Generations: 50
  - Population size: 50
  - Time limit: 300s

### Greedy (Cheapest Insertion)
- **Algorithm**: Constructive heuristic
- **Best for**: Quick solutions, baseline comparison
- **Runtime**: Fast (typically < 1 minute)
- **Configuration**:
  - Time limit: 60s

### MILP (Mixed Integer Linear Programming)
- **Solver**: Gurobi optimizer
- **Best for**: Optimal solutions, small instances
- **Runtime**: Variable (can be slow for large problems)
- **Configuration**:
  - Time limit: 300s
  - MIP gap: 0.01

## Output

Each script saves results to the `../output/` directory:
- `hga_solution_YYYYMMDD_HHMMSS.json`
- `greedy_solution_YYYYMMDD_HHMMSS.json`
- `milp_solution_YYYYMMDD_HHMMSS.json`

## Customization

You can modify parameters in each script's `if __name__ == "__main__"` section:

```python
config = {
    'data_dir': '../data',
    'time_limit': 300,     # Maximum runtime in seconds
    'seed': 42,            # Random seed for reproducibility
    'verbose': True        # Print progress
}
```

## Data

Scripts expect data files in `../data/` directory:
- `customers.csv`
- `depots.csv`
- `vehicles.csv`
- `items.csv`
- `orders.csv`

## Requirements

- Python 3.7+
- DEAP, NumPy, Pandas, tqdm
- Gurobi (for MILP only)

See `../requirements.txt` for complete dependencies.