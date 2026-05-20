"""
Export MDVRP solutions to various formats (CSV, PDF, GeoJSON)
"""

import io
import pandas as pd
import json
from typing import Dict, List, Tuple, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
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

    def _generate_route_map_image(self, solution: Dict, coordinates: Dict,
                                   name_maps: Dict = None):
        """Render a route map with matplotlib and return a BytesIO PNG buffer, or None."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            return None

        if not coordinates:
            return None

        node_name_map = (name_maps or {}).get('node_name_map', {})
        vehicle_name_map = (name_maps or {}).get('vehicle_name_map', {})
        routes = solution.get('routes', {})
        depot_for_vehicle = solution.get('depot_for_vehicle', {})

        route_colors = [
            '#E63946', '#F4A261', '#2A9D8F', '#9B5DE5', '#FFB703',
            '#3A86FF', '#F72585', '#06D6A0', '#FB5607', '#8AC926',
        ]

        fig, ax = plt.subplots(figsize=(10, 7))
        legend_handles = []

        for i, (vehicle_id, route_info) in enumerate(routes.items()):
            if not isinstance(route_info, dict):
                continue
            nodes = route_info.get('nodes', [])
            depot = depot_for_vehicle.get(vehicle_id)
            chain = ([depot] + nodes + [depot]) if depot else nodes
            color = route_colors[i % len(route_colors)]
            v_label = vehicle_name_map.get(vehicle_id, vehicle_id)

            xs, ys = [], []
            for nid in chain:
                if nid in coordinates:
                    lat, lon = coordinates[nid]
                    xs.append(lon)
                    ys.append(lat)

            if len(xs) > 1:
                ax.plot(xs, ys, '-', color=color, linewidth=2, alpha=0.75, zorder=2)
                for j in range(len(xs) - 1):
                    mx = (xs[j] + xs[j + 1]) / 2
                    my = (ys[j] + ys[j + 1]) / 2
                    dx = xs[j + 1] - xs[j]
                    dy = ys[j + 1] - ys[j]
                    length = (dx ** 2 + dy ** 2) ** 0.5
                    if length > 0:
                        scale = length * 0.15
                        ax.annotate('',
                                    xy=(mx + dx / length * scale, my + dy / length * scale),
                                    xytext=(mx - dx / length * scale, my - dy / length * scale),
                                    arrowprops=dict(arrowstyle='->', color=color, lw=1.5),
                                    zorder=3)

            legend_handles.append(mpatches.Patch(color=color, label=v_label))

        # Customer nodes
        for node_id, (lat, lon) in coordinates.items():
            raw = node_id.split('_', 1)[-1] if '_' in node_id else node_id
            if not raw.upper().startswith('D'):
                ax.scatter(lon, lat, c='#27AE60', s=55, zorder=4,
                           edgecolors='white', linewidths=0.7)
                label = node_name_map.get(node_id, node_id)
                ax.annotate(label, (lon, lat), textcoords='offset points',
                            xytext=(3, 3), fontsize=6, color='#333333', zorder=5)

        # Depot nodes on top
        for node_id, (lat, lon) in coordinates.items():
            raw = node_id.split('_', 1)[-1] if '_' in node_id else node_id
            if raw.upper().startswith('D'):
                ax.scatter(lon, lat, c='#2C3E50', s=180, zorder=6,
                           marker='*', edgecolors='white', linewidths=0.8)
                label = node_name_map.get(node_id, node_id)
                ax.annotate(label, (lon, lat), textcoords='offset points',
                            xytext=(5, 5), fontsize=8, fontweight='bold',
                            color='#2C3E50', zorder=7)

        all_handles = ([mpatches.Patch(color='#2C3E50', label='Depot'),
                        mpatches.Patch(color='#27AE60', label='Customer')]
                       + legend_handles)
        ax.legend(handles=all_handles, loc='upper right', fontsize=7,
                  framealpha=0.9, borderpad=0.8)
        ax.set_xlabel('Longitude', fontsize=9)
        ax.set_ylabel('Latitude', fontsize=9)
        ax.set_title('Route Map', fontsize=13, fontweight='bold', pad=12)
        ax.grid(True, alpha=0.25, linestyle='--')
        ax.tick_params(labelsize=7)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf

    def export_csv(self, solution: Dict, output_path: str, name_maps: Dict = None) -> None:
        """
        Export solution to CSV file.

        Args:
            solution: Solution dict with routes and metadata
            output_path: Path to output CSV file
            name_maps: Optional dict with 'vehicle_name_map' and 'node_name_map'

        Raises:
            ValueError: If solution format is invalid
            IOError: If file cannot be written
        """
        if 'routes' not in solution:
            raise ValueError("Solution must contain 'routes' key")

        vehicle_name_map = (name_maps or {}).get('vehicle_name_map', {})
        node_name_map = (name_maps or {}).get('node_name_map', {})

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
                route_str = ' -> '.join(node_name_map.get(str(n), str(n)) for n in full_route)
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
                route_str = ' -> '.join(node_name_map.get(str(n), str(n)) for n in full_route)
                distance = 0
                time_hours = 0
                load_kg = 0
                speed_kmh = vehicle_speed.get(vehicle_id, 0)

            rows.append({
                'vehicle': vehicle_name_map.get(vehicle_id, vehicle_id),
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
                   algorithm_name: str = None, algorithm_params: Dict = None,
                   name_maps: Dict = None, customer_orders: Dict = None) -> None:
        """
        Export solution report to PDF.

        Args:
            solution: Solution dict with routes and metadata
            problem_data: Problem data (coordinates, demands, etc.)
            output_path: Path to output PDF file
            algorithm_name: Name of the algorithm used (e.g., 'Greedy Heuristic', 'Hybrid GA', 'MILP')
            algorithm_params: Algorithm-specific parameters (e.g., population_size, generations, time_limit)
            name_maps: Optional dict with 'vehicle_name_map' and 'node_name_map'

        Raises:
            ValueError: If solution format is invalid
            IOError: If file cannot be written
        """
        if 'routes' not in solution:
            raise ValueError("Solution must contain 'routes' key")

        vehicle_name_map = (name_maps or {}).get('vehicle_name_map', {})
        node_name_map = (name_maps or {}).get('node_name_map', {})

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

        cell_style_10 = ParagraphStyle('CellWrap10', parent=styles['Normal'], fontSize=10)
        cell_style_8 = ParagraphStyle('CellWrap8', parent=styles['Normal'], fontSize=8)

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

        # Calculate total customer demand
        total_demand = 0
        if customer_orders:
            total_demand = sum(v.get('total_weight', 0) for v in customer_orders.values())
        elif isinstance(customers, dict):
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
                capacities = ', '.join([f"{vehicle_name_map.get(k, k)}: {v} kg" for k, v in vehicle_capacity.items()])
            else:
                capacities = f"{vehicle_capacity} kg"
            specs_data.append(['Vehicle Capacity', Paragraph(capacities, cell_style_10)])

        # Add vehicle speed if available
        if vehicle_speed:
            if isinstance(vehicle_speed, dict):
                speeds = ', '.join([f"{vehicle_name_map.get(k, k)}: {v} km/h" for k, v in vehicle_speed.items()])
            else:
                speeds = f"{vehicle_speed} km/h"
            specs_data.append(['Vehicle Speed', Paragraph(speeds, cell_style_10)])

        # Add max time if available
        if max_time:
            if isinstance(max_time, dict):
                times = ', '.join([f"{vehicle_name_map.get(k, k)}: {v} h" for k, v in max_time.items() if v])
            elif max_time:
                times = f"{max_time} h"
            else:
                times = "Not specified"
            if times:  # Only add if there's actual data
                specs_data.append(['Maximum Route Time', Paragraph(times, cell_style_10)])

        # Create specs table
        specs_table = Table(specs_data, colWidths=[2.2*inch, 4.8*inch])
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
        stats_table = Table(stats_data, colWidths=[2.2*inch, 4.8*inch])
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

        # Route Map
        coordinates = problem_data.get('coordinates', {})
        map_buf = self._generate_route_map_image(solution, coordinates, name_maps=name_maps)
        if map_buf is not None:
            story.append(Paragraph("Route Map", heading_style))
            img = Image(map_buf, width=6.5 * inch, height=4.5 * inch)
            story.append(img)
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
                route_str = ' -> '.join(node_name_map.get(str(n), str(n)) for n in full_route)
                distance = route_info.get('distance', 0)
                time_hours = route_info.get('time', 0)
                load_kg = route_info.get('load') or (
                    sum(customer_orders.get(n, {}).get('total_weight', 0) for n in nodes)
                    if customer_orders else 0
                )
                speed_kmh = vehicle_speed.get(vehicle_id, 0)
            else:
                nodes = route_info if route_info else []
                depot = depot_for_vehicle.get(vehicle_id, nodes[0] if nodes else 'D1')
                if nodes:
                    full_route = [depot] + nodes + [depot]
                else:
                    full_route = [depot, depot]
                route_str = ' -> '.join(node_name_map.get(str(n), str(n)) for n in full_route)
                distance = 0
                time_hours = 0
                load_kg = (
                    sum(customer_orders.get(n, {}).get('total_weight', 0) for n in nodes)
                    if customer_orders else 0
                )
                speed_kmh = vehicle_speed.get(vehicle_id, 0)

            table_data.append([
                vehicle_name_map.get(vehicle_id, vehicle_id),
                Paragraph(route_str, cell_style_8),
                f"{distance:.2f}",
                f"{time_hours:.2f}",
                f"{load_kg:.2f}",
                f"{speed_kmh:.2f}"
            ])

        # Create table
        table = Table(table_data, colWidths=[0.7*inch, 3.3*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.9*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        story.append(table)

        # Detailed Route Orders section
        if customer_orders:
            story.append(PageBreak())
            story.append(Paragraph("Detailed Route Orders", heading_style))

            for vehicle_id, route_info in routes.items():
                if isinstance(route_info, dict):
                    nodes = route_info.get('nodes', [])
                    distance = route_info.get('distance', 0)
                    time_hours = route_info.get('time', 0)
                else:
                    nodes = route_info if route_info else []
                    distance = 0
                    time_hours = 0

                depot = depot_for_vehicle.get(vehicle_id, '')
                v_name = vehicle_name_map.get(vehicle_id, vehicle_id)

                story.append(Spacer(1, 0.15 * inch))
                story.append(Paragraph(f"Vehicle: {v_name}", subtitle_style))

                if not nodes:
                    story.append(Paragraph("No customers on this route.", styles['Normal']))
                    continue

                full_route = ([depot] + nodes + [depot]) if depot else nodes
                route_str = ' → '.join(node_name_map.get(n, n) for n in full_route)
                story.append(Paragraph(
                    f"Route: {route_str} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"Distance: {distance:.2f} km &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"Time: {time_hours:.2f} h",
                    cell_style_8))
                story.append(Spacer(1, 0.05 * inch))

                col_widths = [0.45*inch, 1.6*inch, 2.1*inch, 0.5*inch, 0.85*inch, 0.9*inch]
                tdata = [['Stop', 'Customer', 'Item', 'Qty', 'kg/unit', 'Total (kg)']]
                tstyle = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]

                row_idx = 1
                route_total = 0.0

                for stop_num, node_id in enumerate(nodes, 1):
                    cust_name = node_name_map.get(node_id, node_id)
                    cust_data = customer_orders.get(node_id)
                    bg = colors.Color(0.96, 0.96, 1.0) if stop_num % 2 == 1 else colors.white

                    if cust_data and cust_data.get('orders'):
                        orders_list = cust_data['orders']
                        first_row = row_idx

                        for idx, order in enumerate(orders_list):
                            tdata.append([
                                str(stop_num) if idx == 0 else '',
                                Paragraph(cust_name, cell_style_8) if idx == 0 else '',
                                Paragraph(order['item_name'], cell_style_8),
                                str(order['quantity']),
                                f"{order['weight_per_unit']:.2f}",
                                f"{order['total_weight']:.2f}",
                            ])
                            route_total += order['total_weight']
                            row_idx += 1

                        tstyle.append(('BACKGROUND', (0, first_row), (-1, row_idx - 1), bg))
                        if len(orders_list) > 1:
                            tstyle.append(('SPAN', (0, first_row), (0, row_idx - 1)))
                            tstyle.append(('SPAN', (1, first_row), (1, row_idx - 1)))
                    else:
                        tdata.append([str(stop_num), Paragraph(cust_name, cell_style_8),
                                      '—', '—', '—', '—'])
                        tstyle.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg))
                        row_idx += 1

                # Total row
                tdata.append(['', 'Route Total', '', '', '', f"{route_total:.2f}"])
                tstyle.extend([
                    ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.Color(0.88, 0.88, 0.88)),
                    ('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'),
                    ('SPAN', (0, row_idx), (1, row_idx)),
                ])

                order_table = Table(tdata, colWidths=col_widths)
                order_table.setStyle(TableStyle(tstyle))
                story.append(order_table)

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
