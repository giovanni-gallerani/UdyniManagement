from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth import forms as auth_forms
from django.conf import settings

from AccountManagement.models import RegistrationRequest # import the settings file
from AccountManagement.ldap import UdyniLdap

UserModel = get_user_model()


class SetPasswordForm(auth_forms.SetPasswordForm):
    ldap = None

    # Override save method to save to LDAP
    def save(self, commit=True):
        if not commit:
            return self.user

        # Change password
        if self.ldap is None:
            self.ldap = UdyniLdap()
        self.ldap.changePassword(self.user.get_username(), self.cleaned_data['new_password1'])

        # Update the unusable user password in django to invalidate the token
        self.user.set_unusable_password()
        self.user.save()


class PasswordChangeForm(SetPasswordForm):
    """
    A form that lets a user change their password by entering their old
    password.
    """

    error_messages = {
        **SetPasswordForm.error_messages,
        "password_incorrect": "Your old password was entered incorrectly. Please enter it again.",
    }
    old_password = forms.CharField(
        label="Old password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "autofocus": True}
        ),
    )

    field_order = ["old_password", "new_password1", "new_password2"]

    def clean_old_password(self):
        """ Validate that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if self.ldap is None:
            self.ldap = UdyniLdap()
        if not self.ldap.checkPassword(self.user.get_username(), old_password):
            raise ValidationError(
                self.error_messages["password_incorrect"],
                code="password_incorrect",
            )
        return old_password


class PasswordResetForm(auth_forms.PasswordResetForm):
    def get_users(self, email):
        """Given an email, return matching user(s) who should receive a reset.
        """
        email_field_name = UserModel.get_email_field_name()
        active_users = UserModel._default_manager.filter(
            **{
                "%s__iexact" % email_field_name: email,
                "is_active": True,
            }
        )
        return (
            u
            for u in active_users
            if auth_forms._unicode_ci_compare(email, getattr(u, email_field_name))
        )

# Registration form
class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        max_length=32,
        label="Password",
        help_text=password_validation.password_validators_help_text_html(),
        widget=forms.PasswordInput()
    )
    password_confirm = forms.CharField(
        max_length=32,
        label="Confirm password",
        help_text="Enter the same password as before, for verification.",
        widget=forms.PasswordInput()
    )

    def clean_password(self):
        # Create a fake user for password validation
        temp_user = UserModel()
        temp_user.username = self.cleaned_data['name'][0].lower() + "".join(self.cleaned_data['surname'].lower().split())
        temp_user.first_name = self.cleaned_data['name']
        temp_user.last_name = self.cleaned_data['surname']
        temp_user.email = self.cleaned_data['email']
        password_validation.validate_password(self.cleaned_data['password'], temp_user)
        return self.cleaned_data['password']

    def clean_password_confirm(self):
        if 'password' in self.cleaned_data and self.cleaned_data['password'] != self.cleaned_data['password_confirm']:
            raise ValidationError("The two password do not match")
        return self.cleaned_data['password_confirm']

    class Meta:
        model = RegistrationRequest
        fields = ('name', 'surname', 'email')


class AccountCreationForm(forms.Form):
    admin = forms.CharField(label="Admin username", max_length=64, required=True)
    admin_psw = forms.CharField(label="Admin password", max_length=64, required=True, widget=forms.PasswordInput())
    username = forms.CharField(label="Username", max_length=64, required=True)
    name = forms.CharField(label="Name", max_length=64, required=True)
    surname = forms.CharField(label="Surname", max_length=64, required=True)
    email = forms.EmailField(label="E-mail", required=True)
    uid = forms.IntegerField(label="User ID number")
    homedir = forms.CharField(label="Home directory", max_length=128)
    shell = forms.CharField(label="Login shell", max_length=32)
    send_email = forms.BooleanField(label="Send notification", help_text="Send a notification email to the user", required=False)


class AccountRejectionForm(forms.Form):
    send_email = forms.BooleanField(label="Send notification", help_text="Send a notification email to the user", required=False)
    purge_request = forms.BooleanField(label="Purge request", help_text="If the request is not purged, the user will not be able to submit a new request with the same email address", required=False)
    custom_message = forms.CharField(label="Custom rejection message", max_length=4096, required=False, widget=forms.Textarea(), help_text="Custom rejection message that replace the default one (max. 4096 characters)")


class UserDeleteForm(forms.Form):
    delete_ldap = forms.BooleanField(label="Remove from LDAP", help_text="Remove the user also from the LDAP directory", required=False)
    admin = forms.CharField(label="Admin username", max_length=64, required=True)
    admin_psw = forms.CharField(label="Admin password", max_length=64, required=True, widget=forms.PasswordInput())


class EditProfileForm(forms.Form):
    ldap = None
    mail = forms.EmailField(label="Mail")
    mobile = forms.CharField(label="Mobile number", required=False)
    roomNumber = forms.CharField(label="Office room number", required=False)
    sshPublicKey = forms.CharField(label="SSH publick key", widget=forms.Textarea(), required=False)
    jpegPhoto = forms.ImageField(label="Profile picture", required=False)
    user_password = forms.CharField(label="User password", widget=forms.PasswordInput(), help_text="Insert your password to save modifications")

    def __init__(self, *args, **kwargs):
        self.username = kwargs.pop('username')
        super().__init__(*args, **kwargs)

    def clean_user_password(self):
        try:
            self.ldap = UdyniLdap(self.username, self.cleaned_data['user_password'])
            return self.cleaned_data['user_password']
        except Exception as e:
            raise ValidationError(f"Failed to login to LDAP directory (Error: {e})")
