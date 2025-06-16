from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now, timedelta
from django.contrib.auth import get_user_model
from LabLogbook.models import Laboratory, ExperimentalStation, Sample, Experiment, SampleForExperiment
import json

UserModel = get_user_model()

class MeasurementCreateAPITest(TestCase):
    def setUp(self):

        # Create User
        self.user = UserModel.objects.create_user(username='testuser', password='12345')
        # login = self.client.login(username='testuser', password='12345')

        # Create Laboratory
        self.lab = Laboratory.objects.create(
            name='Test Lab',
            description= 'My lab description',
            location='Milan'
        )

        # Create Experimental Station
        self.station = ExperimentalStation.objects.create(
            name='Station A',
            laboratory=self.lab,
            description='Station description',
            responsible=self.user,
            status='AVAILABLE'
        )

        # Create Sample
        self.sample = Sample.objects.create(
            name='Sample X',
            material='X',
            substrate='X substrate',
            manufacturer='My Sample manufacturer',
            description='My sample description',
            reference='NFFA-DI',
            author=self.user
        )

        # Create Experiment
        self.experiment = Experiment.objects.create(
            experimental_station=self.station,
            project=None,
            reference='NFFA-DI',
            description='Experiment description',
            responsible=self.user,
            status='NEW'
        )

        # Associate Sample with Experiment
        self.sample_for_experiment = SampleForExperiment.objects.create(
            sample=self.sample,
            experiment=self.experiment
        )

        # Store client and URL
        self.client = Client()
        self.url = reverse('api_post_measurement', kwargs={'experiment_id': self.experiment.experiment_id})

    def test_create_measurement_success(self):
        start_time = now().isoformat()
        end_time = (now() + timedelta(hours=1)).isoformat()

        payload = {
            "measurement": {
                "start_time": start_time,
                "end_time": end_time,
                "sample_id": self.sample.sample_id,
                "file_paths": [
                    "/data/test_file1.nxs",
                    "/data/test_file2.nxs"
                ]
            }
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("measurement_id", response.json())
        self.assertIn("file_ids", response.json())
        self.assertIn("comment_id", response.json())
        self.assertIn("comment_content_id", response.json())