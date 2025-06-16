from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView

from AccountManagement import views


urlpatterns = [
    # Login/Logout
    path('login/', views.LoginView.as_view(), name="account_login"),
    path('logout/', views.LogoutView.as_view(), name="account_logout"),

    # Manage personal profile
    path('profile/', views.AccountProfileView.as_view(), name="account_profile"),
    path('profile/modify', views.AccountProfileMod.as_view(), name="account_profile_mod"),
    path('profile/<int:pk>', views.AccountProfileView.as_view(), name="account_profile_id"),
    #path('profile/<int:pk>/photo', views.AccountProfilePhoto.as_view(), name="account_profile"),
    path('profile/changepassword', views.AccountPasswordChange.as_view(), name="account_password_change"),
    path('profile/changepassword/done', views.AccountPasswordChangeDone.as_view(), name="account_password_change_done"),

    # Password reset
    path('reset/', views.PasswordResetView.as_view(), name="account_password_reset"),
    path('reset/done', views.PasswordResetDoneView.as_view(), name="account_password_reset_done"),
    path('reset/confirm/<str:uidb64>/<str:token>', views.PasswordResetConfirmView.as_view(), name="account_password_reset_confirm"),
    path('reset/complete', views.PasswordResetCompleteView.as_view(), name="account_password_reset_complete"),

    # Registration
    path('registration/', views.AccountRegistration.as_view(), name="account_registration"),
    path('registration/complete', views.AccountRegistrationComplete.as_view(), name="account_registration_complete"),
    path('registration/verify/<str:token>', views.AccountRegistrationVerify.as_view(), name="account_registration_verify"),
    path('registration/manage', views.AccountRegistrationList.as_view(), name="account_registration_manage"),
    path('registration/manage/<int:pk>/accept', views.AccountRegistrationAccept.as_view(), name="account_registration_accept"),
    path('registration/manage/<int:pk>/reject', views.AccountRegistrationReject.as_view(), name="account_registration_reject"),
    path('registration/manage/<int:pk>/delete', views.AccountRegistrationDelete.as_view(), name="account_registration_delete"),

    # Manage users
    path('users/', views.UserList.as_view(), name="account_users"),
    path('users/manage', views.UserListManage.as_view(), name="account_users_manage"),
    path('users/add', views.UserAdd.as_view(), name="account_users_add"),
    path('users/<int:pk>/modify', views.UserUpdate.as_view(), name="account_users_mod"),
    path('users/<int:pk>/delete', views.UserDelete.as_view(), name="account_users_del"),

    # Manage permissions
    path('permissions/', views.PermissionListView.as_view(), name="account_permissions"),
    path('permissions/add', views.PermissionAdd.as_view(), name="account_permissions_add"),
    path('permissions/<int:pk>/modify', views.PermissionUpdate.as_view(), name="account_permissions_mod"),
    path('permissions/<int:pk>/delete', views.PermissionDelete.as_view(), name="account_permissions_del"),
    path('permissions/change', views.PermissionChange.as_view(), name="permission_change"),
]


menu = {
    'name': 'User management',
    'link': '',
    'icon': 'fa-solid fa-users',
    'subsections': [
        {
            'name': 'Manage Users',
            'link': reverse_lazy('account_users_manage'),
            'permissions': ['auth.change_user'],
        },
        {
            'name': "Permissions",
            'link': reverse_lazy('account_permissions'),
            'permissions': ['auth.view_permission', ],
        },
        {
            'name': "Manage registrations",
            'link': reverse_lazy('account_registration_manage'),
            'permissions': ['AccountManagement.registration_manage', ],
        },
    ],
    'permissions': ['auth.view_user', ],
}