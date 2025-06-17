"""UdyniManagement URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from UdyniManagement import views
from UdyniManagement.menu import menu_include


urlpatterns = [
    path('', views.EmptyView.as_view(), name="main_page"),
    path('accounts/', include('AccountManagement.urls')),
    path('projects/', include('Projects.urls')),
    path('accounting/', include('Accounting.urls')),
    #path('reporting_old/', include('FinancialReporting.urls')),
    path('reporting/', include('Reporting.urls')),
    path('lablogbook/', include('LabLogbook.urls')),
    path('sigla/', include('sigla.urls')),
    path('admin/', admin.site.urls),
]

menu = [
    {
        'name': 'Platform management',
        'sections': [
            menu_include('AccountManagement.urls'),
        ],
    },
    {
        'name': 'Project Management',
        'sections': [
            menu_include('Projects.urls'),
            menu_include('Accounting.urls'),
            menu_include('Reporting.urls'),
        ],
    },
    {
        'name': 'Experimental Data Management',
        'sections': [
            menu_include('LabLogbook.urls'),
        ],
    },
    {
        'name': 'Services',
        'sections': [
            #{
            #    'name': 'Request VPN certificate',
            #    'link': '/git',
            #    'subsections': [],
            #    'permissions': [],
            #},
            {
                'name': 'Git',
                'link': '/git',
                'icon': 'fa-brands fa-github',
                'subsections': [],
                'permissions': None,
                'target': '_blank',
            },
            {
                'name': 'Wiki',
                'link': '/xwiki',
                'icon': 'fa-brands fa-wikipedia-w',
                'subsections': [],
                'permissions': None,
                'target': '_blank',
            },
            {
                'name': 'Postgres Admin',
                'link': '/pgadmin',
                'icon': 'fa-solid fa-database',
                'subsections': [],
                'permissions': ['is_superuser', ],
                'target': '_blank',
            },
        ],
    },
]


## ERROR HANDLERS
handler403 = 'UdyniManagement.views.udyni_403_view'
handler404 = 'UdyniManagement.views.udyni_404_view'
