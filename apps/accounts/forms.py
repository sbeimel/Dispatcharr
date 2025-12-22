from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group as AuthGroup
from apps.channels.models import ChannelGroup
from .models import User

from .models import User


class UserRegistrationForm(UserCreationForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=AuthGroup.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = User
        fields = ['username', 'groups', 'password1', 'password2', ]

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            self.save_m2m()  # Save the many-to-many field data
        return user



class GroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = AuthGroup
        fields = ['name', 'permissions']


class UserEditForm(forms.ModelForm):
    auth_groups = forms.ModelMultipleChoiceField(
        queryset=AuthGroup.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Auth Groups"
    )
    channel_groups = forms.ModelMultipleChoiceField(
        queryset=ChannelGroup.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Channel Groups"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'auth_groups', 'channel_groups']
