from LabLogbook.models import Laboratory, Sample, ExperimentalStation, Experiment, SampleForExperiment, Measurement, File, Comment, CommentContent
from LabLogbook.forms import CommentForm, CommentContentForm
from UdyniManagement.views import ListViewMenu, CreateViewMenu, UpdateViewMenu, DeleteViewMenu
from UdyniManagement.menu import UdyniMenu

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy


# =============================================
# SAMPLE
#
class SampleList(PermissionRequiredMixin, ListViewMenu):
    model = Sample
    permission_required = 'Sample.sample_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Samples"
        context['can_edit'] = self.request.user.has_perm('Sample.sample_manage')
        return context

class SampleCreate(PermissionRequiredMixin, CreateViewMenu):
    model = Sample
    fields = ['name', 'material', 'substrate', 'manufacturer', 'description', 'reference']
    permission_required = 'Sample.sample_manage'
    template_name = "UdyniManagement/generic_form.html"
    
    def get_success_url(self):
        return reverse_lazy('sample_view')
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new sample"
        context['back_url'] = self.get_success_url()
        return context

class SampleUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = Sample
    fields = ['name', 'material', 'substrate', 'manufacturer', 'description', 'reference']
    permission_required = 'Sample.sample_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('sample_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify sample"
        context['back_url'] = self.get_success_url()
        return context

class SampleDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = Sample
    permission_required = 'Sample.sample_manage'
    template_name = "LabLogbook/sample_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('sample_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sample_id = self.kwargs['pk']
        sample = get_object_or_404(Sample, sample_id=sample_id)
        experiments_that_use_the_sample = SampleForExperiment.objects.filter(sample=sample).values_list('experiment_id', flat=True)
        measurements_that_use_the_sample = Measurement.objects.filter(sample=sample).values_list('measurement_id', flat=True)


        context['title'] = "Delete sample"
        context['sample_used_in_experiments'] = experiments_that_use_the_sample.exists()
        context['experiments_that_use_the_sample'] = list(experiments_that_use_the_sample)
        context['sample_used_in_measurements'] = measurements_that_use_the_sample.exists()
        context['measurements_that_use_the_sample'] = list(measurements_that_use_the_sample)
        context['message'] = f"Are you sure you want to delete the sample: {context['sample']}?"
        context['back_url'] = self.get_success_url()
        return context
    

# =============================================
# LABORATORY & EXPERIMENTAL STATION
#
class LabAndExperimentalStationList(PermissionRequiredMixin, ListViewMenu): # This view is used for the 'Labs & Experimental Stations' page
    model = ExperimentalStation
    permission_required = 'Laboratory.laboratory_view', 'ExperimentalStation.experimentalstation_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Labs & Experimental Stations"
        context['can_edit_lab'] = self.request.user.has_perm('Laboratory.laboratory_manage')
        context['can_edit_station'] = self.request.user.has_perm('ExperimentalStation.experimentalstation_manage')
        context['laboratory_list'] = Laboratory.objects.all()
        return context


# =============================================
# LABORATORY
#
class LaboratoryCreate(PermissionRequiredMixin, CreateViewMenu):
    model = Laboratory
    fields = ['name', 'description', 'location']
    permission_required = 'Laboratory.laboratory_manage'
    template_name = "UdyniManagement/generic_form.html"
    
    def get_success_url(self):
        return reverse_lazy('lab_and_experimentalstation_view')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new laboratory"
        context['back_url'] = self.get_success_url()
        return context

class LaboratoryUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = Laboratory
    fields = ['name', 'description', 'location']
    permission_required = 'Laboratory.laboratory_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('lab_and_experimentalstation_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify laboratory"
        context['back_url'] = self.get_success_url()
        return context

class LaboratoryDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = Laboratory
    permission_required = 'Laboratory.laboratory_manage'
    template_name = "LabLogbook/laboratory_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('lab_and_experimentalstation_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        laboratory_id = self.kwargs['pk']
        laboratory = get_object_or_404(Laboratory, laboratory_id=laboratory_id)
        experimental_stations_in_the_lab = ExperimentalStation.objects.filter(laboratory=laboratory).values_list('name', flat=True)

        context['title'] = f"Delete laboratory"
        context['experimental_stations_in_the_lab'] = list(experimental_stations_in_the_lab)
        context['message'] = f"Are you sure you want to delete the laboratory: {context['laboratory']}?"
        context['back_url'] = self.get_success_url()
        return context


