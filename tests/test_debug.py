import sys
sys.path.insert(0, '.')

# Create a modified version with print statements
code = open('algorithms/mdvrp_greedy.py').read()

# Find and replace the insert_customer method
import re

# Pattern to match the insert_customer method
pattern = r'(    def insert_customer\(self, vehicle, customer, position\):.*?)(        # Remove from unallocated)'

replacement = r'''\1        print(f'[DEBUG] time_increase = {time_increase}')
        print(f'[DEBUG] route_time before +=: {self.route_time}')
        print(f'[DEBUG] id(self.route_time): {id(self.route_time)}')
        print(f'[DEBUG] About to execute: self.route_time["{vehicle}"] += {time_increase}')
        self.route_time[vehicle] += time_increase
        print(f'[DEBUG] route_time after +=: {self.route_time}')
\2'''

new_code = re.sub(pattern, replacement, code, flags=re.DOTALL)

# Write to a temp file
with open('algorithms/mdvrp_greedy_debug.py', 'w') as f:
    f.write(new_code)

print("Created algorithms/mdvrp_greedy_debug.py")
