"""
Export MDVRP solutions to various formats (CSV, PDF, GeoJSON)
"""

import pandas as pd
import json
from typing import Dict, List, Tuple, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import geojson
from geojson import Feature, FeatureCollection, Point, LineString


class MDVRPExporter:
    """Export MDVRP solutions to CSV, PDF, GeoJSON"""

    def __init__(self):
        """Initialize exporter"""
        self.solution = None
        self.problem_data = None

    def export_csv(self, solution: Dict, output_path: str) -> None:
        """
        Export solution to CSV file.

        Args:
            solution: Solution dict with routes and metadata
            output_path: Path to output CSV file

        Raises:
            ValueError: If solution format is invalid
            IOError: If file cannot be written
        """
        if 'routes' not in solution:
            raise ValueError("Solution must contain 'routes' key")

        routes = solution['routes']
        depot_for_vehicle = solution.get('depot_for_vehicle', {})
        vehicle_speed = solution.get('vehicle_speed', {})

        # Build rows for CSV
        rows = []
        for vehicle_id, route_info in routes.items():
            if isinstance(route_info, dict):
                # New format: route_info is a dict with nodes, distance, time, load
                nodes = route_info.get('nodes', [])
                # Get depot for this vehicle
                depot = depot_for_vehicle.get(vehicle_id, nodes[0] if nodes else 'D1')
                # Create full route with depot at start and end
                if nodes:
                    full_route = [depot] + nodes + [depot]
                else:
                    full_route = [depot, depot]  # Empty route
                route_str = ' -> '.join(map(str, full_route))
                distance = route_info.get('distance', 0)
                time_hours = route_info.get('time', 0)
                load_kg = route_info.get('load', 0)
                speed_kmh = vehicle_speed.get(vehicle_id, 0)
            else:
                # Old format: route_info is just a list of nodes
                depot = depot_for_vehicle.get(vehicle_id, route_info[0] if route_info else 'D1')
                if route_info:
                    full_route = [depot] + route_info + [depot]
                else:
                    full_route = [depot, depot]
                route_str = ' -> '.join(map(str, full_route))
                distance = 0
                time_hours = 0
                load_kg = 0
                speed_kmh = vehicle_speed.get(vehicle_id, 0)

            rows.append({
                'vehicle_id': vehicle_id,
                'route': route_str,
                'distance_km': round(distance, 2),
                'time_hours': round(time_hours, 2),
                'load_kg': round(load_kg, 2),
                'speed_kmh': round(speed_kmh, 2)
            })

        # Create DataFrame and save
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)

    def export_pdf(self, solution: Dict, problem_data: Dict, output_path: str,
                   algorithm_name: str = None, algorithm_params: Dict = None) -> None:
        """
        Export solution report to PDF.

        Args:
            solution: Solution dict with routes and metadata
            problem_data: Problem data (coordinates, demands, etc.)
            output_path: Path to output PDF file
            algorithm_name: Name of the algorithm used (e.g., 'Greedy Heuristic', 'Hybrid GA', 'MILP')
            algorithm_params: Algorithm-specific parameters (e.g., population_size, generations, time_limit)

        Raises:
            ValueError: If solution format is invalid
            IOError: If file cannot be written
        """
        if 'routes' not in solution:
            raise ValueError("Solution must contain 'routes' key")

        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=30, leftMargin=30,
                                topMargin=30, bottomMargin=18)

        # Build story
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            spaceAfter=30
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=12
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.darkblue,
            spaceAfter=10,
            spaceBefore=10
        )

        # Title
        title = Paragraph("MDVRP Solution Report", title_style)
        story.append(title)

        # Algorithm Information Section
        if algorithm_name:
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("Algorithm Information", heading_style))
            story.append(Paragraph(f"Algorithm: <b>{algorithm_name}</b>", styles['Normal']))

            # Add algorithm-specific parameters
            if algorithm_params:
                for param_name, param_value in algorithm_params.items():
                    if param_value is not None:
                        story.append(Paragraph(f"{param_name.replace('_', ' ').title()}: {param_value}", styles['Normal']))

        # Problem Specifications Section
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("Problem Specifications", heading_style))

        # Extract problem statistics
        depots = problem_data.get('depots', {})
        customers = problem_data.get('customers', {})
        vehicles = problem_data.get('vehicles', {})
        vehicle_capacity = problem_data.get('vehicle_capacity', {})
        vehicle_speed = problem_data.get('vehicle_speed', {})
        max_time = problem_data.get('max_time', {})

        # Calculate total customer demand - handle different data formats
        total_demand = 0
        if isinstance(customers, dict):
            for customer in customers.values():
                if isinstance(customer, dict):
                    total_demand += customer.get('demand', 0)
                elif hasattr(customer, 'demand'):
                    total_demand += customer.demand
        elif isinstance(customers, list):
            for customer in customers:
                if isinstance(customer, dict):
                    total_demand += customer.get('demand', 0)
                elif hasattr(customer, 'demand'):
                    total_demand += customer.demand

        # Build problem specs table
        specs_data = [
            ['Specification', 'Value'],
            ['Number of Depots', str(len(depots))],
            ['Number of Customers', str(len(customers))],
            ['Number of Vehicles', str(len(vehicles))],
            ['Total Customer Demand', f'{total_demand:.2f} kg'],
        ]

        # Add vehicle capacity if available
        if vehicle_capacity:
            if isinstance(vehicle_capacity, dict):
                capacities = ', '.join([f"{k}: {v} kg" for k, v in vehicle_capacity.items()])
            else:
                capacities = f"{vehicle_capacity} kg"
            specs_data.append(['Vehicle Capacity', capacities])

        # Add vehicle speed if available
        if vehicle_speed:
            if isinstance(vehicle_speed, dict):
                speeds = ', '.join([f"{k}: {v} km/h" for k, v in vehicle_speed.items()])
            else:
                speeds = f"{vehicle_speed} km/h"
            specs_data.append(['Vehicle Speed', speeds])

        # Add max time if available
        if max_time:
            if isinstance(max_time, dict):
                times = ', '.join([f"{k}: {v} h" for k, v in max_time.items() if v])
            elif max_time:
                times = f"{max_time} h"
            else:
                times = "Not specified"
            if times:  # Only add if there's actual data
                specs_data.append(['Maximum Route Time', times])

        # Create specs table
        specs_table = Table(specs_data, colWidths=[2.5*inch, 2.5*inch])
        specs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(specs_table)
        story.append(Spacer(1, 0.2 * inch))

        # Solution Statistics Section
        story.append(Paragraph("Solution Statistics", heading_style))

        # Build solution stats table
        stats_data = [['Metric', 'Value']]

        # Use total_distance (without penalties) instead of fitness (with penalties)
        distance_key = 'total_distance' if 'total_distance' in solution else 'fitness'
        if distance_key in solution:
            stats_data.append(['Total Distance', f"{solution[distance_key]:.2f} km"])

        # Show penalty if exists
        if 'penalty' in solution and solution['penalty'] > 0:
            stats_data.append(['Penalty', f"{solution['penalty']:.2f}"])

        # Show fitness (distance + penalty)
        if 'fitness' in solution:
            stats_data.append(['Fitness (with penalties)', f"{solution['fitness']:.2f}"])

        # Add generations if available
        if 'generations' in solution:
            stats_data.append(['Generations Completed', str(solution['generations'])])

        # Add runtime if available
        if 'runtime' in solution:
            stats_data.append(['Runtime', f"{solution['runtime']:.2f} seconds"])

        # Calculate additional solution statistics
        routes = solution.get('routes', {})
        if routes:
            # Calculate total vehicles used
            vehicles_used = len([r for r in routes.values() if r])
            stats_data.append(['Vehicles Used', str(vehicles_used)])

            # Calculate total load from routes
            total_load = 0
            total_distance_from_routes = 0
            total_time = 0

            for route_info in routes.values():
                if isinstance(route_info, dict):
                    total_load += route_info.get('load', 0)
                    total_distance_from_routes += route_info.get('distance', 0)
                    total_time += route_info.get('time', 0)

            if total_load > 0:
                stats_data.append(['Total Load Delivered', f"{total_load:.2f} kg"])
            if total_distance_from_routes > 0:
                stats_data.append(['Total Route Distance', f"{total_distance_from_routes:.2f} km"])
            if total_time > 0:
                stats_data.append(['Total Route Time', f"{total_time:.2f} hours"])

        # Create stats table
        stats_table = Table(stats_data, colWidths=[2.5*inch, 2.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.2 * inch))

        # Routes table
        story.append(Paragraph("Vehicle Routes", heading_style))
        story.append(Spacer(1, 0.1 * inch))

        # Build table data
        table_data = [['Vehicle', 'Route', 'Distance (km)', 'Time (h)', 'Load (kg)', 'Speed (km/h)']]

        routes = solution['routes']
        depot_for_vehicle = solution.get('depot_for_vehicle', {})
        vehicle_speed = solution.get('vehicle_speed', {})

        for vehicle_id, route_info in routes.items():
            if isinstance(route_info, dict):
                nodes = route_info.get('nodes', [])
                # Get depot for this vehicle
                depot = depot_for_vehicle.get(vehicle_id, nodes[0] if nodes else 'D1')
                # Create full route with depot at start and end
                if nodes:
                    full_route = [depot] + nodes + [depot]
                else:
                    full_route = [depot, depot]  # Empty route
                route_str = ' -> '.join(map(str, full_route))
                distance = route_info.get('distance', 0)
                time_hours = route_info.get('time', 0)
                load_kg = route_info.get('load', 0)
                speed_kmh = vehicle_speed.get(vehicle_id, 0)
            else:
                nodes = route_info if route_info else []
                depot = depot_for_vehicle.get(vehicle_id, nodes[0] if nodes else 'D1')
                if nodes:
                    full_route = [depot] + nodes + [depot]
                else:
                    full_route = [depot, depot]
                route_str = ' -> '.join(map(str, full_route))
                distance = 0
                time_hours = 0
                load_kg = 0
                speed_kmh = vehicle_speed.get(vehicle_id, 0)

            table_data.append([
                vehicle_id,
                route_str,
                f"{distance:.2f}",
                f"{time_hours:.2f}",
                f"{load_kg:.2f}",
                f"{speed_kmh:.2f}"
            ])

        # Create table
        table = Table(table_data, colWidths=[1*inch, 2.5*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))

        story.append(table)

        # Build PDF
        doc.build(story)

    def export_geojson(self, solution: Dict, coordinates: Dict, output_path: str) -> None:
        """
        Export routes as GeoJSON for mapping.

        Args:
            solution: Solution dict with routes
            coordinates: Dict mapping node IDs to (lat, lon) tuples
            output_path: Path to output GeoJSON file

        Raises:
            ValueError: If solution format is invalid
            IOError: If file cannot be written
        """
        if 'routes' not in solution:
            raise ValueError("Solution must contain 'routes' key")

        routes = solution['routes']
        depot_for_vehicle = solution.get('depot_for_vehicle', {})
        features = []

        # Color palette for routes (distinct, vibrant colors)
        route_colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',
            '#EF476F', '#FFD166', '#06D6A0', '#118AB2', '#073B4C',
            '#9D4EDD', '#FF5733', '#C70039', '#900C3F', '#581845'
        ]

        # Add depot points with enhanced styling
        depot_features = {}
        for node_id, (lat, lon) in coordinates.items():
            if node_id.startswith('D'):  # It's a depot
                feature = Feature(
                    geometry=Point((lon, lat)),  # GeoJSON uses (lon, lat)
                    properties={
                        'id': node_id,
                        'type': 'depot',
                        'marker-color': '#2C3E50',  # Dark blue-gray
                        'marker-size': 'large',
                        'marker-symbol': 'warehouse',
                        'title': f'Depot {node_id}',
                        'stroke': '#2C3E50',
                        'stroke-width': 3,
                        'fill': '#34495E',
                        'fill-opacity': 0.9
                    }
                )
                features.append(feature)
                depot_features[node_id] = feature

        # Add customer points with enhanced styling
        for node_id, (lat, lon) in coordinates.items():
            if node_id.startswith('C'):  # It's a customer
                feature = Feature(
                    geometry=Point((lon, lat)),
                    properties={
                        'id': node_id,
                        'type': 'customer',
                        'marker-color': '#27AE60',  # Green
                        'marker-size': 'medium',
                        'marker-symbol': 'marker-stroked',
                        'title': f'Customer {node_id}',
                        'stroke': '#27AE60',
                        'stroke-width': 2,
                        'fill': '#2ECC71',
                        'fill-opacity': 0.7
                    }
                )
                features.append(feature)

        # Add route lines with depots and color coding
        route_index = 0
        for vehicle_id, route_info in routes.items():
            if isinstance(route_info, dict):
                nodes = route_info.get('nodes', [])
                distance = route_info.get('distance', 0)
                load = route_info.get('load', 0)
                time = route_info.get('time', 0)
            else:
                nodes = route_info if route_info else []
                distance = 0
                load = 0
                time = 0

            # Get depot for this vehicle
            depot = depot_for_vehicle.get(vehicle_id, None)
            if not depot and depot_features:
                # If no depot assigned, use first available depot
                depot = list(depot_features.keys())[0]

            if nodes or depot:
                # Build coordinates for route (including depot at start and end)
                route_coords = []

                # Start from depot
                if depot and depot in coordinates:
                    lat, lon = coordinates[depot]
                    route_coords.append((lon, lat))

                # Add customer nodes
                for node in nodes:
                    if node in coordinates:
                        lat, lon = coordinates[node]
                        route_coords.append((lon, lat))

                # Return to depot
                if depot and depot in coordinates:
                    lat, lon = coordinates[depot]
                    route_coords.append((lon, lat))

                if len(route_coords) > 1:
                    # Assign color to route
                    color = route_colors[route_index % len(route_colors)]
                    route_index += 1

                    feature = Feature(
                        geometry=LineString(route_coords),
                        properties={
                            'vehicle_id': vehicle_id,
                            'type': 'route',
                            'distance_km': round(distance, 2),
                            'load_kg': round(load, 2),
                            'time_hours': round(time, 2),
                            'depot': depot,
                            'stroke': color,
                            'stroke-width': 4,
                            'stroke-opacity': 0.8,
                            'title': f'Route {vehicle_id} ({distance:.1f} km, {load:.1f} kg)',
                            'description': f'Vehicle {vehicle_id} from {depot}: {distance:.2f} km, {load:.2f} kg, {time:.2f} hrs'
                        }
                    )
                    features.append(feature)

        # Create FeatureCollection
        feature_collection = FeatureCollection(features)

        # Save to file
        with open(output_path, 'w') as f:
            json.dump(feature_collection, f, indent=2)

    def export_all(self, solution: Dict, problem_data: Dict, output_dir: str,
                   base_name: str = 'solution', algorithm_name: str = None,
                   algorithm_params: Dict = None) -> List[str]:
        """
        Export solution to all formats (CSV, PDF, GeoJSON).

        Args:
            solution: Solution dict with routes and metadata
            problem_data: Problem data
            output_dir: Directory to save files
            base_name: Base name for output files (default: 'solution')
            algorithm_name: Name of the algorithm used
            algorithm_params: Algorithm-specific parameters

        Returns:
            List of created file paths

        Raises:
            ValueError: If solution format is invalid
            IOError: If files cannot be written
        """
        import os

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        created_files = []

        # Export CSV
        csv_path = os.path.join(output_dir, f"{base_name}.csv")
        self.export_csv(solution, csv_path)
        created_files.append(csv_path)

        # Export PDF with algorithm information
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        self.export_pdf(solution, problem_data, pdf_path, algorithm_name, algorithm_params)
        created_files.append(pdf_path)

        # Export GeoJSON
        geojson_path = os.path.join(output_dir, f"{base_name}.geojson")
        coordinates = problem_data.get('coordinates', {})
        self.export_geojson(solution, coordinates, geojson_path)
        created_files.append(geojson_path)

        return created_files
