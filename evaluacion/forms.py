from django import forms

from .models import ActividadEvaluativa


class ActividadEvaluativaForm(forms.ModelForm):
    class Meta:
        model = ActividadEvaluativa
        fields = [
            'carga_academica',
            'periodo',
            'dimension',
            'nombre',
            'porcentaje',
            'fecha',
            'activa',
        ]
        widgets = {
            'carga_academica': forms.Select(attrs={'class': 'form-select'}),
            'periodo': forms.Select(attrs={'class': 'form-select'}),
            'dimension': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'porcentaje': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'activa': forms.Select(
                choices=[(True, 'Activa'), (False, 'Inactiva')],
                attrs={'class': 'form-select'}
            ),
        }

    def __init__(self, *args, **kwargs):
        cargas = kwargs.pop('cargas', None)
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = ['%Y-%m-%d']
        if cargas is not None:
            self.fields['carga_academica'].queryset = cargas

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        self.instance.carga_academica = cleaned_data.get('carga_academica')
        self.instance.periodo = cleaned_data.get('periodo')
        self.instance.dimension = cleaned_data.get('dimension')
        self.instance.nombre = cleaned_data.get('nombre')
        self.instance.porcentaje = cleaned_data.get('porcentaje')
        self.instance.fecha = cleaned_data.get('fecha')
        self.instance.activa = cleaned_data.get('activa')
        self.instance.clean()
        return cleaned_data
