
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class MessageForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea(attrs={"rows":2}), required=False)
    files = MultipleFileField(required=False)


class FriendRequestForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-800',
            'placeholder': 'Enter username',
        })
    )

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user

    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError("User not found.")
        
        if user == self.current_user:
            raise forms.ValidationError("You cannot send a friend request to yourself.")
        
        return username


class InvitationLinkForm(forms.Form):
    max_uses = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-800',
        })
    )
    expires_in_days = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=30,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-800',
            'placeholder': 'Leave empty for no expiration',
        })
    )

 