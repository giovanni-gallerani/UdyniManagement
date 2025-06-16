from django import forms
from Accounting.models import GAE


class GaeForm(forms.ModelForm):

    sigla_gae = forms.CharField(label="GAE on SIGLA", widget=forms.Select(), required=False)

    class Meta:
        model = GAE
        fields = ['project', 'name', 'description', 'include_funding']
        widgets = {
            'name': forms.HiddenInput(),
            'description': forms.HiddenInput(),
        }
