from django import forms
from django.contrib.auth.hashers import make_password
from .models import Learner

class RegisterForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        label="Confirmer le mot de passe"
    )
    accept_terms = forms.BooleanField(
        required=True,
        label="J'accepte les conditions"
    )

    class Meta:
        model = Learner
        fields = ['name', 'email', 'password']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Votre nom'}),
            'email': forms.EmailInput(attrs={'placeholder': 'votre@email.com'}),
            'password': forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Learner.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        
        if password and len(password) < 6:
            raise forms.ValidationError("Le mot de passe doit contenir au moins 6 caractères.")
        
        return cleaned_data

    def save(self, commit=True):
        learner = super().save(commit=False)
        # Hasher le mot de passe avant sauvegarde
        learner.password = make_password(self.cleaned_data["password"])
        if commit:
            learner.save()
        return learner