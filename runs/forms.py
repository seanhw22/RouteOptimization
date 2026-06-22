"""Solver configuration form (per-algorithm parameters)."""

from django import forms
from django.utils.translation import gettext_lazy as _


class SolverConfigForm(forms.Form):
    run_greedy = forms.BooleanField(required=False, initial=True, label='Greedy')
    run_hga = forms.BooleanField(required=False, initial=True, label='HGA')
    run_milp = forms.BooleanField(required=False, initial=False, label=_('MILP (≤25 nodes only)'))
    generations = forms.IntegerField(min_value=1, max_value=10000, initial=100, error_messages={'required': _('Enter the number of generations.')})
    population_size = forms.IntegerField(min_value=2, max_value=2000, initial=50, error_messages={'required': _('Enter the population size.')})
    mutation_rate = forms.FloatField(min_value=0.0, max_value=1.0, initial=0.1, error_messages={'required': _('Enter the mutation rate.')})
    crossover_rate = forms.FloatField(min_value=0.0, max_value=1.0, initial=0.8, error_messages={'required': _('Enter the crossover rate.')})
    no_improve_limit = forms.IntegerField(min_value=1, max_value=1000, initial=20, help_text=_('Stop early if no significant improvement for this many generations.'), error_messages={'required': _('Enter the no-improvement limit.')})
    seed = forms.IntegerField(initial=42, error_messages={'required': _('Enter the random seed.')})
    milp_time_limit = forms.IntegerField(min_value=10, max_value=86400, initial=3600, help_text=_('Maximum seconds for the MILP solver (Gurobi).'), error_messages={'required': _('Enter the MILP time limit in seconds.')})

    def __init__(self, *args, milp_available: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.milp_available = milp_available
        if not milp_available:
            self.fields['run_milp'].disabled = True
            self.fields['run_milp'].initial = False
            self.fields['milp_time_limit'].disabled = True

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get(k) for k in ('run_greedy', 'run_hga', 'run_milp')):
            raise forms.ValidationError(_('Pick at least one algorithm to run.'))
        if cleaned.get('run_milp') and not self.milp_available:
            raise forms.ValidationError(_('MILP is not available for datasets larger than 25 nodes.'))
        return cleaned
