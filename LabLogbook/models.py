from Projects.models import Project

from django.db import models
from mptt.models import MPTTModel, TreeForeignKey  # used for Comments
from django.contrib.auth import get_user_model


UserModel = get_user_model()


class Sample(models.Model):
    sample_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    substrate = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255)
    description = models.TextField()
    reference = models.CharField(max_length=255)
    author = models.ForeignKey(UserModel, on_delete=models.PROTECT)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['name'], name="%(app_label)s_%(class)s_unique"),
        ]
        default_permissions = ()
        permissions = [
            ('sample_view', 'View list of samples'),
            ('sample_manage', 'Manage list of samples'),
        ]
    
    def __str__(self):
        return f'{self.name}'


class Laboratory(models.Model):
    laboratory_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=['name'], name="%(app_label)s_%(class)s_unique"),
        ]
        default_permissions = ()
        permissions = [
            ('laboratory_view', 'View list of laboratories'),
            ('laboratory_manage', 'Manage list of laboratories'),
        ]

    def __str__(self):
        return f"{self.name}: {self.location}"


class ExperimentalStation(models.Model):
    POSSIBLE_STATUSES = [
        ("AVAILABLE", "Available"),
        ("TEMP_UNAVAILABLE", "Temporary Unavailable"),
        ("DISMISSED", "Dismissed"),
    ]

    station_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    laboratory = models.ForeignKey(Laboratory, on_delete=models.PROTECT)
    description = models.TextField()
    responsible = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    status = models.CharField(max_length=17, choices=POSSIBLE_STATUSES)

    class Meta:
        ordering = ['laboratory', 'name']
        constraints = [
            models.UniqueConstraint(fields=['name'], name="%(app_label)s_%(class)s_unique"),
        ]
        default_permissions = ()
        permissions = [
            ('experimentalstation_view', 'View list of experimental stations'),
            ('experimentalstation_manage', 'Manage list of experimental stations'),
        ]

    def __str__(self):
        return f"{self.name}, status: {self.status}"


class Experiment(models.Model):
    POSSIBLE_STATUSES = [
        ("NEW", "New"),
        ("SCHEDULED", "Scheduled"),
        ("RUNNING", "Running"),
        ("CLOSED", "Closed"),
        ("CANCELLED", "Cancelled"),
    ]

    experiment_id = models.AutoField(primary_key=True)
    creation_time = models.DateTimeField(auto_now_add=True)
    experimental_station = models.ForeignKey(ExperimentalStation, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True)
    reference = models.CharField(max_length=255)
    description = models.TextField()
    def get_samples_for_exp(self):
        return SampleForExperiment.objects.filter(experiment=self.experiment_id)
    samples = property(get_samples_for_exp)
    responsible = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=POSSIBLE_STATUSES)

    class Meta:
        ordering = ['experiment_id']
        default_permissions = ()
        permissions = [
            ('experiment_view', 'View list of experiments'),
            ('experiment_manage', 'Manage list of experiments'),
        ]

    def __str__(self):
        return f"{self.experiment_id}, creation time: {self.creation_time.isoformat()}"


class SampleForExperiment(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    sample = models.ForeignKey(Sample, on_delete=models.PROTECT)
    class Meta:
        ordering = ['sample']
        constraints = [
            models.UniqueConstraint(fields=["experiment", "sample"], name="%(app_label)s_%(class)s_unique")
        ]
        default_permissions = ()
    
    def __str__(self):
        return f"Relation between sample {self.sample.name} and experiment {self.experiment.experiment_id}"


class Measurement(models.Model):
    measurement_id = models.AutoField(primary_key=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.PROTECT)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    sample = models.ForeignKey(Sample, on_delete=models.PROTECT)

    class Meta:
        default_permissions = ()
    
    def __str__(self):
        return f"{self.measurement_id}, start time: {self.start_time.isoformat()}, end time: {self.end_time.isoformat()}"


class File(models.Model):
    file_id = models.AutoField(primary_key=True)
    measurement = models.ForeignKey(Measurement, on_delete=models.PROTECT)
    path = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['path'], name="%(app_label)s_%(class)s_unique"),
        ]
        default_permissions = ()
    
    def __str__(self):
        return f"File at: {self.path}"


class Comment(MPTTModel):
    COMMENT_TYPES = [
        ("ACQUISITION", "Acquisition"),
        ("ANALYSIS", "Analysis"),
    ]

    comment_id = models.AutoField(primary_key=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    measurement = models.ForeignKey(Measurement, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=12, choices=COMMENT_TYPES)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class MPTTMeta:
        order_insertion_by = ['comment_id']

    class Meta:
        default_permissions = ()
        # TODO permissions will be added in the future

    @property
    def latest_content(self):
        return self.commentcontent_set.order_by('-version').first()
    
    @property
    def content_history(self):
        return self.commentcontent_set.order_by('-version')
    
    @property
    def latest_text_before_deletion(self):
        latest_text_before_deletion = None
        for content in self.commentcontent_set.order_by('version'):
            if content.text is not None:
                latest_text_before_deletion = content.text
        return latest_text_before_deletion
    
    def __str__(self):
        return f"Comment {self.comment_id} for experiment: {self.experiment}, reply to: {self.parent}"


class CommentContent(models.Model):
    comment_content_id = models.AutoField(primary_key=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    version = models.IntegerField()
    author = models.ForeignKey(UserModel, on_delete=models.PROTECT, null=True, blank=True) # if the author is null it means that the comment has been generated by a machine
    timestamp = models.DateTimeField(auto_now_add=True)
    text = models.TextField(null=True, blank=False)  # a comment with content null is considered deleted and does not appear in logbook

    class Meta:
        # ordering by comment because that way they stay ordered and different versions can be accessed contiguously
        # reverse ordered by version so that the first comment found is the latest
        ordering = ['comment', '-version']
        default_permissions = ()
        # TODO permissions will be added in the future
    
    def __str__(self):
        return f"Content for comment: {self.comment}, version: {self.version}, timestamp: {self.timestamp.isoformat()}"


class Attachment(models.Model): # TODO to be implemented for future versions of the application ################################
    attachment_id = models.AutoField(primary_key=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    author = models.ForeignKey(UserModel, on_delete=models.PROTECT, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(default=False)
    mimetype = models.CharField(max_length=255)
    path = models.CharField(max_length=255)

    class Meta:
        default_permissions = ()
        # TODO permissions will be added in the future, when the functionality will be implemented inside the application

    def __str__(self):
        return f"Attachment for comment: {self.comment}, timestamp: {self.timestamp.isoformat}"