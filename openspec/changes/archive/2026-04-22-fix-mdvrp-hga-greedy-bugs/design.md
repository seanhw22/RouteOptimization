# Design: Fix MDVRP HGA and Greedy Bugs

## Context

**Current State:**
- HGA (Hybrid Genetic Algorithm) in `mdvrp_hga.py` has 5 critical bugs: disabled crossover, no elitism, probabilistic local search, missing relocation operator, and missing time export
- Greedy in `mdvrp_greedy.py` has 1 critical bug: time calculation order wrong, causing all route times to be 0.0
- Exporter in `src/exporter.py` displays routes without depot information

**Constraints:**
- HGA uses DEAP framework with specific Individual class structure
- Chromosome representation: linear list with depots as separators (e.g., `[D1, C1, C2, D2, C3, C4, D1]`)
- Must maintain backward compatibility with existing API contracts
- Solution dicts are used by CSV/PDF exporters

**Stakeholders:**
- Research users relying on HGA for diverse solutions
- Thesis/skripsi work requiring correct time calculations
- Performance benchmarking comparing HGA vs Greedy vs MILP

## Goals / Non-Goals

**Goals:**
- Enable genetic diversity in HGA through proper crossover and elitism
- Ensure route times are accurately calculated and exported in both algorithms
- Improve HGA solution quality through deterministic local search
- Provide complete route information including depot origins

**Non-Goals:**
- Changing chromosome representation structure
- Modifying DEAP framework integration
- Adding new algorithm variants
- Performance optimization beyond bug fixes

## Decisions

### D1: HGA Crossover Implementation - Vehicle-Scoped Order Crossover

**Decision:** Implement vehicle-scoped Order Crossover (OX) instead of chromosome-level OX.

**Rationale:**
- Standard OX breaks MDVRP chromosome structure by moving customers across depot boundaries
- Vehicle-scoped OX treats each vehicle's route segment independently
- Preserves depot positions and vehicle-depot assignments

**Alternatives Considered:**
- **Standard OX**: Rejected - would create invalid chromosomes with depots in wrong positions
- **PMX/Edge recombination**: Rejected - same depot boundary issue
- **Random vehicle-wise OX**: Chosen - apply OX to each vehicle's customer segment independently

**Implementation:**
```python
def _ox_crossover(self, parent1, parent2):
    # Decode to routes dict
    routes1 = self._decode_chromosome(parent1)
    routes2 = self._decode_chromosome(parent2)

    offspring_routes = {}
    for vehicle in self.vehicles:
        # Apply OX to customer list only
        route1 = routes1[vehicle]
        route2 = routes2[vehicle]
        offspring_routes[vehicle] = self._ox_on_list(route1, route2)

    # Re-encode to chromosome
    return self._encode_from_routes(offspring_routes)
```

### D2: HGA Elitism - Pre-Sort and Inject

**Decision:** Sort population by fitness, preserve top N elites, only replace remaining population slots.

**Rationale:**
- DEAP's `eaSimple` doesn't support elitism out-of-the-box
- Manual elitism gives explicit control over elite count
- Prevents loss of best solutions during evolution

**Alternatives Considered:**
- **DEAP's HallOfFame only**: Rejected - HallOfFame tracks but doesn't inject elites back into population
- **Custom eaSimple**: Rejected - more complex than needed
- **Manual elitism**: Chosen - simple, explicit, easy to debug

**Implementation:**
```python
# In evolution loop, after evaluating offspring:
population.sort(key=lambda x: x.fitness.values[0])
elites = population[:self.elite_size]
# Generate offspring for remaining slots
offspring = self.toolbox.select(population, len(population) - self.elite_size)
# ... crossover & mutation on offspring ...
# Evaluate offspring
# Replace population
population = elites + offspring
```

### D3: HGA Local Search - Always Run

**Decision:** Remove random probability check, always run 2-opt after mutation.

**Rationale:**
- User requirement: "local search should always run"
- 30% probability was arbitrary, not based on research
- Deterministic behavior improves reproducibility

**Implementation:**
```python
def _mutation_pipeline(self, individual):
    # Apply swap mutation
    individual = self._swap_mutation(individual)[0]

    # Always run local search (removed if random.random() < 0.3)
    routes = self._decode_chromosome(individual)
    individual = self._two_opt_local_search(individual, routes)

    return (individual,)
```

### D4: HGA Relocation - Two-Phase Operator

**Decision:** Implement relocation as two-phase operator: intra-route (move within route) then inter-route (move between routes).

**Rationale:**
- Relocation explores different neighborhood than 2-opt (2-opt reverses segments, relocation moves single nodes)
- Two-phase approach: try improving current route first, then try moving to other routes
- Separates concerns and makes each phase testable

**Alternatives Considered:**
- **Intra-route only**: Rejected - misses opportunities to rebalance load between vehicles
- **Inter-route only**: Rejected - excessive overhead checking all vehicles
- **Two-phase**: Chosen - balances exploration and computational cost

