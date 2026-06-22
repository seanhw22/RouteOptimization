"""Forms for uploading and naming datasets."""

from django import forms
from django.utils.translation import gettext_lazy as _


class DatasetUploadForm(forms.Form):
    UPLOAD_TYPE_CHOICES = [('', _('— choose a format —')), ('xlsx', _('Single XLSX workbook')), ('csv', _('Five individual CSV files'))]
    name = forms.CharField(max_length=255, required=True, label=_('Dataset name'), help_text=_('A label you can recognise later.'), error_messages={'required': _('Enter a name for this dataset.')}, widget=forms.TextInput(attrs={'placeholder': _('e.g. Jakarta West Region 7-node')}))
    upload_type = forms.ChoiceField(choices=UPLOAD_TYPE_CHOICES, required=True, label=_('Upload format'), error_messages={'required': _('Choose an upload format (XLSX or CSV).')})
    xlsx = forms.FileField(required=False, label=_('XLSX workbook'), help_text=_('Single .xlsx with all five sheets.'))
    depots_csv = forms.FileField(required=False, label=_('Depots CSV'), help_text='depot_id, x, y [, name]')
    customers_csv = forms.FileField(required=False, label=_('Customers CSV'), help_text='customer_id, x, y, deadline_hours [, name]')
    vehicles_csv = forms.FileField(required=False, label=_('Vehicles CSV'), help_text='vehicle_id, depot_id, vehicle_type, capacity_kg, max_operational_hrs, speed_kmh [, name]')
    items_csv = forms.FileField(required=False, label=_('Items CSV'), help_text='item_id, weight_kg, expiry_hours [, name]')
    orders_csv = forms.FileField(required=False, label=_('Orders CSV'), help_text='customer_id, item_id, quantity')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('upload_type') == 'xlsx' and not cleaned.get('xlsx'):
            self.add_error('xlsx', _('Please upload an XLSX file.'))
        elif cleaned.get('upload_type') == 'csv':
            for field, label in {'depots_csv': 'depots', 'customers_csv': 'customers', 'vehicles_csv': 'vehicles', 'items_csv': 'items', 'orders_csv': 'orders'}.items():
                if not cleaned.get(field):
                    self.add_error(field, _('Please upload the %(label)s CSV file.') % {'label': label})
        return cleaned
