import base64
import re
import uuid
from io import BytesIO
from PIL import Image

from typing import OrderedDict
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.template import loader as template_loader
from django.views.generic import View, TemplateView
from django.views.generic.edit import CreateView
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import auth
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import Permission
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin

from UdyniManagement.menu import UdyniMenu
from UdyniManagement.views import ListViewMenu, CreateViewMenu, TemplateViewMenu, UpdateViewMenu, DeleteViewMenu, FormViewMenu, udyni_error_view
from AccountManagement.ldap import UdyniLdap
from AccountManagement.forms import SetPasswordForm, PasswordChangeForm, PasswordResetForm, RegistrationForm, AccountCreationForm, AccountRejectionForm, UserDeleteForm, EditProfileForm
from AccountManagement.models import RegistrationRequest


# =======================
# Login/Logout

class LoginView(auth_views.LoginView):
    template_name = 'AccountManagement/login.html'
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    template_name = 'AccountManagement/logged_out.html'


# =======================
# Password change/reset

class PasswordResetView(auth_views.PasswordResetView):
    template_name = "AccountManagement/passwordreset.html"
    success_url = reverse_lazy('account_password_reset_done')
    subject_template_name = "AccountManagement/account_management_subject.txt"
    email_template_name = "AccountManagement/password_reset_email.html"
    extra_email_context = {'subject': 'Password reset'}
    from_email = settings.DEFAULT_FROM_EMAIL
    form_class = PasswordResetForm


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "AccountManagement/passwordreset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "AccountManagement/passwordreset_confirm.html"
    form_class = SetPasswordForm
    success_url = reverse_lazy('account_password_reset_complete')


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "AccountManagement/passwordreset_complete.html"


