import re
import pandas as pd

from django import forms
from django.db.models import CharField
from django.db.models import Q, F, Value
from django.db.models.functions import Concat
from django.core.exceptions import ValidationError

from Projects.models import Researcher, WorkPackage
from Reporting.models import EpasCode, PresenceData, ReportedWork, ReportedMission, ReportedWorkWorkpackage
from Reporting.utils import ConvertApostrophe2Accent

from Tags.templatetags import tr_month


class EpasCodeUpdateForm(forms.Form):

    file = forms.FileField()

    def clean_file(self):
        # File should contain only an HTML table with EPAS codes
        file = self.cleaned_data['file']
        try:
            from lxml import etree
            etree.HTML(file.read()).find("body/table/tbody")
            file.seek(0)
        except Exception as e:
            print(e)
            raise ValidationError("File is not a valid table of EPAS codes (Error: {0!s})".format(e))


class PresenceInputForm(forms.Form):
    researcher = forms.ModelChoiceField(queryset=Researcher.objects.all())
    file = forms.FileField()

    def __init__(self, researcher=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if researcher is not None:
            self.fields['researcher'].widget = forms.HiddenInput()
            self.fields['researcher'].initial = researcher

    def clean_file(self):
        file = self.cleaned_data['file']
        try:
            name = f"{self.cleaned_data['researcher'].surname} {self.cleaned_data['researcher'].name}"
            xls = pd.ExcelFile(file)
            good_sheets = 0
            # Check if is an old format file
            if 'Riassunto RF' in xls.sheet_names:
                # TODO: any check for old files?
                pass
            else:
                # Check that the file matches the selected researcher
                for n in xls.sheet_names:
                    m = re.match(r"([a-zA-Z \']+)_([a-z]+)(\d+)", n)
                    if m is not None:
                        if ConvertApostrophe2Accent(m.groups()[0]) == name:
                            good_sheets += 1
                if good_sheets == 0:
                    raise ValidationError("Excel file does not contain data for the selected researcher")

            return self.cleaned_data['file']

        except ValueError:
            raise ValidationError("File is not a valid Excel file")


class ReportedWorkForm(forms.ModelForm):

    class Meta:
        model = ReportedWork
        fields = ['hours', ]

    def __init__(self, researcher, period, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If the instance does not have a PK we are inserting a new item
        if not self.instance.pk:
            # Months that already have work reported
            work = (
                ReportedWork.objects
                .filter(researcher=researcher, period=period)
                .order_by('year', 'month')
                .annotate(year_month=Concat(F('year'), Value("_"), F('month'), output_field=CharField()))
                .values_list('year_month')
            )
            already_reported = [w[0] for w in work]

            # Available months
            year_month = []
            for y in range(period.rp_start.year, period.rp_end.year + 1):
                if y == period.rp_start.year:
                    if y == period.rp_end.year:
                        year_month += [("{0:d}_{1:d}".format(y, m), "{1:s} {0:d}".format(y, tr_month.month_num2en(m))) for m in range(period.rp_start.month, period.rp_end.month + 1)]
                    else:
                        year_month += [("{0:d}_{1:d}".format(y, m), "{1:s} {0:d}".format(y, tr_month.month_num2en(m))) for m in range(period.rp_start.month, 13)]

                elif y == period.rp_end.year:
                    year_month += [("{0:d}_{1:d}".format(y, m), "{1:s} {0:d}".format(y, tr_month.month_num2en(m))) for m in range(1, period.rp_end.month + 1)]
                else:
                    year_month += [("{0:d}_{1:d}".format(y, m), "{1:s} {0:d}".format(y, tr_month.month_num2en(m))) for m in range(1, 13)]

            self.year_month_choices = list(filter(lambda x: x[0] not in already_reported, year_month))
            self.fields['year_month'] = forms.ChoiceField(choices=self.year_month_choices)

            # Add researcher and period to the model instance
            self.instance.researcher = researcher
            self.instance.period = period

        # Get workpackages
        wps = (
            WorkPackage.objects
            .filter(project=self.instance.period.project)
            .order_by('name')
        )
        for wp in wps:
            field_name = "wp_{0:s}".format(wp.name.lower())
            self.fields[field_name] = forms.FloatField(required=False, label="{0:s}: {1:s}".format(wp.name, wp.desc))
            # If instance has PK set initial value as the saved one
            if self.instance.pk:
                try:
                    rp = self.instance.workpackages.get(Q(workpackage=wp))
                    self.fields[field_name].initial = rp.fraction
                except ReportedWorkWorkpackage.DoesNotExist:
                    pass

    def clean(self):
        # Get parent cleaned data
        data = super().clean()

        if 'year_month' in data:
            # We are adding a new item
            try:
                # Store year and month
                year, month = self.cleaned_data.get('year_month').split("_")
                self.instance.year = int(year)
                self.instance.month = int(month)
            except Exception as e:
                raise ValidationError({'year_month': "Invalid month/year selection (Error: {0!s})".format(e)})

        # Check workpackages
        self.reported_workpackages = []
        for k, v in data.items():
            m = re.match('wp_(.*)', k)
            if m is not None:
                if v != "":
                    wp_name = m.groups()[0]
                    try:
                        wp = WorkPackage.objects.get(Q(project=self.instance.period.project) & Q(name__iexact=wp_name))
                        try:
                            new_rp = ReportedWorkWorkpackage.objects.get(report=self.instance, workpackage=wp)
                        except ReportedWorkWorkpackage.DoesNotExist:
                            new_rp = ReportedWorkWorkpackage()
                            new_rp.workpackage = wp
                        new_rp.fraction = float(v)
                        self.reported_workpackages.append(new_rp)
                    except WorkPackage.DoesNotExist:
                        ValidationError({k: 'Could not find the corresponding workpackage'})
                    except (TypeError, ValueError):
                        ValidationError({k: 'Invalid fraction specified for workpackage'})
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            for rwp in self.reported_workpackages:
                rwp.report = instance
                rwp.save()
        return instance


class AddReportedMissionForm(forms.Form):

    def __init__(self, instance, researcher, period, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Store researcher and period
        self.researcher = researcher
        self.period = period

        # Find missions in the period not already reported
        reported_missions = (
            ReportedMission.objects
            .filter(
                Q(day__researcher=researcher) &
                Q(day__day__gte=period.rp_start) &
                Q(day__day__lte=period.rp_end)
            )
            .values_list('day__pk')
        )

        missions = (
            PresenceData.objects
            .filter(
                Q(researcher=researcher) &
                Q(day__gte=period.rp_start) &
                Q(day__lte=period.rp_end) &
                Q(ts_code=EpasCode.MISSION)
            )
            .exclude(
                Q(pk__in=reported_missions)
            )
        )

        # Add workpackage selection
        wps = WorkPackage.objects.filter(project=period.project)
        if wps.count():
            self.fields['workpackage'] = forms.ChoiceField(label="Workpackage", choices=wps)

        # Add missions checkboxes
        for m in missions:
            name = 'mission_{0:d}'.format(m.pk)
            self.fields[name] = forms.BooleanField(label=m.day, required=False)

    def clean_workpackage(self):
        try:
            wp = WorkPackage.objects.get(pk=self.cleaned_data['workpackage'])
            return wp
        except WorkPackage.DoesNotExist:
            ValidationError('Invalid workpackage')

    def clean(self):
        data = self.cleaned_data
        self.missions = []
        for k, v in self.cleaned_data.items():
            m = re.match('^mission_(\d+)$', k)
            if m is not None and v:
                try:
                    pk = int(m.groups()[0])
                    new_m = ReportedMission()
                    new_m.period = self.period
                    new_m.day = PresenceData.objects.get(pk=pk)
                    new_m.workpackage = self.cleaned_data.get('workpackage')
                    self.missions.append(new_m)

                except (PresenceData.DoesNotExist, ValueError):
                    ValidationError({k: "Invalid mission day"})

        return data

    def save(self, commit=True):
        if commit:
            for m in self.missions:
                m.save()
