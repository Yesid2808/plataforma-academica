import re

from django import forms
from .models import (
    AnioLectivo,
    Asignatura,
    CargaAcademica,
    Estudiante,
    Grado,
    Grupo,
    PeriodoAcademico,
)


DATE_INPUT_FORMAT = '%Y-%m-%d'


def _normalizar_numero(valor):
    return re.sub(r'\D', '', str(valor or ''))


class EstudianteBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_nacimiento'].input_formats = [DATE_INPUT_FORMAT]
        self.fields['grupo'].queryset = Grupo.objects.select_related('grado').filter(activo=True).order_by(
            'grado__nombre',
            'nombre'
        )

    def clean_documento(self):
        documento = _normalizar_numero(self.cleaned_data.get('documento'))
        if not documento:
            raise forms.ValidationError('Ingresa un numero de documento valido.')
        if len(documento) < 8:
            raise forms.ValidationError('El numero de documento debe tener al menos 8 digitos para verse real.')
        return documento

    def clean_whatsapp(self):
        return _normalizar_numero(self.cleaned_data.get('whatsapp'))

    def clean_telefono_acudiente(self):
        telefono = _normalizar_numero(self.cleaned_data.get('telefono_acudiente'))
        if not telefono:
            raise forms.ValidationError('Ingresa un telefono del acudiente valido.')
        return telefono

    def clean_whatsapp_acudiente(self):
        return _normalizar_numero(self.cleaned_data.get('whatsapp_acudiente'))


class EstudianteForm(EstudianteBaseForm):
    class Meta:
        model = Estudiante
        fields = [
            'tipo_documento',
            'documento',
            'nombres',
            'apellidos',
            'genero',
            'fecha_nacimiento',
            'grupo',
            'foto',
            'correo',
            'whatsapp',
            'acudiente',
            'correo_acudiente',
            'telefono_acudiente',
            'whatsapp_acudiente',
            'direccion',
            'activo',
        ]
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'documento': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '20', 'placeholder': 'Solo numeros'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'fecha_nacimiento': forms.DateInput(
                format=DATE_INPUT_FORMAT,
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'grupo': forms.Select(attrs={'class': 'form-select'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '20', 'placeholder': 'Solo numeros'}),
            'acudiente': forms.TextInput(attrs={'class': 'form-control'}),
            'correo_acudiente': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono_acudiente': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '20', 'placeholder': 'Solo numeros'}),
            'whatsapp_acudiente': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '20', 'placeholder': 'Solo numeros'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.Select(
                choices=[(True, 'Activo'), (False, 'Inactivo')],
                attrs={'class': 'form-select'}
            ),
        }



class EstudianteUpdateForm(EstudianteBaseForm):
    codigo = forms.CharField(
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Estudiante
        fields = [
            'tipo_documento',
            'documento',
            'nombres',
            'apellidos',
            'genero',
            'fecha_nacimiento',
            'grupo',
            'foto',
            'correo',
            'whatsapp',
            'acudiente',
            'correo_acudiente',
            'telefono_acudiente',
            'whatsapp_acudiente',
            'direccion',
            'activo',
        ]
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'documento': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '20', 'placeholder': 'Solo numeros'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'fecha_nacimiento': forms.DateInput(
                format=DATE_INPUT_FORMAT,
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'grupo': forms.Select(attrs={'class': 'form-select'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '20', 'placeholder': 'Solo numeros'}),
            'acudiente': forms.TextInput(attrs={'class': 'form-control'}),
            'correo_acudiente': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono_acudiente': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '20', 'placeholder': 'Solo numeros'}),
            'whatsapp_acudiente': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '20', 'placeholder': 'Solo numeros'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.Select(
                choices=[(True, 'Activo'), (False, 'Inactivo')],
                attrs={'class': 'form-select'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['codigo'].initial = self.instance.codigo


class ImportarEstudiantesForm(forms.Form):
    archivo = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )


class AnioLectivoForm(forms.ModelForm):
    class Meta:
        model = AnioLectivo
        fields = ['anio', 'activo']
        widgets = {
            'anio': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000', 'max': '2100'}),
            'activo': forms.Select(choices=[(True, 'Activo'), (False, 'Inactivo')], attrs={'class': 'form-select'}),
        }


class PeriodoAcademicoForm(forms.ModelForm):
    class Meta:
        model = PeriodoAcademico
        fields = ['nombre', 'numero', 'fecha_inicio', 'fecha_fin', 'anio_lectivo', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '4'}),
            'fecha_inicio': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'anio_lectivo': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.Select(choices=[(True, 'Activo'), (False, 'Inactivo')], attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_inicio'].input_formats = ['%Y-%m-%d']
        self.fields['fecha_fin'].input_formats = ['%Y-%m-%d']


class GradoForm(forms.ModelForm):
    class Meta:
        model = Grado
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }


class GrupoForm(forms.ModelForm):
    class Meta:
        model = Grupo
        fields = ['nombre', 'grado', 'director_grupo', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'grado': forms.Select(attrs={'class': 'form-select'}),
            'director_grupo': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.Select(choices=[(True, 'Activo'), (False, 'Inactivo')], attrs={'class': 'form-select'}),
        }


class AsignaturaForm(forms.ModelForm):
    class Meta:
        model = Asignatura
        fields = ['nombre', 'intensidad_horaria', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'intensidad_horaria': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'activa': forms.Select(choices=[(True, 'Activa'), (False, 'Inactiva')], attrs={'class': 'form-select'}),
        }


class CargaAcademicaForm(forms.ModelForm):
    class Meta:
        model = CargaAcademica
        fields = ['docente', 'grupo', 'asignatura', 'anio_lectivo', 'activo']
        widgets = {
            'docente': forms.Select(attrs={'class': 'form-select'}),
            'grupo': forms.Select(attrs={'class': 'form-select'}),
            'asignatura': forms.Select(attrs={'class': 'form-select'}),
            'anio_lectivo': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.Select(choices=[(True, 'Activa'), (False, 'Inactiva')], attrs={'class': 'form-select'}),
        }
