import math
import pulp

def haversine(coord1, coord2):
    R = 6371
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def build_distance_matrix(locations):
    names = list(locations.keys())
    matrix = {}
    for i in names:
        for j in names:
            if i != j:
                matrix[i, j] = haversine(locations[i], locations[j])
    return matrix

def solve_cvrp(locations, demands, num_vehicles, vehicle_capacity, fuel_cost_per_km):
    nodes = list(locations.keys())
    customers = [n for n in nodes if n != 'Depot']
    distance_matrix = build_distance_matrix(locations)

    prob = pulp.LpProblem("CVRP", pulp.LpMinimize)
    vehicles = list(range(num_vehicles))

    x = {}
    for k in vehicles:
        for i in nodes:
            for j in nodes:
                if i != j:
                    x[i, j, k] = pulp.LpVariable(f"x_{i}_{j}_{k}", cat='Binary')

    # Objective: minimize total cost
    prob += pulp.lpSum(
        distance_matrix[i, j] * fuel_cost_per_km * x[i, j, k]
        for k in vehicles for i in nodes for j in nodes if i != j
    )

    # Each customer visited exactly once
    for j in customers:
        prob += pulp.lpSum(x[i, j, k] for k in vehicles for i in nodes if i != j) == 1

    # Flow conservation
    for k in vehicles:
        for h in customers:
            prob += (pulp.lpSum(x[i, h, k] for i in nodes if i != h) ==
                     pulp.lpSum(x[h, j, k] for j in nodes if j != h))

    # Depot constraints
    for k in vehicles:
        prob += pulp.lpSum(x['Depot', j, k] for j in customers) <= 1
        prob += pulp.lpSum(x[i, 'Depot', k] for i in customers) <= 1

    # Capacity constraints
    for k in vehicles:
        prob += pulp.lpSum(
            demands[j] * x[i, j, k]
            for i in nodes for j in customers if i != j
        ) <= vehicle_capacity

    # Subtour elimination (MTZ)
    u = {}
    n = len(customers)
    for k in vehicles:
        for i in customers:
            u[i, k] = pulp.LpVariable(f"u_{i}_{k}", lowBound=1, upBound=n, cat='Continuous')

    for k in vehicles:
        for i in customers:
            for j in customers:
                if i != j:
                    prob += u[i, k] - u[j, k] + n * x[i, j, k] <= n - 1

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != 'Optimal':
        return None

    # Extract routes
    routes = []
    for k in vehicles:
        if not any(pulp.value(x.get(('Depot', j, k), 0)) == 1 for j in customers):
            continue
        route = ['Depot']
        current = 'Depot'
        while True:
            moved = False
            for j in nodes:
                if current != j and pulp.value(x.get((current, j, k), 0)) == 1:
                    route.append(j)
                    current = j
                    moved = True
                    break
            if not moved or current == 'Depot':
                break

        total_dist = sum(distance_matrix[route[i], route[i+1]] for i in range(len(route)-1))
        total_load = sum(demands[stop] for stop in route if stop != 'Depot')
        total_cost = total_dist * fuel_cost_per_km

        routes.append({
            'vehicle': k + 1,
            'route': route,
            'distance': round(total_dist, 2),
            'load': total_load,
            'cost': round(total_cost, 2)
        })

    return routes