**Implementation:**
```python
def _relocation_local_search(self, individual, routes):
    improved = False

    # Phase 1: Intra-route relocation
    for vehicle in self.vehicles:
        route = routes[vehicle]
        best_move = self._find_best_intra_relocation(vehicle, route)
        if best_move:
            self._apply_intra_relocation(route, best_move)
            improved = True

    # Phase 2: Inter-route relocation (only if intra didn't improve)
    if not improved:
        best_move = self._find_best_inter_relocation(routes)
        if best_move:
            self._apply_inter_relocation(routes, best_move)

    return self._encode_from_routes(routes)
```

### D5: Greedy Time Calculation - Reorder Operations

**Decision:** Calculate time increase BEFORE inserting customer into route.

**Rationale:**
- Current order calculates delta after insertion, resulting in 0.0 (customer already present)
- Simple fix with minimal code changes
- No API or data structure changes needed

**Implementation:**
```python
def insert_customer(self, vehicle, customer, position):
    # STEP 1: Calculate time increase FIRST
    time_increase = self.calculate_time_increase(vehicle, customer, position)

    # STEP 2: Insert customer
    route = self.routes[vehicle]
    if position >= len(route):
        route.append(customer)
    else:
        route.insert(position, customer)

    # STEP 3: Update load and time
    self.route_load[vehicle] += self.demand[customer]
    self.route_time[vehicle] += time_increase  # Now adds actual time

    self.unallocated.remove(customer)
```

### D6: HGA Time Export - Add to Solution Dict

**Decision:** Calculate and include route time in `_format_solution` output.

**Rationale:**
- Time already calculated during fitness evaluation
- Matches Greedy's solution format (has 'time' field)
- Backward compatible (adding optional field)

**Implementation:**
```python
def _format_solution(self, best_individual, start_time, generations):
    routes = self._decode_chromosome(best_individual)
    routes_dict = {}

    for vehicle in self.vehicles:
        route = routes[vehicle]
        route_dist = self._calculate_route_distance(vehicle, route)
        route_time = self._calculate_route_time(vehicle, route)  # NEW method

        routes_dict[vehicle] = {
            'nodes': route,
            'distance': route_dist,
            'time': route_time,  # NEW field
            'load': sum(self.demand[c] for c in route if c is not None)
        }
    # ...
```

### D7: Route Display - Add Depot Information

**Decision:** Modify exporter to wrap customer nodes with depot at start and end.

**Rationale:**
- Shows complete route path
- Helps visualize vehicle departure and return
- Minimal change to exporter logic

**Implementation:**
```python
# In src/exporter.py export_csv() and export_pdf():
for vehicle_id, route_info in routes.items():
    nodes = route_info.get('nodes', [])
    depot = problem_data['depot_for_vehicle'][vehicle_id]

    # Create full route with depot
    if nodes:
        full_route = [depot] + nodes + [depot]
    else:
        full_route = [depot, depot]  # Empty route: depot -> depot

    route_str = ' -> '.join(map(str, full_route))
```

## Risks / Trade-offs

### Risk R1: Crossover May Create Infeasible Solutions
**Risk:** Vehicle-scoped OX may violate time/capacity constraints
**Mitigation:** Accept penalty-based fitness (already implemented), infeasible solutions get penalized and naturally selected against

### Risk R2: Increased HGA Runtime
**Risk:** Always running local search + relocation increases per-generation time
**Mitigation:** Monitor performance, add early termination if no improvement after N iterations (already in 2-opt)

### Risk R3: Elitism May Reduce Diversity
**Risk:** Preserving elites could lead to premature convergence
**Mitigation:** Keep elite size small (default 3 out of 20 population = 15%), rely on crossover for diversity

### Risk R4: Relocation Complexity
**Risk:** Inter-route relocation is computationally expensive (O(V × N²) where V=vehicles, N=customers)
**Mitigation:** Only run inter-route if intra-route doesn't improve, limit to best candidate only

### Risk R5: Breaking Change in Route Display
**Risk:** Changing route string format could break parsers
**Mitigation:** Additive change (appends depot), not removing information. CSV format unchanged structurally.

## Migration Plan

**Deployment Steps:**
1. Apply all changes in development environment
2. Run unit tests for each modified function
3. Run integration tests on small dataset (5 customers)
4. Run comparison tests: verify HGA produces different solutions across multiple seeds
5. Run benchmark: verify Greedy time calculations match manual calculations
6. Commit with descriptive message referencing this change

**Rollback Strategy:**
- All changes are additive (no breaking API changes)
- Git revert can restore previous state
- No database migrations or external state changes

**Testing Strategy:**
- Small dataset test: Verify HGA produces variance, Greedy times > 0
- Medium dataset test: Verify solutions remain feasible (capacity/time constraints)
- Comparison test: Run each algorithm 10x with different seeds, verify solutions differ

## Open Questions

None - all design decisions are straightforward bug fixes with clear implementation paths.
