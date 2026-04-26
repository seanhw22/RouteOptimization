"""Dataset import services: parse uploaded CSV/XLSX files into DB rows."""

import io
from datetime import timedelta
from typing import Dict

import pandas as pd
from django.db import transaction
from django.utils import timezone

from .models import Customer, Dataset, Depot, Item, Node, Order, Vehicle


REQUIRED_COLUMNS = {
    'depots': {'depot_id', 'x', 'y'},
    'customers': {'customer_id', 'x', 'y', 'deadline_hours'},
    'vehicles': {'vehicle_id', 'depot_id', 'vehicle_type', 'capacity_kg', 'max_operational_hrs', 'speed_kmh'},
    'items': {'item_id', 'weight_kg', 'expiry_hours'},
    'orders': {'customer_id', 'item_id', 'quantity'},
}


class DatasetValidationError(ValueError):
    """Raised when uploaded files fail validation."""


def parse_uploaded(form_files) -> Dict[str, pd.DataFrame]:
    """Return ``{'depots': df, 'customers': df, ...}`` from an upload form's files.

    Accepts either a single XLSX or five CSVs (form layer enforces which).
    """
    xlsx = form_files.get('xlsx')
    if xlsx:
        try:
            sheets = pd.read_excel(xlsx, sheet_name=None)
        except Exception as e:
            raise DatasetValidationError(f'Could not read XLSX: {e}') from e
        missing = set(REQUIRED_COLUMNS) - {name.lower() for name in sheets}
        if missing:
            raise DatasetValidationError(f'XLSX is missing required sheet(s): {", ".join(sorted(missing))}')
        return {key: sheets[key] for key in REQUIRED_COLUMNS}

    out = {}
    for entity in REQUIRED_COLUMNS:
        f = form_files.get(f'{entity}_csv')
        if f is None:
            raise DatasetValidationError(f'Missing CSV for {entity}.')
        try:
            out[entity] = pd.read_csv(f)
        except Exception as e:
            raise DatasetValidationError(f'Could not read {entity}.csv: {e}') from e
    return out


def validate_frames(frames: Dict[str, pd.DataFrame]) -> None:
    """Check that every required column is present and IDs unique within each table."""
    for entity, required in REQUIRED_COLUMNS.items():
        df = frames[entity]
        missing = required - set(df.columns)
        if missing:
            raise DatasetValidationError(
                f'{entity}.csv is missing required column(s): {", ".join(sorted(missing))}'
            )

    for entity, id_col in (
        ('depots', 'depot_id'),
        ('customers', 'customer_id'),
        ('vehicles', 'vehicle_id'),
        ('items', 'item_id'),
    ):
        df = frames[entity]
        dup = df[df.duplicated(id_col, keep=False)][id_col].unique().tolist()
        if dup:
            raise DatasetValidationError(
                f'Duplicate {id_col} value(s) in {entity}.csv: {", ".join(map(str, dup))}'
            )

    # Cross-table referential checks
    customer_ids = set(frames['customers']['customer_id'].astype(str))
    item_ids = set(frames['items']['item_id'].astype(str))
    depot_ids = set(frames['depots']['depot_id'].astype(str))

    bad_orders_customers = sorted(set(frames['orders']['customer_id'].astype(str)) - customer_ids)
    if bad_orders_customers:
        raise DatasetValidationError(
            f'orders.csv references unknown customer_id(s): {", ".join(bad_orders_customers)}'
        )
    bad_orders_items = sorted(set(frames['orders']['item_id'].astype(str)) - item_ids)
    if bad_orders_items:
        raise DatasetValidationError(
            f'orders.csv references unknown item_id(s): {", ".join(bad_orders_items)}'
        )
    bad_vehicles_depots = sorted(set(frames['vehicles']['depot_id'].astype(str)) - depot_ids)
    if bad_vehicles_depots:
        raise DatasetValidationError(
            f'vehicles.csv references unknown depot_id(s): {", ".join(bad_vehicles_depots)}'
        )


def _prefixed(dataset_id: int, raw_id) -> str:
    """All entity ids are stored prefixed with the dataset id to keep them globally unique."""
    return f'{dataset_id}_{raw_id}'


@transaction.atomic
def save_dataset(
    *,
    name: str,
    user=None,
    session_key: str = '',
    is_guest: bool = False,
    frames: Dict[str, pd.DataFrame],
) -> Dataset:
    """Create the Dataset row and all child rows. Returns the Dataset instance.

    All entity ids are prefixed with the new dataset_id so multiple datasets
    can coexist without primary-key collisions on the underlying VARCHAR PKs.
    """
    expires_at = None
    if is_guest:
        expires_at = timezone.now() + timedelta(days=3)

    dataset = Dataset.objects.create(
        user=user,
        session_key=session_key,
        name=name,
        expires_at=expires_at,
    )
    ds_id = dataset.dataset_id

    depot_rows = []
    node_rows = []
    for _, row in frames['depots'].iterrows():
        node_id = _prefixed(ds_id, row['depot_id'])
        node_rows.append(Node(node_id=node_id, dataset=dataset, x=float(row['x']), y=float(row['y'])))
    Node.objects.bulk_create(node_rows)
    for _, row in frames['depots'].iterrows():
        depot_id = _prefixed(ds_id, row['depot_id'])
        depot_rows.append(Depot(depot_id=depot_id, node_id=depot_id, dataset=dataset))
    Depot.objects.bulk_create(depot_rows)

    customer_node_rows = []
    customer_rows = []
    for _, row in frames['customers'].iterrows():
        node_id = _prefixed(ds_id, row['customer_id'])
        customer_node_rows.append(Node(node_id=node_id, dataset=dataset, x=float(row['x']), y=float(row['y'])))
    Node.objects.bulk_create(customer_node_rows)
    for _, row in frames['customers'].iterrows():
        cid = _prefixed(ds_id, row['customer_id'])
        customer_rows.append(Customer(
            customer_id=cid, node_id=cid, dataset=dataset, deadline_hours=int(row['deadline_hours'])
        ))
    Customer.objects.bulk_create(customer_rows)

    vehicle_rows = []
    for _, row in frames['vehicles'].iterrows():
        vehicle_rows.append(Vehicle(
            vehicle_id=_prefixed(ds_id, row['vehicle_id']),
            depot_id=_prefixed(ds_id, row['depot_id']),
            dataset=dataset,
            vehicle_type=str(row['vehicle_type']),
            capacity_kg=float(row['capacity_kg']),
            max_operational_hrs=float(row['max_operational_hrs']),
            speed_kmh=float(row['speed_kmh']),
        ))
    Vehicle.objects.bulk_create(vehicle_rows)

    item_rows = []
    for _, row in frames['items'].iterrows():
        item_rows.append(Item(
            item_id=_prefixed(ds_id, row['item_id']),
            dataset=dataset,
            weight_kg=float(row['weight_kg']),
            expiry_hours=int(row['expiry_hours']),
        ))
    Item.objects.bulk_create(item_rows)

    order_rows = []
    for _, row in frames['orders'].iterrows():
        order_rows.append(Order(
            customer_id=_prefixed(ds_id, row['customer_id']),
            item_id=_prefixed(ds_id, row['item_id']),
            dataset=dataset,
            quantity=int(row['quantity']),
        ))
    Order.objects.bulk_create(order_rows)

    return dataset
