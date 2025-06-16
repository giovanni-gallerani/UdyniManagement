from LabLogbook import views
from LabLogbook import views_api
from UdyniManagement.views import EmptyView

from django.urls import path, reverse_lazy
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path('', EmptyView.as_view(), name='lablogbook_index'),
    
    # Samples
    path('samples/', views.SampleList.as_view(), name='sample_view'),
    path('samples/add', views.SampleCreate.as_view(), name='sample_add'),
    path('samples/<int:pk>/modify', views.SampleUpdate.as_view(), name='sample_mod'),
    path('samples/<int:pk>/delete', views.SampleDelete.as_view(), name='sample_del'),

    # Experimental Stations
    path('labs_and_experimentalstations/', views.LabAndExperimentalStationList.as_view(), name='lab_and_experimentalstation_view'),
    path('laboratories/add', views.LaboratoryCreate.as_view(), name='laboratory_add'),
    path('laboratories/<int:pk>/modify', views.LaboratoryUpdate.as_view(), name='laboratory_mod'),
    path('laboratories/<int:pk>/delete', views.LaboratoryDelete.as_view(), name='laboratory_del'),
    path('laboratories/<int:laboratory_id>/experimentalstations/add', views.ExperimentalStationCreate.as_view(), name='experimentalstation_add'),
    path('experimentalstations/<int:pk>/modify', views.ExperimentalStationUpdate.as_view(), name='experimentalstation_mod'),
    path('experimentalstations/<int:pk>/delete', views.ExperimentalStationDelete.as_view(), name='experimentalstation_del'),

    # Experiments for experimental station
    path('experimentalstations/<int:station_id>/experiments/', views.ExperimentList.as_view(), name='experiment_view'),
    path('experimentalstations/<int:station_id>/experiments/add', views.ExperimentCreate.as_view(), name='experiment_add'),
    path('experimentalstations/<int:station_id>/experiments/<int:pk>/modify', views.ExperimentUpdate.as_view(), name='experiment_mod'),
    path('experimentalstations/<int:station_id>/experiments/<int:pk>/delete', views.ExperimentDelete.as_view(), name='experiment_del'),
    path('experimentalstations/<int:station_id>/experiments/<int:experiment_id>/add_sample', views.SampleForExperimentAdd.as_view(), name='experiment_sample_add'),
    # note that here pk is the key of the SampleForExperiment object, not of the sample object
    path('experimentalstations/<int:station_id>/experiments/<int:experiment_id>/remove_sample/<int:pk>', views.SampleForExperimentRemove.as_view(), name='experiment_sample_del'),
    
    # Logbook for experiment
    path('experimentalstations/<int:station_id>/experiments/<int:experiment_id>/logbook', views.LogbookList.as_view(), name='logbook_view'),
    path('experimentalstations/<int:station_id>/experiments/<int:experiment_id>/logbook/add', views.CommentCreate.as_view(), name='comment_add'),
    path('experimentalstations/<int:station_id>/experiments/<int:experiment_id>/logbook/<int:pk>/modify', views.CommentUpdate.as_view(), name='comment_mod'),
    path('experimentalstations/<int:station_id>/experiments/<int:experiment_id>/logbook/<int:pk>/reply', views.CommentReply.as_view(), name='comment_reply'),
    path('experimentalstations/<int:station_id>/experiments/<int:experiment_id>/logbook/<int:pk>/delete', views.CommentDelete.as_view(), name='comment_del'),
    path('experimentalstations/<int:station_id>/experiments/<int:experiment_id>/logbook/<int:pk>/history', views.CommentContentHistory.as_view(), name='comment_content_history'),

    # APIs
    path('rest/experimentalstations', views_api.ExperimentalStationListAPI.as_view(), name='api_get_experimentalstation_list'),
    path('rest/experimentalstations/<int:station_id>/experiments', views_api.ExperimentForStationListAPI.as_view(), name='api_get_experiment_for_station_list'),
    path('rest/experiments/<int:experiment_id>/samples', views_api.SampleForExperimentListAPI.as_view(), name='api_get_sample_for_experiment_list'),

    # This API given a json file creates an instance of Measurement, for each file in the measurement creates an instance of File, then create a Comment with CommentContent
    path('rest/experiments/<int:experiment_id>/add_measurement', csrf_exempt(views_api.MeasurementCreateAPI.as_view()), name='api_post_measurement'),
]

menu = {
    'name': "Lab Logbook",
    'link': reverse_lazy('lablogbook_index'),
    'icon': 'fa-solid fa-book',
    'subsections': [
        {
            'name': 'Labs & Exp Stations',
            'link': reverse_lazy('lab_and_experimentalstation_view'),
            'permissions': ['Laboratory.laboratory_view', 'ExperimentalStation.experimentalstation_view'],
        },
        {
            'name': 'Samples',
            'link': reverse_lazy('sample_view'),
            'permissions': ['Sample.sample_view',],
        },
    ],
    'permissions': [],
}