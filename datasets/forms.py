"""Forms for the datasets app: file-upload + dataset-name."""

from django import forms


class DatasetUploadForm(forms.Form):
    """Either an XLSX file with depots/customers/vehicles/items/orders sheets,
    OR five CSV files. The upload_type field controls which path is active."""

    UPLOAD_TYPE_CHOICES = [
        ('', '— choose a format —'),
        ('xlsx', 'Single XLSX workbook'),
        ('csv', 'Five individual CSV files'),
    ]

    name = forms.CharField(
        max_length=255,
        required=True,
        help_text='A label you can recognise later.',
        error_messages={'required': 'Enter a name for this dataset.'},
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Jakarta West Region 7-node'}),
    )
    upload_type = forms.ChoiceField(
        choices=UPLOAD_TYPE_CHOICES,
        required=True,
        label='Upload format',
        error_messages={'required': 'Choose an upload format (XLSX or CSV).'},
    )

    xlsx = forms.FileField(required=False, help_text='Single .xlsx with all five sheets.')

    depots_csv = forms.FileField(required=False, help_text='depot_id, x, y [, name]')
    customers_csv = forms.FileField(required=False, help_text='customer_id, x, y, deadline_hours [, name]')
    vehicles_csv = forms.FileField(required=False, help_text='vehicle_id, depot_id, vehicle_type, capacity_kg, max_operational_hrs, speed_kmh [, name]')
    items_csv = forms.FileField(required=False, help_text='item_id, weight_kg, expiry_hours [, name]')
    orders_csv = forms.FileField(required=False, help_text='customer_id, item_id, quantity')

    def clean(self):
        cleaned = super().clean()
        upload_type = cleaned.get('upload_type')

        if upload_type == 'xlsx':
            if not cleaned.get('xlsx'):
                self.add_error('xlsx', 'Please upload an XLSX file.')
        elif upload_type == 'csv':
            missing = {
                'depots_csv': 'depots',
                'customers_csv': 'customers',
                'vehicles_csv': 'vehicles',
                'items_csv': 'items',
                'orders_csv': 'orders',
            }
            for field, label in missing.items():
                if not cleaned.get(field):
                    self.add_error(field, f'Please upload the {label} CSV file.')

        return cleaned
