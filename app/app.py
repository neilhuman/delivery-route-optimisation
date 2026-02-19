from flask import Flask, render_template, request, jsonify
import openrouteservice
from solver import solve_cvrp

app = Flask(__name__)

ORS_API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImVjNzRhNmQwODNkYjQ5Nzk5YmI4YTQxZDkwY2Q4MjQ4IiwiaCI6Im11cm11cjY0In0='
client = openrouteservice.Client(key=ORS_API_KEY)

def get_road_coords(coord1, coord2):
    try:
        result = client.directions(
            coordinates=[[coord1[1], coord1[0]], [coord2[1], coord2[0]]],
            profile='driving-car',
            format='geojson'
        )
        route_coords = result['features'][0]['geometry']['coordinates']
        return [[c[1], c[0]] for c in route_coords]
    except:
        return [list(coord1), list(coord2)]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
def solve():
    data = request.get_json()

    # Build locations dict
    locations = {'Depot': (float(data['depot_lat']), float(data['depot_lng']))}
    demands = {}
    for i, customer in enumerate(data['customers']):
        name = f"Customer_{i+1}"
        locations[name] = (float(customer['lat']), float(customer['lng']))
        demands[name] = float(customer['demand'])

    num_vehicles = int(data['num_vehicles'])
    vehicle_capacity = float(data['vehicle_capacity'])
    fuel_cost = float(data['fuel_cost'])

    routes = solve_cvrp(locations, demands, num_vehicles, vehicle_capacity, fuel_cost)

    if routes is None:
        return jsonify({'error': 'No optimal solution found. Try adding more vehicles or increasing capacity.'})

    # Get road coordinates for each route
    vehicle_colors = ['blue', 'red', 'green', 'purple', 'orange']
    map_routes = []
    for r in routes:
        segments = []
        for i in range(len(r['route']) - 1):
            start = locations[r['route'][i]]
            end = locations[r['route'][i+1]]
            road_coords = get_road_coords(start, end)
            segments.append(road_coords)
        map_routes.append({
            'vehicle': r['vehicle'],
            'segments': segments,
            'color': vehicle_colors[(r['vehicle']-1) % len(vehicle_colors)],
            'route': r['route'],
            'distance': r['distance'],
            'load': r['load'],
            'cost': r['cost']
        })

    # Build marker data
    markers = []
    for name, coords in locations.items():
        markers.append({
            'name': name,
            'lat': coords[0],
            'lng': coords[1],
            'demand': demands.get(name, 0)
        })

    return jsonify({'routes': map_routes, 'markers': markers})

if __name__ == '__main__':
    app.run(debug=True)