# =============================================
# EXPERIMENTAL STATION
#
class ExperimentalStationCreate(PermissionRequiredMixin, CreateViewMenu):
    model = ExperimentalStation
    fields = ['name', 'description', 'responsible', 'status']  # laboratory is determined when pressing the Add experimental station button inside a lab
    permission_required = 'ExperimentalStation.experimentalstation_manage'
    template_name = "UdyniManagement/generic_form.html"
    
    def form_valid(self, form):
        laboratory_id = self.kwargs['laboratory_id']
        laboratory = get_object_or_404(Laboratory, laboratory_id=laboratory_id)
        form.instance.laboratory = laboratory
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('lab_and_experimentalstation_view')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        laboratory_id = self.kwargs['laboratory_id']
        laboratory = Laboratory.objects.get(laboratory_id=laboratory_id)  # here we must query for the name of the laboratory since it's not in context
        context['title'] = f"Add new experimental station to {laboratory.name}"
        context['back_url'] = self.get_success_url()
        return context

class ExperimentalStationUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = ExperimentalStation
    fields = ['laboratory', 'name', 'description', 'responsible', 'status']  # here laboratory is present in case is necessary to move an exp station to another lab
    permission_required = 'ExperimentalStation.experimentalstation_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('lab_and_experimentalstation_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Modify experimental station"
        context['back_url'] = self.get_success_url()
        return context

class ExperimentalStationDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = ExperimentalStation
    permission_required = 'ExperimentalStation.experimentalstation_manage'
    template_name = "LabLogbook/experimental_station_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('lab_and_experimentalstation_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        station_id = self.kwargs['pk']
        station = get_object_or_404(ExperimentalStation, station_id=station_id)
        experiments_made_with_experimental_station = Experiment.objects.filter(experimental_station=station).values_list('experiment_id', flat=True)

        context['title'] = "Delete experimental station"
        context['experiments_made_with_experimental_station'] = list(experiments_made_with_experimental_station)
        context['message'] = f"Are you sure you want to delete the experimental station '{context['experimentalstation'].name}' in lab '{context['experimentalstation'].laboratory}'?"
        context['back_url'] = self.get_success_url()
        return context


# =============================================
# EXPERIMENT FOR EXPERIMENTAL STATION
#
class ExperimentList(PermissionRequiredMixin, ListViewMenu):
    model = Experiment
    permission_required = 'Experiment.experiment_view'

    def get_queryset(self):
        station_id = self.kwargs['station_id']
        station = get_object_or_404(ExperimentalStation, station_id=station_id)
        return Experiment.objects.filter(experimental_station=station_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station_id = self.kwargs['station_id']
        station = ExperimentalStation.objects.get(station_id=station_id)  # here we must query for the name of the experimental station since it's not in context
        context['title'] = f"Experiments for {station.name}"
        context['this_station_id'] = station_id  # here the experimental station id is saved so that the urls in the html page can reference to it
        context['can_edit'] = self.request.user.has_perm('Experiment.experiment_manage')
        return context


class ExperimentCreate(PermissionRequiredMixin, CreateViewMenu):
    model = Experiment
    fields = ['project', 'reference', 'description', 'status']
    permission_required = 'Experiment.experiment_manage'
    template_name = "UdyniManagement/generic_form.html"
    
    def get_success_url(self):
        station_id = self.kwargs['station_id']
        return reverse_lazy('experiment_view', kwargs={'station_id': station_id})
    
    # experimental_station is not editable, it's the same from the web page the experiment has been created
    def form_valid(self, form):
        station_id = self.kwargs['station_id']
        experimental_station = get_object_or_404(ExperimentalStation, station_id=station_id)
        form.instance.experimental_station = experimental_station
        form.instance.responsible = self.request.user
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station_id = self.kwargs['station_id']
        station = ExperimentalStation.objects.get(station_id=station_id)  # here we must query for the name of the experimental station since it's not in context
        context['title'] = f"Add new experiment for {station.name}"
        context['back_url'] = self.get_success_url()
        return context

class ExperimentUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = Experiment
    fields = ['project', 'reference', 'description', 'responsible','status']
    permission_required = 'Experiment.experiment_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        station_id = self.kwargs['station_id']
        return reverse_lazy('experiment_view', kwargs={'station_id': station_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Modify experiment for {context['experiment'].experimental_station.name}"
        context['back_url'] = self.get_success_url()
        return context

class ExperimentDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = Experiment
    permission_required = 'Experiment.experiment_manage'
    template_name = "LabLogbook/experiment_confirm_delete.html"

    def get_success_url(self):
        station_id = self.kwargs['station_id']
        return reverse_lazy('experiment_view', kwargs={'station_id': station_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        experiment_id = self.kwargs['pk']
        experiment = get_object_or_404(Experiment, experiment_id=experiment_id)
        measurements_for_experiment = Measurement.objects.filter(experiment=experiment).values_list('measurement_id', flat=True)

        context['title'] = "Delete experiment"
        context['measurements_for_experiment'] = list(measurements_for_experiment)
        context['message'] = f"Are you sure you want to delete the experiment {context['experiment']} ?"
        context['back_url'] = self.get_success_url()
        return context


# =============================================
# SAMPLE FOR EXPERIMENT
#
class SampleForExperimentAdd(PermissionRequiredMixin, CreateViewMenu):
    model = SampleForExperiment
    fields = ['sample']
    permission_required = 'Experiment.experiment_manage'
    template_name = "LabLogbook/sample_for_experiment_form.html"
    
    def get_success_url(self):
        station_id = self.kwargs['station_id']
        return reverse_lazy('experiment_view', kwargs={'station_id': station_id})
    
    def get_form(self, *args):
        form = super().get_form(*args)
        experiment_id = self.kwargs['experiment_id']
        experiment = get_object_or_404(Experiment, experiment_id=experiment_id)

        # Get all samples already associated with this experiment
        used_samples = SampleForExperiment.objects.filter(experiment=experiment).values_list('sample_id', flat=True)
        
        # Show only samples NOT already used
        form.fields['sample'].queryset = Sample.objects.exclude(sample_id__in=used_samples)

        return form
    
    def form_valid(self, form):
        experiment_id = self.kwargs['experiment_id']
        experiment = get_object_or_404(Experiment, experiment_id=experiment_id)
        form.instance.experiment = experiment
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        experiment_id = self.kwargs['experiment_id']
        experiment = get_object_or_404(Experiment, experiment_id=experiment_id)  # here we must query for the experiment id since it's not in context

        # Get all samples NOT already used with this experiment
        used_samples = SampleForExperiment.objects.filter(experiment=experiment).values_list('sample_id', flat=True)
        not_used_samples = Sample.objects.exclude(sample_id__in=used_samples)

        context['title'] = f"Add existing sample to experiement {experiment.experiment_id}"
        context['all_samples_used'] = not not_used_samples.exists()
        context['back_url'] = self.get_success_url()
        return context
    
class SampleForExperimentRemove(PermissionRequiredMixin, DeleteViewMenu):
    model = SampleForExperiment
    permission_required = 'Experiment.experiment_manage'
    template_name = "UdyniManagement/confirm_delete.html"

    def get_success_url(self):
        station_id = self.kwargs['station_id']
        return reverse_lazy('experiment_view', kwargs={'station_id': station_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Remove sample from the experiment"
        context['message'] = f"Are you sure you want to remove the sample '{context['sampleforexperiment'].sample.name}' from the experiment '{context['sampleforexperiment'].experiment.experiment_id}'?"
        context['back_url'] = self.get_success_url()
        return context

# =============================================
# EXPERIMENT LOGBOOK
#
def get_comment_tree(experiment):
    return Comment.objects.filter(experiment=experiment).order_by('tree_id', 'lft')


class LogbookList(View):
    http_method_names = ['get']
    template_name = 'LabLogbook/comment_list.html'

    def get(self, request, *args, **kwargs):
        show_deleted = request.GET.get('show_deleted') == 'true' # pressing a button is possible to show deleted comments
        station = get_object_or_404(ExperimentalStation, station_id=kwargs['station_id'])
        experiment = get_object_or_404(Experiment, experiment_id=kwargs['experiment_id'])

        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f"Logbook for experiment {experiment.experiment_id}",
            'back_url' : reverse_lazy('experiment_view', kwargs={'station_id': station.station_id}),
            'back_url_button_title' : f'Experiments for {station.name}',
            'station_id' : station.station_id, # this is used as an argument in various urls in the template
            'experiment_id' : experiment.experiment_id, # this is used as an argument in various urls in the template
            'comment_tree': get_comment_tree(experiment),
            'show_deleted': show_deleted,
        }
        return render(request, self.template_name, context)
    

class CommentContentHistory(View):
    http_method_names = ['get']
    template_name = 'LabLogbook/comment_content_history_list.html'

    def get(self, request, *args, **kwargs):
        station = get_object_or_404(ExperimentalStation, station_id=kwargs['station_id'])
        experiment = get_object_or_404(Experiment, experiment_id=kwargs['experiment_id'])
        comment = get_object_or_404(Comment, comment_id=kwargs['pk'])

        title = f'Content version history, Comment ID: {comment.comment_id}'
        # The comment history of deleted comments can be accessed (provided a link) but the user must know that the comment is no more visible
        if comment.latest_content.text == None:
            title += ' (DELETED)'

        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': title,
            'back_url' : reverse_lazy('logbook_view', kwargs={'station_id': station.station_id, 'experiment_id': experiment.experiment_id}),
            'back_url_button_title' : f'Logbook for experiment {experiment.experiment_id}',
            'comment': comment,
        }
        return render(request, self.template_name, context)


class CommentCreate(View):
    http_method_names = ['get', 'post']
    template_name = 'LabLogbook/comment_form.html'
    
    def get_experiment_and_back_url(self, **kwargs):
        station = get_object_or_404(ExperimentalStation, station_id=kwargs['station_id'])
        experiment = get_object_or_404(Experiment, experiment_id=kwargs['experiment_id'])
        back_url = reverse_lazy('logbook_view', kwargs={'station_id': station.station_id, 'experiment_id': experiment.experiment_id})
        return experiment, back_url

    def get(self, request, *args, **kwargs):
        experiment, back_url = self.get_experiment_and_back_url(**kwargs)

        comment_form = CommentForm()
        comment_content_form = CommentContentForm()

        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f'Create comment for experiment {experiment.experiment_id}',
            'comment_form': comment_form,
            'comment_content_form': comment_content_form,
            'back_url' : back_url,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        experiment, back_url = self.get_experiment_and_back_url(**kwargs)

        comment_form = CommentForm(request.POST)
        comment_content_form = CommentContentForm(request.POST)
        
        if comment_form.is_valid() and comment_content_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.experiment = experiment
            # measurement, and parent are null when creating a new comment, we don't need to edit them
            comment.save()

            # This instruction is present because when a new tree is created the tree_id of already existing comment could change,
            # this would move entire comment trees in the logbook making the user experience inconsistent, so it's better to have this little overhead.
            # Note that this only applies when a new comment is created, so editing comments does not have any overhead.
            Comment.objects.rebuild()

            comment_content = comment_content_form.save(commit=False)
            comment_content.comment = comment
            comment_content.version = 1
            comment_content.author = self.request.user
            comment_content.save()

            return redirect(back_url)

        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f'Create comment for experiment {experiment.experiment_id}',
            'comment_form': comment_form,
            'comment_content_form': comment_content_form,
            'back_url' : back_url,
        }
        return render(request, self.template_name, context)


class CommentUpdate(View):
    '''
    Type and text of comments can be edited.
    The text can be edited starting from the text of the previous version.

    Note that comments with author = None are machine generated and cannot be edited.
    Note that comments with text = None have been deleted and cannot be edited.

    When a comment text is updated a new entry of comment content is created.
    If text is not changed, it won't be created a new entry of comment content if you press save. You can change the type without creating a new version.
    The new comment inherits the unchanged characteristic from the previous version of comment content, but it has its own author and timestamp.
    '''
    
    http_method_names = ['get', 'post']
    template_name = 'LabLogbook/comment_form.html'
    
    def get_back_url(self, **kwargs):
        station = get_object_or_404(ExperimentalStation, station_id=kwargs['station_id'])
        experiment = get_object_or_404(Experiment, experiment_id=kwargs['experiment_id'])
        return reverse_lazy('logbook_view', kwargs={'station_id': station.station_id, 'experiment_id': experiment.experiment_id})
    
    def get_comment(self, **kwargs):
        return get_object_or_404(Comment, comment_id=kwargs['pk'])

    def get(self, request, *args, **kwargs):
        back_url = self.get_back_url(**kwargs)
        comment = self.get_comment(**kwargs)
        latest_content = comment.latest_content

        initial_comment_form = {
            'type': comment.type,  # get the type currently assigned to the comment
        }
        initial_comment_content_form = {
            'text': latest_content.text, # get the text from the previous version of the comment
        }
        comment_form = CommentForm(initial=initial_comment_form)
        comment_content_form = CommentContentForm(initial=initial_comment_content_form)

        # if the comment is machine generated (has author NULL) it cannot be edited
        machine_generated = True if latest_content.author is None else False
        # if the comment has been deleted (has text NULL) it cannot be edited
        deleted = True if latest_content.text is None else False
        
        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f"Edit comment, Comment ID: {comment.comment_id}",
            'machine_generated': machine_generated,
            'deleted': deleted,
            'comment_form': comment_form,
            'comment_content_form': comment_content_form,
            'back_url' : back_url,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        back_url = self.get_back_url(**kwargs)
        comment = self.get_comment(**kwargs)
        latest_content = comment.latest_content

        comment_form = CommentForm(request.POST)
        comment_content_form = CommentContentForm(request.POST)

        # if the comment is machine generated (has author NULL) it cannot be edited
        machine_generated = True if latest_content.author is None else False
        # if the comment has been deleted (has text NULL) it cannot be edited
        deleted = True if latest_content.text is None else False
        
        if comment_form.is_valid() and comment_content_form.is_valid() and not machine_generated and not deleted:
            # The data gets updated update the the comment and its content, otherwise when save is pressed just go back
            comment_type_inserted_in_form = comment_form.cleaned_data['type']
            if comment_type_inserted_in_form != comment.type:
                # if the type has changed get the object comment and update it
                comment.type = comment_type_inserted_in_form # here i use the value stored in the form in order to update the comment
                comment.save()

            if comment_content_form.cleaned_data['text'] != latest_content.text:
                comment_content = comment_content_form.save(commit=False)
                comment_content.comment = comment  # the referred comment does not change
                comment_content.version = latest_content.version + 1  # update version number
                comment_content.author = self.request.user
                comment_content.save()

            return redirect(back_url)

        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f"Edit comment, Comment ID: {comment.comment_id}",
            'machine_generated': machine_generated,
            'deleted': deleted,
            'comment_form': comment_form,
            'comment_content_form': comment_content_form,
            'back_url' : back_url,
        }
        return render(request, self.template_name, context)


class CommentReply(View):
    '''
    When replying to a comment a new comment and comment content gets created.
    Note that comments with author = None are machine generated and cannot be replied to.
    '''
    http_method_names = ['get', 'post']
    template_name = 'LabLogbook/comment_reply_form.html'
    
    def get_back_url(self, **kwargs):
        station = get_object_or_404(ExperimentalStation, station_id=kwargs['station_id'])
        experiment = get_object_or_404(Experiment, experiment_id=kwargs['experiment_id'])
        return reverse_lazy('logbook_view', kwargs={'station_id': station.station_id, 'experiment_id': experiment.experiment_id})
    
    def get_comment(self, **kwargs):
        '''
        Used for obtaining the comment the user want to reply to.
        '''
        return get_object_or_404(Comment, comment_id=kwargs['pk'])

    def get(self, request, *args, **kwargs):
        back_url = self.get_back_url(**kwargs)
        comment_to_reply = self.get_comment(**kwargs)

        comment_form = CommentForm()
        comment_content_form = CommentContentForm()

        deleted = True if comment_to_reply.latest_content.text is None else False

        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f"Reply to comment, Comment ID: {comment_to_reply.comment_id}",
            'deleted': deleted,
            'comment_to_reply' : comment_to_reply,
            'comment_content_to_reply' : comment_to_reply.latest_content,
            'comment_form': comment_form,
            'comment_content_form': comment_content_form,
            'back_url' : back_url,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        back_url = self.get_back_url(**kwargs)
        comment_to_reply = self.get_comment(**kwargs)

        comment_form = CommentForm(request.POST)
        comment_content_form = CommentContentForm(request.POST)

        deleted = True if comment_to_reply.latest_content.text is None else False
        
        if comment_form.is_valid() and comment_content_form.is_valid() and not deleted:
            comment = comment_form.save(commit=False)
            comment.experiment = comment_to_reply.experiment
            comment.measurement = comment_to_reply.measurement  # measurment and experiment are the same of the parent comment
            comment.parent = comment_to_reply  # the parent comment is the one the user has replied to
            comment.save()

            # This instruction is present because when a new tree is created the tree_id of already existing comment could change,
            # this would move entire comment trees in the logbook making the user experience inconsistent, so it's better to have this little overhead.
            # Note that this only applies when a new comment is created, so editing comments does not have any overhead.
            Comment.objects.rebuild()

            comment_content = comment_content_form.save(commit=False)
            comment_content.comment = comment
            comment_content.version = 1
            comment_content.author = self.request.user
            comment_content.save()

            return redirect(back_url)

        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f"Reply to comment, Comment ID: {comment_to_reply.comment_id}",
            'deleted': deleted,
            'comment_to_reply' : comment_to_reply,
            'comment_content_to_reply' : comment_to_reply.latest_content,
            'comment_form': comment_form,
            'comment_content_form': comment_content_form,
            'back_url' : back_url,
        }
        return render(request, self.template_name, context)


class CommentDelete(CreateViewMenu):
    '''
    When a comment is deleted a new comment content with text = NULL get added as the final version of the content.
    Note that comments with author = None are machine generated and cannot be deleted.
    Note that comments with text = None have been deleted and cannot be deleted again.
    '''
    
    http_method_names = ['get', 'post']
    template_name = 'LabLogbook/comment_confirm_delete.html'
    
    def get_station_experiment_back_url(self, **kwargs):
        station = get_object_or_404(ExperimentalStation, station_id=kwargs['station_id'])
        experiment = get_object_or_404(Experiment, experiment_id=kwargs['experiment_id'])
        return station, experiment, reverse_lazy('logbook_view', kwargs={'station_id': station.station_id, 'experiment_id': experiment.experiment_id})
    
    def get_comment(self, **kwargs):
        return get_object_or_404(Comment, comment_id=kwargs['pk'])
    
    def delete_comment(self, comment: Comment):
        '''Function used for creating a new comment content for the comment passed'''
        comment_content = CommentContent()
        comment_content.comment = comment  # the referred comment does not change
        comment_content.version = comment.latest_content.version + 1  # update version number
        comment_content.author = self.request.user
        comment_content.text = None
        comment_content.save()

    def get(self, request, *args, **kwargs):
        station, experiment, back_url = self.get_station_experiment_back_url(**kwargs)
        comment_to_delete = self.get_comment(**kwargs)
        latest_content = comment_to_delete.latest_content

        # if the comment is machine generated (has author NULL) it cannot be deleted
        machine_generated = True if latest_content.author is None else False
        # if the comment has been deleted (has text NULL) it cannot be deleted again
        deleted = True if latest_content.text is None else False
        
        message = f'''Are you sure you want to delete comment with Comment ID: {comment_to_delete.comment_id} and all its replies from the logbook?
            You will be able to continue seeing its content version history at this link: '''
        
        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f"Delete comment, Comment ID: {comment_to_delete.comment_id}",
            
            # used for the message
            'message' : message,
            'station_id' : station.station_id,
            'experiment_id': experiment.experiment_id,
            'pk' : comment_to_delete.comment_id,

            'machine_generated': machine_generated,
            'deleted': deleted,
            'back_url' : back_url,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        station, experiment, back_url = self.get_station_experiment_back_url(**kwargs)
        comment_to_delete = self.get_comment(**kwargs)

        # if the comment is machine generated (has author NULL) it cannot be edited
        machine_generated = True if comment_to_delete.latest_content.author is None else False
        # if the comment has been deleted (has text NULL) it cannot be edited
        deleted = True if comment_to_delete.latest_content.text is None else False
        
        if not machine_generated and not deleted: # proceed deleting the comment
            self.delete_comment(comment_to_delete)
            for child_comment in comment_to_delete.get_descendants(): # delete also the comment descendants (if they are not already been deleted)
                deleted = True if child_comment.latest_content.text is None else False
                if not deleted:
                    self.delete_comment(child_comment)

            return redirect(back_url)

        message = f'''Are you sure you want to delete comment with Comment ID: {comment_to_delete.comment_id} and all its replies from the logbook?
            You will be able to continue seeing its content version history at this link: '''
        
        context = {
            'menu': UdyniMenu().getMenu(request.user),
            'title': f"Delete comment, Comment ID: {comment_to_delete.comment_id}",
            
            # used for the message
            'message' : message,
            'station_id' : station.station_id,
            'experiment_id': experiment.experiment_id,
            'pk' : comment_to_delete.comment_id,
            
            'machine_generated': machine_generated,
            'deleted': deleted,
            'back_url' : back_url,
        }
        return render(request, self.template_name, context)