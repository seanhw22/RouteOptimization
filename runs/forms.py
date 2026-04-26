"""Solver configuration form (per-algorithm parameters)."""

from django import forms


class SolverConfigForm(forms.Form):
    run_greedy = forms.BooleanField(required=False, initial=True, label='Greedy')
    run_hga = forms.BooleanField(required=False, initial=True, label='HGA')
    run_milp = forms.BooleanField(required=False, initial=False, label='MILP (≤25 nodes only)')

    # HGA parameters
    generations = forms.IntegerField(min_value=1, max_value=10000, initial=100)
    population_size = forms.IntegerField(min_value=2, max_value=2000, initial=50)
    mutation_rate = forms.FloatField(min_value=0.0, max_value=1.0, initial=0.1)
    crossover_rate = forms.FloatField(min_value=0.0, max_value=1.0, initial=0.8)
    seed = forms.IntegerField(initial=42)

    # MILP parameter
    milp_time_limit = forms.IntegerField(
        min_value=10, max_value=86400, initial=3600,
        help_text='Maximum seconds for the MILP solver (Gurobi).'
    )

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
            raise forms.ValidationError('Pick at least one algorithm to run.')
        if cleaned.get('run_milp') and not self.milp_available:
            raise forms.ValidationError('MILP is not available for datasets larger than 25 nodes.')
        return cleaned
