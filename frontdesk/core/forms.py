"""
Forms for J. Austin Front Desk Processing.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Customer, Appointment, TextTemplate, Match


class LoginForm(AuthenticationForm):
    """Custom login form with Bootstrap styling."""

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username",
                "autofocus": True,
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
            }
        )
    )


class CustomerForm(forms.ModelForm):
    """Form for creating/editing customers."""

    class Meta:
        model = Customer
        fields = [
            "name",
            "phone",
            "email",
            "category",
            "bullion_type",
            "bullion_amount",
            "price_per_oz",
            "notes",
            "status",
            "source",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "bullion_type": forms.Select(attrs={"class": "form-select"}),
            "bullion_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "price_per_oz": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "source": forms.Select(attrs={"class": "form-select"}),
        }


class AppointmentForm(forms.ModelForm):
    """Form for creating/editing appointments."""

    class Meta:
        model = Appointment
        fields = [
            "customer",
            "match",
            "datetime",
            "end_datetime",
            "purpose",
            "location",
            "status",
            "notes",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "match": forms.Select(attrs={"class": "form-select"}),
            "datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "purpose": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["match"].required = False
        self.fields["end_datetime"].required = False
        self.fields["datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]


class TextTemplateForm(forms.ModelForm):
    """Form for creating/editing text templates."""

    class Meta:
        model = TextTemplate
        fields = ["name", "content", "category", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SendTextForm(forms.Form):
    """Form for sending a text message."""

    customer_ids = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Comma-separated customer IDs",
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Type your message..."}),
    )
    template_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )
