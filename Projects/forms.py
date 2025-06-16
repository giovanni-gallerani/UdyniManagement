from django import forms
from Projects.models import ResearcherRole, Project


class ResearcherRoleForm(forms.ModelForm):

    start_date = forms.DateField(input_formats=['%d/%m/%Y', '%Y-%m-%d'], widget=forms.DateInput())

    class Meta:
        model = ResearcherRole
        fields = ['researcher', 'role', 'start_date']
        widgets = {
            'researcher': forms.HiddenInput,
        }


class ProjectForm(forms.ModelForm):

    sigla_progetti = forms.CharField(label="Project on SIGLA", widget=forms.Select(), required=False)

    class Meta:
        model = Project
        fields = ['name', 'agency', 'reference', 'pi', 'depreciation', 'sigla_name', 'sigla_id', 'sigla_cup']
        widgets = {
            'sigla_id': forms.HiddenInput(),
            'sigla_cup': forms.HiddenInput(),
            'sigla_name': forms.HiddenInput(),
        }
