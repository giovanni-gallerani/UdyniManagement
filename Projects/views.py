from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.db.models import F, Subquery

from Projects.models import Researcher, ResearcherRole, Project, WorkPackage, ConflictOfInterest

from django.contrib.auth.mixins import PermissionRequiredMixin

from Projects.forms import ResearcherRoleForm, ProjectForm

from django.views import View
from UdyniManagement.views import ListViewMenu, CreateViewMenu, UpdateViewMenu, DeleteViewMenu


# =============================================
# RESEARCHERS VIEWS

class ResearcherList(PermissionRequiredMixin, ListViewMenu):
    model = Researcher
    permission_required = 'Projects.researcher_view'

    def get_queryset(self):
        return Researcher.objects.all().annotate(user=F("username__username")).order_by('surname', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Researchers"
        researchers = list(context['researcher_list'].values())
        print(researchers)
        for r in researchers:
            r['roles'] = ResearcherRole.objects.filter(researcher=r['id'])
        context['researcher_list'] = researchers
        context['can_edit'] = self.request.user.has_perm('Projects.researcher_manage')
        context['can_edit_own'] = self.request.user.has_perm('Projects.role_manage_own')
        return context


class ResearcherCreate(PermissionRequiredMixin, CreateViewMenu):
    model = Researcher
    fields = ['name', 'surname', 'username']
    permission_required = 'Projects.researcher_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('researcher_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new researcher"
        context['back_url'] = self.get_success_url()
        return context


class ResearcherUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = Researcher
    fields = ['name', 'surname', 'username']
    permission_required = 'Projects.researcher_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('researcher_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify researcher"
        context['back_url'] = self.get_success_url()
        return context


class ResearcherDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = Researcher
    permission_required = 'Projects.researcher_manage'
    template_name = "UdyniManagement/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('researcher_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete researcher"
        context['message'] = "Are you sure you want to delete the researcher: {0!s}?".format(context['researcher'])
        context['back_url'] = self.get_success_url()
        return context


class ResearcherRoleCreate(PermissionRequiredMixin, CreateViewMenu):
    model = ResearcherRole
    form_class = ResearcherRoleForm
    permission_required = 'Projects.researcher_manage'

    def has_permission(self):
        r = get_object_or_404(Researcher, pk=self.kwargs['researcher'])
        if r.username is not None and r.username.username == self.request.user.username and self.request.user.has_perm('Projects.role_manage_own'):
            return True
        return super().has_permission()

    def get_success_url(self):
        return reverse_lazy('researcher_view')

    def get_initial(self):
        return {'researcher': self.kwargs['researcher']}

    def get_context_data(self, **kwargs):
        r = get_object_or_404(Researcher, pk=self.kwargs['researcher'])
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new role for {0!s}".format(r)
        context['researcher'] = r
        context['back_url'] = self.get_success_url()
        return context


class ResearcherRoleUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = ResearcherRole
    form_class = ResearcherRoleForm
    permission_required = 'Projects.researcher_manage'

    def has_permission(self):
        r = get_object_or_404(Researcher, pk=self.kwargs['researcher'])
        if r.username is not None and r.username.username == self.request.user.username and self.request.user.has_perm('Projects.role_manage_own'):
            return True
        return super().has_permission()

    def get_success_url(self):
        return reverse_lazy('researcher_view')

    def get_context_data(self, **kwargs):
        r = get_object_or_404(Researcher, pk=self.kwargs['researcher'])
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify role for {0!s}".format(r)
        context['researcher'] = r
        context['back_url'] = self.get_success_url()
        return context


class ResearcherRoleDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = ResearcherRole
    permission_required = 'Projects.researcher_manage'
    template_name = "UdyniManagement/confirm_delete.html"

    def has_permission(self):
        r = get_object_or_404(Researcher, pk=self.kwargs['researcher'])
        if r.username is not None and r.username.username == self.request.user.username and self.request.user.has_perm('Projects.role_manage_own'):
            return True
        return super().has_permission()

    def get_success_url(self):
        return reverse_lazy('researcher_view')

    def get_context_data(self, **kwargs):
        r = get_object_or_404(Researcher, pk=self.kwargs['researcher'])
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete role for {0!s}".format(r)
        context['message'] = "Are you sure you want to delete role {0!s} for researcher {1!s}?".format(context['researcherrole'], r)
        context['back_url'] = self.get_success_url()
        return context


# =============================================
# PROJECTS and WORKPACKAGES
#
class ProjectList(PermissionRequiredMixin, ListViewMenu):
    model = Project
    permission_required = 'Projects.project_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Projects & Work Packages"
        context['can_edit'] = self.request.user.has_perm('Projects.project_manage')
        return context


class ProjectCreate(PermissionRequiredMixin, CreateViewMenu):
    model = Project
    form_class = ProjectForm
    permission_required = 'Projects.project_manage'
    template_name = "Projects/project_form.html"

    def get_success_url(self):
        return reverse_lazy('project_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new project"
        context['back_url'] = reverse_lazy('project_view')
        return context


class ProjectUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = Project
    form_class = ProjectForm
    permission_required = 'Projects.project_manage'
    template_name = "Projects/project_form.html"

    def get_success_url(self):
        return reverse_lazy('project_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify project"
        context['back_url'] = self.get_success_url()
        return context


class ProjectDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = Project
    permission_required = 'Projects.project_manage'
    template_name = "UdyniManagement/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('project_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete project"
        context['message'] = "Are you sure you want to delete project {0!s}?".format(context['project'])
        context['back_url'] = self.get_success_url()
        return context


class ProjectGaeRedirect(PermissionRequiredMixin, View):
    permission_required = 'Projects.gae_view'
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        prj = get_object_or_404(Project, pk=self.kwargs['pk'])
        return redirect('sigla_gae', pg_progetto=prj.sigla_id)


# =============================================
# Work packages
#
class WorkPackageCreate(PermissionRequiredMixin, CreateViewMenu):
    model = WorkPackage
    fields = ['name', 'desc']
    permission_required = 'Projects.project_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('project_view')

    def form_valid(self, form):
        project = get_object_or_404(Project, pk=self.kwargs['project'])
        form.instance.project = project
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs['project'])
        context['title'] = "Add new work package to project " + str(project)
        context['back_url'] = self.get_success_url()
        return context


class WorkPackageUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = WorkPackage
    fields = ['name', 'desc']
    permission_required = 'Projects.project_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('project_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify work package of project " + str(context['workpackage'].project)
        context['back_url'] = self.get_success_url()
        return context


class WorkPackageDelete(DeleteViewMenu):
    model = WorkPackage
    permission_required = 'Projects.project_manage'
    template_name = "UdyniManagement/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('project_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete work package of project " + str(context['workpackage'].project)
        context['message'] = "Are you sure you want to delete the workpackage {0!s} in project {1!s}?".format(context['workpackage'].name, context['workpackage'].project)
        context['back_url'] = self.get_success_url()
        return context


# =============================================
# CONFLICTS OF INTEREST
#
class ConflictList(PermissionRequiredMixin, ListViewMenu):
    model = ConflictOfInterest
    permission_required = 'Projects.conflict_manage'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Conflicts of interest"
        return context


class ConflictCreate(PermissionRequiredMixin, CreateViewMenu):
    model = ConflictOfInterest
    fields = ['researcher', 'director', 'delegate', 'start_date']
    permission_required = 'Projects.conflict_manage'
    template_name = "Projects/conflictofinterest_form.html"

    def get_success_url(self):
        return reverse_lazy('conflicts_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add conflict of interest"
        context['back_url'] = reverse_lazy('project_view')
        context['form'].fields['director'].queryset = Researcher.objects.filter(pk__in=Subquery(ResearcherRole.objects.filter(role=ResearcherRole.INSTITUTE_DIRECTOR).values('researcher'))) 
        return context


class ConflictUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = ConflictOfInterest
    fields = ['researcher', 'director', 'delegate', 'start_date']
    permission_required = 'Projects.conflict_manage'
    template_name = "Projects/conflictofinterest_form.html"

    def get_success_url(self):
        return reverse_lazy('conflicts_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify conflict of interest"
        context['back_url'] = self.get_success_url()
        return context


class ConflictDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = ConflictOfInterest
    permission_required = 'Projects.project_manage'
    template_name = "UdyniManagement/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('conflicts_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete conflict of interest"
        context['message'] = f"Are you sure you want to delete conflict of interest between {context['conflictofinterest'].researcher} and {context['conflictofinterest'].director}?"
        context['back_url'] = self.get_success_url()
        return context
