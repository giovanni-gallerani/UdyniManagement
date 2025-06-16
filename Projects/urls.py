from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView

from Projects import views

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('project_view'), permanent=False), name='projects_index'),

    path('researchers/', views.ResearcherList.as_view(), name='researcher_view'),
    path('researchers/add', views.ResearcherCreate.as_view(), name='researcher_add'),
    path('researchers/<int:pk>/modify', views.ResearcherUpdate.as_view(), name='researcher_mod'),
    path('researchers/<int:pk>/delete', views.ResearcherDelete.as_view(), name='researcher_del'),
    path('researchers/<int:researcher>/role', RedirectView.as_view(url=reverse_lazy('researcher_view'), permanent=False), name='researcher_role_view'),
    path('researchers/<int:researcher>/role/add', views.ResearcherRoleCreate.as_view(), name='researcher_role_add'),
    path('researchers/<int:researcher>/role/<int:pk>/modify', views.ResearcherRoleUpdate.as_view(), name='researcher_role_mod'),
    path('researchers/<int:researcher>/role/<int:pk>/delete', views.ResearcherRoleDelete.as_view(), name='researcher_role_del'),

    path('registry/', views.ProjectList.as_view(), name='project_view'),
    path('registry/add', views.ProjectCreate.as_view(), name='project_add'),
    path('registry/<int:pk>/modify', views.ProjectUpdate.as_view(), name='project_mod'),
    path('registry/<int:pk>/delete', views.ProjectDelete.as_view(), name='project_del'),
    path('registry/<int:pk>/gae', views.ProjectGaeRedirect.as_view(), name='project_gae'),

    path('workpackages/', RedirectView.as_view(url=reverse_lazy('project_view'), permanent=False), name='wp_view'),
    path('workpackages/add', RedirectView.as_view(url=reverse_lazy('project_view'), permanent=False), name='wp_add'),
    path('workpackages/add/<int:project>', views.WorkPackageCreate.as_view(), name='wp_add_prj'),
    path('workpackages/<int:pk>/modify', views.WorkPackageUpdate.as_view(), name='wp_mod'),
    path('workpackages/<int:pk>/delete', views.WorkPackageDelete.as_view(), name='wp_del'),

    path('conflicts/', views.ConflictList.as_view(), name='conflicts_view'),
    path('conflicts/add', views.ConflictCreate.as_view(), name='conflicts_add'),
    path('conflicts/<int:pk>/modify', views.ConflictUpdate.as_view(), name='conflicts_mod'),
    path('conflicts/<int:pk>/delete', views.ConflictDelete.as_view(), name='conflicts_del'),
]

menu = {
    'name': "Projects registry",
    'link': reverse_lazy('project_view'),
    'icon': 'fa-solid fa-diagram-project',
    'subsections': [
        {
            'name': 'Researchers',
            'link': reverse_lazy('researcher_view'),
            'permissions': ['Projects.researcher_view', ],
        },
        {
            'name': 'Projects',
            'link': reverse_lazy('project_view'),
            'permissions': ['Projects.project_view', ],
        },
        {
            'name': 'Conflicts of Interest',
            'link': reverse_lazy('conflicts_view'),
            'permissions': ['Projects.conflicts_manage', ],
        },
    ],
    'permissions': ['Projects.project_view', 'Projects.researcher_view'],
}
