"""Forms for the datasets app: file-upload + dataset-name."""

from django import forms


class DatasetUploadForm(forms.Form):
    """Either an XLSX file with depots/customers/vehicles/items/orders sheets,
    OR five CSV files. The view picks the right loader path based on what was
    submitted."""

    name = forms.CharField(max_length=255, required=True, help_text='A label you can recognise later.')

    xlsx = forms.FileField(required=False, help_text='Single .xlsx with all five sheets.')

    depots_csv = forms.FileField(required=False, help_text='depot_id, x, y')
    customers_csv = forms.FileField(required=False, help_text='customer_id, x, y, deadline_hours')
    vehicles_csv = forms.FileField(required=False, help_text='vehicle_id, depot_id, vehicle_type, capacity_kg, max_operational_hrs, speed_kmh')
    items_csv = forms.FileField(required=False, help_text='item_id, weight_kg, expiry_hours')
    orders_csv = forms.FileField(required=False, help_text='customer_id, item_id, quantity')

    def clean(self):
        cleaned = super().clean()
        has_xlsx = bool(cleaned.get('xlsx'))
        csv_fields = ('depots_csv', 'customers_csv', 'vehicles_csv', 'items_csv', 'orders_csv')
        csvs = [cleaned.get(f) for f in csv_fields]
        has_all_csvs = all(csvs)
        has_any_csv = any(csvs)

        if has_xlsx and has_any_csv:
            raise forms.ValidationError('Provide either an XLSX file OR the five CSVs, not both.')
        if not has_xlsx and not has_all_csvs:
            raise forms.ValidationError('Upload an XLSX file or all five CSV files (depots, customers, vehicles, items, orders).')
        return cleaned
