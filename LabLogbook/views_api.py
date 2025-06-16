from LabLogbook.models import ExperimentalStation
from LabLogbook.models import Experiment
from LabLogbook.models import SampleForExperiment
from LabLogbook.models import Measurement, Sample, File, Comment, CommentContent

import json
from django.views import View
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime


class ExperimentalStationListAPI(View):
    '''get a json response containing all the experimental stations'''

    http_method_names = ['get']
    
    def get(self, request, *args, **kwargs):
        try:
            stations = ExperimentalStation.objects.all().order_by('station_id')
            data = [
                {
                    'station_id': s.station_id,
                    'name': s.name,
                    'description': s.description,
                    'responsible':s.responsible.email,
                    'status': s.status,
                    'laboratory': s.laboratory.name,
                }
                for s in stations
            ]
            return JsonResponse({'experimental_stations': data})
        except Exception as e:
            return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


class ExperimentForStationListAPI(View):
    '''get a json response containing all the experiments for a given experimental station'''

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):

        station_id = kwargs['station_id']
        try:
            station = ExperimentalStation.objects.get(station_id=station_id)
        except ExperimentalStation.DoesNotExist:
            return JsonResponse({'error': 'ExperimentalStation not found.'}, status=404)

        try:
            experiments = Experiment.objects.filter(experimental_station=station_id).order_by('experiment_id')
            data = [
                {
                    'experiment_id': e.experiment_id,
                    'creation_time': e.creation_time,
                    'project': e.project.name if e.project is not None else None,
                    'reference': e.reference,
                    'description': e.description,
                    'responsible': e.responsible.email,
                    'status': e.status,
                }
                for e in experiments
            ]
            return JsonResponse({'experiments': data})
        except Exception as e:
            return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)
    

class SampleForExperimentListAPI(View):
    '''get a json response containing all the sample used in a given experiment'''

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):

        experiment_id = kwargs['experiment_id']
        try:
            experiment = Experiment.objects.get(experiment_id=experiment_id)
        except Experiment.DoesNotExist:
            return JsonResponse({'error': 'Experiment not found.'}, status=404)

        try:
            # since sample is ordered by name, order_by('sample') put the samples in alphabetical order
            samples = SampleForExperiment.objects.filter(experiment=experiment_id).order_by('sample')
            data = [
                {
                    'sample_id': s.sample.sample_id,
                    'sample_name': s.sample.name,
                    'material': s.sample.material,
                    'substrate': s.sample.substrate,
                    'manufacturer': s.sample.manufacturer,
                    'description': s.sample.description,
                    'reference': s.sample.reference,
                    'author': s.sample.author.email,
                }
                for s in samples
            ]
            return JsonResponse({'sample_for_experiment': data})
        except Exception as e:
            return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


class MeasurementCreateAPI(View):
    '''
    given a json file creates an instance of Measurement for a given experiment,
    for each file in measurement creates an instance of File,
    then create a Comment with its associated CommentContent containing the informations regarding the measurement.
    '''

    http_method_names = ['post']

    @staticmethod
    def generate_text_from_measurement(measurement: Measurement):
        text = f'Measurement ID: {measurement.measurement_id} for Experiment ID: {measurement.experiment.experiment_id}.\n'
        text += f'Start time: {measurement.start_time}\n'
        text += f'End time: {measurement.end_time}\n'
        text += f'Sample ID: {measurement.sample.sample_id}\n'
        text += f'Sample name (at the time of the measurement): {measurement.sample.name}\n'
        text += f'Generated files:\n'
        files = File.objects.filter(measurement=measurement)
        for file in files:
            text += f'   - File ID: {file.file_id}, Path: {file.path}\n'
        return text


    def post(self, request, *args, **kwargs):

        experiment_id = kwargs['experiment_id']
        try:
            experiment = Experiment.objects.get(experiment_id=experiment_id)
        except Experiment.DoesNotExist:
            return JsonResponse({'error': 'Experiment not found.'}, status=404)

        try:
            data = json.loads(request.body)

            # Extract and validate required fields
            measurement_data = data.get('measurement')
            if not measurement_data:
                return JsonResponse({'error': 'Missing "measurement" key in JSON.'}, status=400)

            start_time_str = measurement_data.get('start_time')
            if not start_time_str:
                return JsonResponse({'error': 'Missing "start_time" in "measurement".'}, status=400)
            
            end_time_str = measurement_data.get('end_time')
            if not end_time_str:
                return JsonResponse({'error': 'Missing "end_time" in "measurement".'}, status=400)
            
            sample_id = measurement_data.get('sample_id')
            if not sample_id:
                return JsonResponse({'error': 'Missing "sample_id" in "measurement".'}, status=400)
            
            file_paths = measurement_data.get('file_paths')
            if not file_paths:
                return JsonResponse({'error': 'Missing "file_paths" in "measurement".'}, status=400)


            # Check if start_time and end_time are actually datetime values
            start_time = parse_datetime(start_time_str)
            if start_time is None:
                return JsonResponse({'error': 'Invalid date format for "start_time" in "measurement".'}, status=400)
            
            end_time = parse_datetime(end_time_str)
            if end_time is None:
                return JsonResponse({'error': 'Invalid date format for "end_time" in "measurement".'}, status=400)
            
            
            # Check if sample is actually one of the samples associated with the specified experiment
            try:
                sample_for_exp = SampleForExperiment.objects.get(sample=sample_id, experiment=experiment_id)
            except SampleForExperiment.DoesNotExist:
                return JsonResponse({'error': '"sample_id" in "measurement" is not related to one of the samples associated to the specified experiment.'}, status=404)
            

            # Check if the file in file_paths are not already present in the File table (if they are it means that they have been saved under a different measurement)
            already_saved_files = list(File.objects.all().values_list('path', flat=True))
            error_files = []
            for path in file_paths:
                if path in already_saved_files:
                    error_files.append(path)
            if error_files:
                return JsonResponse({'error': f'The files {error_files} in "file_paths" are already present in the database.'}, status=404)
            
            

            # Create Measurement
            measurement = Measurement.objects.create(
                experiment=experiment,
                start_time=start_time,
                end_time=end_time,
                sample=sample_for_exp.sample
            )

            # Create associated Files
            generated_files_ids = [] # save the generated files ids for json response
            for path in file_paths:
                file = File.objects.create(
                    measurement=measurement,
                    path=path
                )
                generated_files_ids.append(file.file_id)

            # Auto-generate a Comment about the measurement
            comment = Comment.objects.create(
                experiment=experiment,
                measurement=measurement,
                type='ACQUISITION',
            )
            Comment.objects.rebuild()

            # Auto-generate CommentContent for comment about the measurement
            comment_content = CommentContent.objects.create(
                comment=comment,
                version=1,
                author = None,
                text=self.generate_text_from_measurement(measurement)
            )

            return JsonResponse({
                'status': 'success',
                'measurement_id': measurement.measurement_id,
                'file_ids': generated_files_ids,
                'comment_id': comment.comment_id,
                'comment_content_id': comment_content.comment_content_id
            })
        except Exception as e:
            return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)