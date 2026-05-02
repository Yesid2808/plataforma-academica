from django import forms

from .models import SeguimientoAlerta


class SeguimientoAlertaForm(forms.ModelForm):
    class Meta:
        model = SeguimientoAlerta
        fields = ['accion', 'descripcion', 'resultado', 'proxima_revision']
        widgets = {
            'accion': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe la intervencion realizada, acuerdos o evidencias relevantes.',
            }),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'proxima_revision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