class AccountPasswordChange(LoginRequiredMixin, auth_views.PasswordChangeView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy("account_password_change_done")
    template_name = "UdyniManagement/generic_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Change password"
        context['back_url'] = reverse_lazy('main_page')
        context['menu'] = UdyniMenu().getMenu(self.request.user)
        return context


class AccountPasswordChangeDone(LoginRequiredMixin, TemplateViewMenu):
    template_name = "AccountManagement/passwordchange_done.html"


# =======================
# Registration

class AccountRegistration(CreateView):
    model = RegistrationRequest
    form_class = RegistrationForm
    template_name = 'AccountManagement/registration.html'
    success_url = reverse_lazy('account_registration_complete')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Purge old requests
        RegistrationRequest.PurgeOldRequests()
        return context

    def form_valid(self, form):
        # Update instance with status and UUID
        form.instance.uuid = uuid.uuid4().hex
        form.instance.status = RegistrationRequest.SUBMITTED

        # Create password hashes
        form.instance.ldap_hash = UdyniLdap.createLdapHash(form.cleaned_data['password']).decode()
        form.instance.samba_hash = UdyniLdap.createSambaHash(form.cleaned_data['password']).decode()
        print(len(form.instance.ldap_hash), form.instance.ldap_hash)
        print(len(form.instance.samba_hash), form.instance.samba_hash)

        # Send verification email
        current_site = get_current_site(self.request)
        email_context = {
            "protocol": "https" if self.request.is_secure() else "http",
            "domain": current_site.domain,
            "token": form.instance.uuid,
        }
        msg = EmailMessage(
            to=[form.instance.email, ],
            from_email=settings.DEFAULT_FROM_EMAIL,
            subject=template_loader.render_to_string("AccountManagement/account_management_subject.txt", {'subject': "Email verification"}),
            body=template_loader.render_to_string('AccountManagement/registrationrequest_confirmation_email.html', email_context),
        )
        msg.send()

        return super().form_valid(form)


class AccountRegistrationComplete(TemplateView):
    template_name = 'AccountManagement/registrationrequest_complete.html'


class AccountRegistrationVerify(TemplateView):
    template_name = 'AccountManagement/registrationrequest_verify.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Get request
            req = RegistrationRequest.objects.get(uuid=self.kwargs['token'])

            # Update status
            req.status = RegistrationRequest.VERIFIED

            # Change UUID to invalidate the previous one
            req.uuid = uuid.uuid4().hex

            # Save
            req.save()

            # Notify admin by email that a new registration has been submitted
            admin_emails = []
            for u in auth.get_user_model().objects.all():
                if u.is_staff or u.has_perm('AccountManagement.registration_manage'):
                    admin_emails.append(u.email)

            # Send verification email
            current_site = get_current_site(self.request)
            email_context = {
                "protocol": "https" if self.request.is_secure() else "http",
                "domain": current_site.domain,
                "request": req,
            }
            msg = EmailMessage(
                to=admin_emails,
                from_email=settings.DEFAULT_FROM_EMAIL,
                subject=template_loader.render_to_string("AccountManagement/account_management_subject.txt", {'subject': "New registation request"}),
                body=template_loader.render_to_string('AccountManagement/registrationrequest_new.html', email_context),
            )
            msg.send()

            context['verified'] = True

        except RegistrationRequest.DoesNotExist:
            context['verified'] = False

        return context


class AccountRegistrationList(PermissionRequiredMixin, ListViewMenu):
    model = RegistrationRequest
    permission_required = 'AccountManagement.registration_manage'

    def get_queryset(self):
        # Purge old requests
        RegistrationRequest.PurgeOldRequests()
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Registration requests"
        return context


class AccountRegistrationAccept(PermissionRequiredMixin, FormViewMenu):
    template_name = 'UdyniManagement/generic_form.html'
    form_class = AccountCreationForm
    success_url = reverse_lazy('account_registration_manage')
    permission_required = 'AccountManagement.registration_manage'

    def dispatch(self, request, *args, **kwargs):
        # Load registration
        self.registration = get_object_or_404(RegistrationRequest, pk=self.kwargs['pk'])

        # Check status
        if self.registration.status != RegistrationRequest.VERIFIED:
            # Return error message
            return udyni_error_view(request, f"This request has a status of '{self.registration.get_status_display()}' and cannot be accepted")
        # Continue
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get registration
        context['title'] = f"Creating account for {self.registration.name} {self.registration.surname}"
        # Populate form
        if self.request.method == 'GET':
            username = self.registration.name[0].lower() + self.registration.surname.lower()
            context['form'].fields['admin'].initial = self.request.user.username
            context['form'].fields['name'].initial = self.registration.name
            context['form'].fields['surname'].initial = self.registration.surname
            context['form'].fields['email'].initial = self.registration.email
            context['form'].fields['username'].initial = username
            context['form'].fields['homedir'].initial = f"/home/{username}"
            context['form'].fields['shell'].initial = "/bin/bash"
            try:
                ldap = UdyniLdap()
                context['form'].fields['uid'].initial = ldap.getNewUid()
            except Exception as e:
                context['form'].cleaned_data = {}
                context['form'].add_error('uid', f"Cannot get new UID for LDAP (Error: {e})")
        return context

    def form_valid(self, form):
        # First create user in LDAP
        ldap = UdyniLdap(form.cleaned_data['admin'], form.cleaned_data['admin_psw'])
        username = form.cleaned_data['username']
        entry = {
            'uidNumber': form.cleaned_data.get('uid', ldap.getNewUid()),
            'givenName': form.cleaned_data['name'],
            'sn': form.cleaned_data['surname'],
            'mail': form.cleaned_data['email'],
            'homeDirectory': form.cleaned_data.get('homedir', f"/home/{username}"),
            'loginShell': form.cleaned_data.get('shell', "/bin/bash"),
            'sambaNTPassword': self.registration.samba_hash,
            'userPassword': "{SSHA}" + self.registration.ldap_hash,
        }
        ldap.createUser(username, entry)

        # Then create local linked user
        local_user = auth.get_user_model()()
        local_user.username = username
        local_user.first_name = form.cleaned_data['name']
        local_user.last_name = form.cleaned_data['surname']
        local_user.email = form.cleaned_data['email']
        local_user.is_active = True
        local_user.set_unusable_password()
        local_user.save()

        # Update registration entry
        self.registration.status = RegistrationRequest.ACCEPTED
        self.registration.save()

        # Send confirmation email to user, if needed
        if form.cleaned_data.get('send_email'):
            current_site = get_current_site(self.request)
            email_context = {
                "protocol": "https" if self.request.is_secure() else "http",
                "domain": current_site.domain,
                "request": self.registration,
                "username": username,
            }
            msg = EmailMessage(
                to=[self.registration.email, ],
                from_email=settings.DEFAULT_FROM_EMAIL,
                subject=template_loader.render_to_string("AccountManagement/account_management_subject.txt", {'subject': "Your account has been activated"}),
                body=template_loader.render_to_string('AccountManagement/registrationrequest_accepted.html', email_context),
            )
            msg.send()

        return super().form_valid(form)


class AccountRegistrationReject(PermissionRequiredMixin, FormViewMenu):
    template_name = 'UdyniManagement/generic_form.html'
    permission_required = 'AccountManagement.registration_manage'
    form_class = AccountRejectionForm
    success_url = reverse_lazy('account_registration_manage')

    def dispatch(self, request, *args, **kwargs):
        # Load registration
        self.registration = get_object_or_404(RegistrationRequest, pk=self.kwargs['pk'])

        # Check status
        if self.registration.status != RegistrationRequest.VERIFIED:
            # Return error message
            return udyni_error_view(request, f"This request has a status of '{self.registration.get_status_display()}' and cannot be rejected")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get registration
        context['title'] = f"Rejecting account request from {self.registration.name} {self.registration.surname}"
        # Populate form
        return context

    def form_valid(self, form):
        # Send confirmation email to user, if needed
        if form.cleaned_data.get('send_email'):
            current_site = get_current_site(self.request)
            email_context = {
                "protocol": "https" if self.request.is_secure() else "http",
                "domain": current_site.domain,
                "request": self.registration,
                "custom_message": form.cleaned_data.get('custom_message'),
            }
            msg = EmailMessage(
                to=[self.registration.email, ],
                from_email=settings.DEFAULT_FROM_EMAIL,
                subject=template_loader.render_to_string("AccountManagement/account_management_subject.txt", {'subject': "Your registation has been rejected"}),
                body=template_loader.render_to_string('AccountManagement/registrationrequest_rejected.html', email_context),
            )
            msg.send()

        if form.cleaned_data.get('purge_request'):
            # Update registration entry
            self.registration.delete()
        else:
            # Update registration entry
            self.registration.status = RegistrationRequest.REJECTED
            self.registration.save()

        return super().form_valid(form)


class AccountRegistrationDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = RegistrationRequest
    template_name = 'AccountManagement/registrationrequest_delete.html'
    permission_required = 'AccountManagement.registration_manage'

    def get_success_url(self):
        return reverse_lazy('account_registration_manage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete registration request"
        context['back_url'] = self.get_success_url()
        return context


# =======================
# Profile management

class AccountProfileView(LoginRequiredMixin, TemplateViewMenu):
    """ View user profile from LDAP
    Fields that are displayed and access from users:
    uid: R
    givenName: R
    sn: R
    mail: RW (with confirmation!)
    mobile: RW
    roomNumber: RW
    sshPublicKey: RW
    jpegPhoto: RWg
    title: R (assigned by the administrator) ??
    """
    template_name = "AccountManagement/userprofile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ldap = UdyniLdap()
        if 'pk' in self.kwargs:
            user = get_object_or_404(auth.get_user_model(), pk=self.kwargs['pk'])
            profile = ldap.getUserProfile(user.get_username())
            if user == self.request.user:
                context['own_profile'] = True
            else:
                context['own_profile'] = False
                context['title'] = f"{user.first_name} {user.last_name}"
        else:
            profile = ldap.getUserProfile(self.request.user.get_username())
            context['own_profile'] = True

        if 'title' not in context:
            context['title'] = "My profile"

        attrs = {
            'uid': ('Username', False),
            'uidNumber': ('UID number', False),
            'givenName': ('Name', False),
            'sn': ('Surname', False),
            #'title': ('Role', False),
            'mail': ('E-mail', True),
            'mobile': ('Mobile number', True),
            'roomNumber': ('Office room number', True),
            'sshPublicKey': ('SSH public key', True),
        }

        # Build profile content
        context['profile'] = []
        for k, (label, editable) in attrs.items():
            if k in profile:
                value = profile[k][0].decode()
                if k == 'sshPublicKey':
                    value = value[0:20] + " ...... " + value[-20:]
                context['profile'].append((k, label, value, editable))

        # Profile photo
        if 'jpegPhoto' in profile:
            context['profile_photo'] = base64.b64encode(profile['jpegPhoto'][0]).decode()

        return context


class AccountProfilePhoto(LoginRequiredMixin, View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        ldap = UdyniLdap()
        user = get_object_or_404(auth.get_user_model(), pk=self.kwargs['pk'])
        profile = ldap.getUserProfile(user.get_username())
        if profile is None or 'jpegPhoto' not in profile or not len(profile['jpegPhoto']):
            raise Http404()
        return HttpResponse(profile['jpegPhoto'][0], content_type="image/jpeg")


class AccountProfileMod(LoginRequiredMixin, FormViewMenu):
    template_name = 'UdyniManagement/generic_form.html'
    form_class = EditProfileForm

    def get_initial(self):
        initial = {}
        try:
            ldap = UdyniLdap()
            profile = ldap.getUserProfile(self.request.user.username)
            for attr in ['mail', 'mobile', 'rootNumber', 'sshPublicKey']:
                try:
                    initial[attr] = profile[attr][0].decode()
                except:
                    pass

        except Exception as e:
            raise Http404(e)

        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['username'] = self.request.user.username
        return kwargs

    def get_success_url(self):
        return reverse_lazy('account_profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify profile"
        context['back_url'] = self.get_success_url()
        context['enctype'] = "multipart/form-data"
        return context

    def form_valid(self, form):
        # Get LDAP connection from form or create a new one
        if form.ldap is not None:
            ldap = form.ldap
        else:
            ldap = UdyniLdap(self.request.user.username, form.cleaned_data['user_password'])

        # Create field modification list
        attributes = {}
        for attr in ['mail', 'mobile', 'roomNumber', 'sshPublicKey']:
            if attr in form.cleaned_data:
                attributes[attr] = form.cleaned_data[attr]
        if 'jpegPhoto' in self.request.FILES:
            # Check image size and format
            image = Image.open(self.request.FILES['jpegPhoto'])
            f = 300.0 / max(image.size)
            if f < 1.0:
                new_sz = [int(s * f) for s in image.size]
                new_image = image.resize(new_sz, resample=Image.BICUBIC)
            else:
                new_image = image
            out = BytesIO()
            new_image.save(out, format='jpeg')
            out.seek(0)
            attributes['jpegPhoto'] = out.read()

        ldap.updateUser(self.request.user.username, attributes)

        return super().form_valid(form)


# =======================
# Manage users

class UserList(LoginRequiredMixin, ListViewMenu):
    template_name = 'AccountManagement/user_list.html'

    def dispatch(self, request, *args, **kwargs):
        self.model = auth.get_user_model()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(is_active=True).order_by('last_name', 'first_name')

    def add_user_photo(self, user_list):
        ldap = UdyniLdap()
        for u in user_list:
            try:
                u.profile_picture = base64.b64encode(ldap.getUserAttribute(u.username, 'jpegPhoto')[0]).decode()
            except Exception:
                pass
        return user_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Users"
        context['users'] = self.add_user_photo(context['object_list'])
        return context


class UserListManage(PermissionRequiredMixin, ListViewMenu):
    permission_required = 'auth.change_users'
    template_name = 'AccountManagement/user_list_manage.html'

    def dispatch(self, request, *args, **kwargs):
        self.model = auth.get_user_model()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Manage users"
        return context


class UserAdd(PermissionRequiredMixin, CreateViewMenu):
    permission_required = 'auth.create_users'

    def dispatch(self, request, *args, **kwargs):
        self.model = auth.get_user_model()
        return super().dispatch(request, *args, **kwargs)


class UserUpdate(PermissionRequiredMixin, UpdateViewMenu):
    permission_required = 'auth.change_users'
    fields = ['is_active', 'is_staff', 'is_superuser']
    template_name = "UdyniManagement/generic_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.model = auth.get_user_model()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('account_users')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Editing user '{context['object'].username}' ({context['object'].first_name} {context['object'].last_name})"
        context['back_url'] = self.get_success_url()
        return context


class UserDelete(PermissionRequiredMixin, DeleteViewMenu):
    permission_required = 'auth.delete_users'
    template_name = "AccountManagement/user_confirm_delete.html"
    form_class = UserDeleteForm

    def dispatch(self, request, *args, **kwargs):
        self.model = auth.get_user_model()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('account_users')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete user"
        context['back_url'] = self.get_success_url()
        context['form'].fields['admin'].initial = self.request.user.username
        return context

    def form_valid(self, form):
        success_url = self.get_success_url()
        if form.cleaned_data.get('delete_ldap'):
            # Delete user also from LDAP
            ldap = UdyniLdap(form.cleaned_data['admin'], form.cleaned_data['admin_psw'])
            ldap.deleteUser(self.object.username)
        # Delete object in Django
        self.object.delete()
        return HttpResponseRedirect(success_url)


# =======================
# Manage permissions

class PermissionListView(PermissionRequiredMixin, ListViewMenu):
    permission_required = 'auth.view_permission'
    model = Permission
    template_name = "AccountManagement/permissions.html"

    def build_permission_map(self, permissions):
        # Get list of active users
        users =  auth.get_user_model().objects.filter(is_active=True).order_by('username')

        # Build the map
        pmap = OrderedDict()
        for perm in permissions:
            perm_label = f"{perm.content_type.app_label}.{perm.codename}"
            pmap[perm.codename] = OrderedDict()
            pmap[perm.codename]['pk'] = perm.pk
            pmap[perm.codename]['app'] = perm.content_type.app_label
            pmap[perm.codename]['desc'] = perm.name
            pmap[perm.codename]['users'] = []
            for u in users:
                pmap[perm.codename]['users'].append(u.has_perm(perm_label))

        return (users, pmap)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "User permissions"
        context['users'], context['permission_map'] = self.build_permission_map(context['object_list'])
        return context


class PermissionAdd(PermissionRequiredMixin, CreateViewMenu):
    model = Permission
    permission_required = 'auth.add_permission'
    template_name = "UdyniManagement/generic_form.html"
    fields = ['codename', 'name', 'content_type']

    def get_success_url(self):
        return reverse_lazy('account_permissions')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add permission"
        context['back_url'] = self.get_success_url()
        return context


class PermissionUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = Permission
    permission_required = 'auth.change_permission'
    template_name = "UdyniManagement/generic_form.html"
    fields = ['name', ]

    def get_success_url(self):
        return reverse_lazy('account_permissions')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Modify permission '{context['permission'].content_type.app_label}.{context['permission'].codename}'"
        context['back_url'] = self.get_success_url()
        return context


class PermissionDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = Permission
    permission_required = 'auth.delete_permission'
    template_name = "UdyniManagement/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('account_permissions')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete permission"
        context['message'] = "Are you sure you want to delete permission: {0!s}?".format(context['object'])
        context['back_url'] = self.get_success_url()
        return context


class PermissionChange(PermissionRequiredMixin, View):
    permission_required = 'auth.change_permission'
    http_method_names = ['post', ]

    def post(self, request, *args, **kwargs):
        # Get user
        user = get_object_or_404(auth.get_user_model(), pk=request.POST.get('user'))

        # Get permission
        m = re.match("^(.*)\.(.*)$", request.POST.get('label'))
        if m is None:
            raise Http404('Invalid permission')
        app_label = m.groups()[0]
        codename = m.groups()[1]
        permissions = Permission.objects.filter(codename=codename)
        for p in permissions:
            if p.content_type.app_label == app_label:
                permission = p
                break
        else:
            raise Http404('Invalid permission')

        # Get status
        try:
            status = int(request.POST.get('status'))
        except Exception:
            raise Http404('Invalid status')

        if status:
            # User has permission. Remove
            user.user_permissions.remove(permission)
            return JsonResponse(data={'status': 0})

        else:
            # User does not have permission. Add
            user.user_permissions.add(permission)
            return JsonResponse(data={'status': 1})
