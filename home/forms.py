import re
from django import forms
from .models import Donor,Receiver, BloodRequest
from datetime import date

class DonorForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = [
            "blood_group",
            "age",
            "weight",
            "last_donation",
        ]
        widgets = {
            "blood_group": forms.Select(attrs={"class": "form-select"}),
            "age": forms.NumberInput(attrs={"class": "form-control"}),
            "weight": forms.NumberInput(attrs={"class": "form-control"}),
            "last_donation": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }

    def clean_age(self):
        age = self.cleaned_data.get("age")
        if age is not None and age < 18:
            raise forms.ValidationError("Donor must be at least 18 years old.")
        return age

    def clean_weight(self):
        weight = self.cleaned_data.get("weight")
        if weight < 50:
            raise forms.ValidationError("Minimum weight required is 50 kg.")
        return weight
    
class ReceiverForm(forms.ModelForm):
    class Meta:
        model = Receiver
        fields = ["hospital","contact_person",
            "phone","address"]
        widgets = {
            "hospital": forms.TextInput(attrs={"class": "form-control"}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        def clean_phone(self):
            phone = self.cleaned_data.get("phone")

            pattern = r"^[6-9]\d{9}$"
            if not re.match(pattern, phone):
                raise forms.ValidationError(
                "Enter a valid 10-digit mobile number."
            )

            return phone

class BloodRequestForm(forms.ModelForm):
    class Meta:
        model = BloodRequest
        fields = ["blood_group", "units_required", "required_date", "emergency"]
        widgets = {
            "blood_group": forms.Select(attrs={"class": "form-select"}),
            "units_required": forms.NumberInput(attrs={"class": "form-control"}),
            "required_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "emergency": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
