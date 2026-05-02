from django import forms

from academico.models import CargaAcademica


class AsistenciaFiltroForm(forms.Form):
    carga_academica = forms.ModelChoiceField(
        queryset=CargaAcademica.objects.filter(activo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Carga academica'
    )

    def __init__(self, *args, **kwargs):
        cargas = kwargs.pop('cargas', None)
        super().__init__(*args, **kwargs)
        if cargas is not None:
            self.fields['carga_academica'].queryset = cargas
