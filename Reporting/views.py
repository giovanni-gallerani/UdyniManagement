from typing import OrderedDict
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import JsonResponse, Http404, FileResponse
from django.core.exceptions import MultipleObjectsReturned, PermissionDenied, ValidationError

from django.db.models import Count, Sum, Q, F, Value, ExpressionWrapper, BooleanField, CharField

from django.db.models.functions import ExtractYear, ExtractMonth, Concat, Coalesce, Floor, Least

from Projects.models import Project, Researcher, ResearcherRole, WorkPackage, ConflictOfInterest
from Reporting.models import EpasCode, BankHoliday, PersonnelCost, PresenceData, ReportingPeriod, ReportedWork, ReportedWorkWorkpackage, ReportedMission, TimesheetHours

from Reporting.forms import AddReportedMissionForm, EpasCodeUpdateForm, PresenceInputForm, ReportedWorkForm  #, ReportingAddForm

from Reporting.utils import process_presences, summarize_presences, serialize_presences
from Reporting.utils import unserialize_presences, check_presences_unique, check_bank_holiday
from Reporting.utils import get_workpackages_fractions
from Reporting.utils import ReportingError
from Reporting.timesheets import CheckTimesheetData, GetTimesheetData
from Reporting.print import PrintPFDTimesheet

from Tags.templatetags import tr_month

from django.views import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from UdyniManagement.menu import UdyniMenu
from UdyniManagement.views import TemplateViewMenu, ListViewMenu, CreateViewMenu, UpdateViewMenu, DeleteViewMenu
from UdyniManagement.views import AjaxPermissionRequiredMixin, ObjectValidationMixin

from django.contrib.auth.mixins import PermissionRequiredMixin

import re
import pandas as pd
from lxml import etree
import datetime
import calendar
import json
import copy


# =============================================
# EPAS CODES
#

class EpasCodeList(PermissionRequiredMixin, ListViewMenu):
    model = EpasCode
    paginate_by = 20
    permission_required = 'Reporting.epas_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "EPAS codes"
        context['choices'] = EpasCode.CHOICES
        print(context['page_obj'])
        return context


class EpasCodeImport(PermissionRequiredMixin, View):

    http_method_names = ['get', 'post']
    permission_required = 'Reporting.epas_manage'

    def get(self, request, *args, **kwargs):
        context = {
            'title': 'Import EPAS codes',
            'form': EpasCodeUpdateForm(),
            'menu': UdyniMenu().getMenu(request.user),
            'back_url': reverse_lazy('epas_view'),
        }
        return render(request, 'Reporting/epascode_form.html', context)

    def post(self, request, *args, **kwargs):
        form = EpasCodeUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            # Parse file
            codes = {}
            try:
                f = request.FILES['file']
                parser = etree.HTMLParser(encoding="utf-8")
                tbody = etree.HTML(f.read(), parser=parser).find("body/table/tbody")
                if tbody is None:
                    raise ValidationError("Invalid file. Cannot parse code table.")
                for row in iter(tbody):
                    # Get cells
                    cols = row.getchildren()
                    # Check if the code is active
                    code = cols[0].find("a").text.strip()
                    desc = cols[2].text
                    if desc is not None:
                        desc = desc.strip()
                        codes[code] = desc
            except Exception as e:
                form.add_error(None, str(e))
                context = {
                    'title': 'Import EPAS codes',
                    'form': form,
                    'menu': UdyniMenu().getMenu(request.user),
                    'back_url': reverse_lazy('epas_view'),
                }
                return render(request, 'Reporting/epascode_form.html', context)

            for k, v in codes.items():
                try:
                    obj = EpasCode.objects.get(code=k)
                    if obj.description != v:
                        obj.description = v
                        obj.save()
                except EpasCode.DoesNotExist:
                    new_code = EpasCode(code=k, ts_code="", description=v)
                    new_code.save()
            return redirect('epas_view')

        else:
            context = {
                'title': 'Import EPAS codes',
                'form': form,
                'menu': UdyniMenu().getMenu(request.user),
                'back_url': reverse_lazy('epas_view'),
            }
            return render(request, 'Reporting/epascode_form.html', context)


class EpasCodeUpdate(PermissionRequiredMixin, View):

    http_method_names = ['post', ]
    permission_required = 'Reporting.epas_manage'

    def post(self, request, *args, **kwargs):
        for k, v in request.POST.items():
            m = re.match(r"ts_(\d+)", k)
            if m is not None:
                pk = int(m.groups()[0])
                try:
                    obj = EpasCode.objects.get(pk=pk)
                    obj.ts_code = v
                    obj.save()
                except EpasCode.DoesNotExist:
                    pass

        return JsonResponse({'success': True})


# =============================================
# BANK HOLYDAYS
#

class BankHolidayList(PermissionRequiredMixin, ListViewMenu):
    model = BankHoliday
    permission_required = 'Reporting.holiday_view'

    def ordinaltg(self, n):
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(4 if 10 <= n % 100 < 20 else n % 10, "th")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Bank Holidays"
        for bh in context['object_list']:
            if bh.year == 0:
                bh.date = "{0:s} {1:d}{2:s}".format(calendar.month_name[bh.month], bh.day, self.ordinaltg(bh.day))
            else:
                bh.date = "{0:s} {1:d}{2:s}, {3:d}".format(calendar.month_name[bh.month], bh.day, self.ordinaltg(bh.day), bh.year)
        return context


class BankHolidayCreate(PermissionRequiredMixin, CreateViewMenu):
    model = BankHoliday
    fields = ['name', 'year', 'month', 'day']
    permission_required = 'Reporting.holiday_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('bankholiday_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new bank holiday"
        context['back_url'] = self.get_success_url()
        return context


class BankHolidayUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = BankHoliday
    fields = ['name', 'year', 'month', 'day']
    permission_required = 'Reporting.holiday_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('bankholiday_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify bank holiday"
        context['back_url'] = self.get_success_url()
        return context


class BankHolidayDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = BankHoliday
    permission_required = 'Reporting.holiday_manage'
    template_name = "UdyniManagement/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('bankholiday_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete bank holiday"
        context['message'] = "Are you sure you want to delete the bank holiday: {0!s}?".format(context['bankholiday'])
        context['back_url'] = self.get_success_url()
        return context


# =============================================
# PERSONNEL COSTS
#
class PersonnelCostList(PermissionRequiredMixin, ListViewMenu):
    model = PersonnelCost
    permission_required = 'Reporting.costs_view'

    def get_queryset(self):
        return PersonnelCost.objects.all().order_by('researcher', 'year')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Personnel cost"
        return context


class PersonnelCostCreate(PermissionRequiredMixin, CreateViewMenu):
    model = PersonnelCost
    fields = ['researcher', 'year', 'cost']
    permission_required = 'Reporting.costs_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('cost_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new personnel cost"
        context['back_url'] = reverse_lazy('cost_view')
        return context


class PersonnelCostUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = PersonnelCost
    fields = ['year', 'cost']
    permission_required = 'Reporting.costs_manage'
    template_name = "UdyniManagement/generic_form.html"

    def get_success_url(self):
        return reverse_lazy('cost_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify personnel cost of " + str(context['personnelcost'].researcher)
        context['back_url'] = reverse_lazy('cost_view')
        return context


class PersonnelCostDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = PersonnelCost
    permission_required = 'Reporting.costs_manage'
    template_name = "UdyniManagement/confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy('cost_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete personnel cost"
        context['message'] = "Are you sure you want to delete the personnel cost for {0!s} for year {1!s}?".format(context["personnelcost"].researcher, context["personnelcost"].year)
        context['back_url'] = reverse_lazy('cost_view')
        return context


# =============================================
# PRESENCES
#

class PresenceDataList(PermissionRequiredMixin, ListViewMenu):
    model = PresenceData
    view_only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.presences_view'):
            return True
        elif self.request.user.has_perm('Reporting.presences_view_own'):
            self.view_only_own = True
            return True
        return False

    def get_queryset(self):
        qs = PresenceData.objects.annotate(year=ExtractYear('day'))

        if self.view_only_own:
            qs = qs.filter(Q(researcher__username=self.request.user))

        qs = (
            qs.values('researcher', 'year')
            .annotate(
                tot_hours=Sum('hours', filter=Q(code__ts_code=EpasCode.NONE) | Q(code__isnull=True) | Q(code__ts_code=EpasCode.MISSION)),
                tot_hours_nom=Sum('hours', filter=Q(code__ts_code=EpasCode.NONE) | Q(code__isnull=True)),
                working_days=Count('hours', filter=Q(code__ts_code=EpasCode.NONE) | ~Q(hours=0)),
                holidays=Count('code', filter=Q(code__ts_code=EpasCode.HOLIDAYS)),
                illness_leave=Count('code', filter=Q(code__ts_code=EpasCode.ILLNESS)),
                missions=Count('code', filter=Q(code__ts_code=EpasCode.MISSION)),
            )
            .order_by('year')
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Presences summary"
        # Extract researchers' IDs
        researchers_pks = []
        for q in context['object_list']:
            if q['researcher'] not in researchers_pks:
                researchers_pks.append(q['researcher'])
        context['researchers'] = Researcher.objects.filter(pk__in=researchers_pks).order_by()
        return context


class PresenceDataDetail(PermissionRequiredMixin, ListViewMenu):
    model = PresenceData
    context_object_name = 'presences'

    def has_permission(self):
        if self.request.user.has_perm('Reporting.presences_view'):
            return True
        elif self.request.user.has_perm('Reporting.presences_view_own'):
            r = get_object_or_404(Researcher, pk=self.kwargs['researcher'])
            if r.username == self.request.user:
                return True
        return False

    def get_template_names(self):
        if 'month' in self.kwargs:
            return ["Reporting/presencedata_detailmonth.html", ]
        else:
            return ["Reporting/presencedata_detail.html", ]

    def get_queryset(self):
        if 'month' in self.kwargs:
            qs = (
                PresenceData.objects
                .annotate(year=ExtractYear('day'), month=ExtractMonth('day'))
                .filter(
                    researcher=self.kwargs['researcher'],
                    year=self.kwargs['year'],
                    month=self.kwargs['month'],
                )
                .annotate(code_name=F('code__code'))
                .order_by('day')
            )
            cs = (
                PresenceData.objects
                .annotate(year=ExtractYear('day'), month=ExtractMonth('day'))
                .filter(
                    researcher=self.kwargs['researcher'],
                    year=self.kwargs['year'],
                    month=self.kwargs['month'],
                    code__isnull=False,
                )
                .values('code')
                .annotate(
                    code_name=F('code__code'),
                    code_desc=F('code__description'),
                    code_ts=F('code__ts_code'),
                    tot_code=Count('code'),
                )
                .order_by()
            )

        else:
            qs = (
                PresenceData.objects
                .annotate(year=ExtractYear('day'))
                .filter(researcher=self.kwargs['researcher'], year=self.kwargs['year'])
                .annotate(month=ExtractMonth('day'))
                .values('month')
                .annotate(
                    tot_hours=Sum('hours', filter=Q(code__ts_code=EpasCode.NONE) | Q(code__isnull=True) | Q(code__ts_code=EpasCode.MISSION)),
                    tot_hours_nom=Sum('hours', filter=Q(code__ts_code=EpasCode.NONE) | Q(code__isnull=True)),
                    working_days=Count('hours', filter=Q(code__ts_code=EpasCode.NONE) | ~Q(hours=0)),
                    holidays=Count('code', filter=Q(code__ts_code=EpasCode.HOLIDAYS)),
                    illness_leave=Count('code', filter=Q(code__ts_code=EpasCode.ILLNESS)),
                    missions=Count('code', filter=Q(code__ts_code=EpasCode.MISSION)),
                )
                .order_by('month')
            )
            cs = (
                PresenceData.objects
                .annotate(year=ExtractYear('day'))
                .filter(researcher=self.kwargs['researcher'], year=self.kwargs['year'], code__isnull=False)
                .values('code')
                .annotate(
                    code_name=F('code__code'),
                    code_desc=F('code__description'),
                    code_ts=F('code__ts_code'),
                    tot_code=Count('code'),
                )
                .order_by()
            )

        return {'pres_stat': qs, 'code_stat': cs}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        r = Researcher.objects.get(pk=self.kwargs['researcher'])
        if 'month' in self.kwargs:
            context['title'] = "Presences for {0!s} - {1:s} {2:d}".format(r, tr_month.month_num2en(self.kwargs['month']), self.kwargs['year'])
        else:
            context['title'] = "Presences summary for {0!s} - {1:d}".format(r, self.kwargs['year'])
        return context


class PresenceDataImport(PermissionRequiredMixin, View):

    http_method_names = ['get', 'post']
    manage_only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.presences_manage'):
            return True
        elif self.request.user.has_perm('Reporting.presences_manage_own'):
            self.manage_only_own = True
            return True
        return False

    def get(self, request, *args, **kwargs):
        # Clear session
        try:
            del request.session['presences']
        except KeyError:
            pass
        if self.manage_only_own:
            try:
                r = Researcher.objects.get(username=request.user)
            except Researcher.DoesNotExist:
                raise PermissionDenied("User is not registered as researcher")
            except MultipleObjectsReturned:
                raise PermissionDenied("User is registered as multiple researchers. This should not happen!")
            form = PresenceInputForm(researcher=r)
        else:
            form = PresenceInputForm()

        context = {
            'title': "Import presence data",
            'form': form,
            'menu': UdyniMenu().getMenu(request.user),
        }
        return render(request, 'Reporting/presencedata_form.html', context)

    def post(self, request, *args, **kwargs):
        if self.manage_only_own:
            try:
                r = Researcher.objects.get(username=request.user)
            except Researcher.DoesNotExist:
                raise PermissionDenied("User is not registered as researcher")
            except MultipleObjectsReturned:
                raise PermissionDenied("User is registered as multiple researchers. This should not happen!")
            form = PresenceInputForm(researcher=r, data=request.POST, files=request.FILES)
        else:
            form = PresenceInputForm(data=request.POST, files=request.FILES)

        if form.is_valid():
            r = form.cleaned_data['researcher']
            # Check that user is allowd to load data for this researcher
            if self.manage_only_own and r.username != request.user:
                raise PermissionDenied()

            # Load excel file
            xls = pd.ExcelFile(request.FILES['file'])
            # Process excel file
            presences = process_presences(xls, f"{r.surname} {r.name}")
            request.session['presences'] = serialize_presences(presences)
            context = {
                'title': f"Confirm presence data for {r}",
                'summary': summarize_presences(presences),
                'researcher': r,
                'menu': UdyniMenu().getMenu(request.user),
            }
            return render(request, 'Reporting/presencedata_summary.html', context)

        context = {
            'title': "Import presence data",
            'form': form,
            'menu': UdyniMenu().getMenu(request.user),
        }
        return render(request, 'Reporting/presencedata_form.html', context)


class PresenceDataStore(PermissionRequiredMixin, View):

    http_method_names = ['post', ]
    manage_only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.presences_manage'):
            return True
        elif self.request.user.has_perm('Reporting.presences_manage_own'):
            self.manage_only_own = True
            return True
        return False

    def post(self, request, *args, **kwargs):
        if 'presences' in request.session:
            # Unserialize presences
            presences = unserialize_presences(request.session['presences'])
            researcher = get_object_or_404(Researcher, pk=request.POST['researcher'])

            # Verify permissions
            if self.manage_only_own and researcher.username != request.user:
                raise PermissionDenied()

            check_presences_unique(presences)

            # data = []
            for year, v1 in presences.items():
                for month, v2 in v1.items():
                    # Check post data
                    checkbox = "i_{0:d}_{1:s}".format(year, month)
                    if checkbox in request.POST and request.POST[checkbox] == 'on':
                        # Insert data in DB
                        for i, row in v2.iterrows():
                            # Convert code
                            if row['Code'] != "":
                                try:
                                    code = EpasCode.objects.get(code=row['Code'])
                                except EpasCode.DoesNotExist:
                                    print("Missing code:", year, month, row['Date'], row['Code'])
                                    code = None
                            else:
                                code = None

                            # Check if data is already in DB
                            try:
                                obj = PresenceData.objects.get(researcher=researcher, day=row['Date'])
                                update = False
                                if obj.hours != row['Hours']:
                                    obj.hours = row['Hours']
                                    update = True
                                if obj.code != code:
                                    obj.code = code
                                    if code is not None and code.ts_code:
                                        obj.ts_code=code.ts_code
                                    update = True
                                if update:
                                    obj.save()

                            except PresenceData.MultipleObjectsReturned:
                                print("ERROR: more that one result! This should never happen!")

                            except PresenceData.DoesNotExist:
                                p = PresenceData(researcher=researcher,
                                                 day=row['Date'],
                                                 hours=row['Hours'],
                                                 code=code)
                                if code is not None and code.ts_code:
                                    p.ts_code=code.ts_code
                                p.save()
                                # data.append(p) NOTE: disabled bulk create as it was impossibile to debug an integrity violation

                # if len(data):
                    # PresenceData.objects.bulk_create(data)

        return redirect('presencedata_view')


# =============================================
# REPORTING PERIODS
#

class ReportingPeriodList(PermissionRequiredMixin, ListViewMenu):
    model = ReportingPeriod
    permission_required = 'Reporting.reporting_view'

    def get_queryset(self):
        qs = (
            ReportingPeriod.objects
            .annotate(
                project_name=F('project__name'),
                is_own=ExpressionWrapper(Q(project__pi__username=self.request.user), output_field=BooleanField()),
            )
            .order_by('project__name', 'rp_start')
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Reporting periods"
        print(context['object_list'])
        return context


class ReportingCreate(PermissionRequiredMixin, CreateViewMenu):
    model = ReportingPeriod
    fields = ['project', 'rp_start', 'rp_end']
    template_name = "Reporting/reportingperiod_add.html"
    manage_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.reporting_manage'):
            return True
        if self.request.user.has_perm('Reporting.reporting_manage_own'):
            self.manage_own = True
            return True
        return False

    def get_success_url(self):
        return reverse_lazy('reporting_periods')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new reporting period"
        context['back_url'] = self.get_success_url()
        if self.manage_own:
            context['form'].fields['project'].queryset = Project.objects.filter(Q(pi__username=self.request.user))
        if 'project' in self.request.GET:
            try:
                pk = int(self.request.GET['project'])
                context['form'].fields['project'].initial = pk
            except:
                pass
        return context

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        if self.manage_own:
            # If can manage only own projects, check that the project submitted is owned by the user
            if form.cleaned_data['project'].pi is None or form.cleaned_data['project'].pi.username != self.request.user:
                raise PermissionDenied('You do not have the right to edit reporting periods for this project')
        return super().form_valid(form)


class ReportingUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = ReportingPeriod
    fields = ['rp_start', 'rp_end']
    template_name = "UdyniManagement/generic_form.html"

    def has_permission(self):
        if self.request.user.has_perm('Reporting.reporting_manage'):
            return True
        if self.request.user.has_perm('Reporting.reporting_manage_own'):
            period = get_object_or_404(ReportingPeriod, pk=self.kwargs['pk'])
            if period.project.pi is not None and period.project.pi.username == self.request.user:
                return True
        return False

    def get_success_url(self):
        return reverse_lazy('reporting_periods')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Editing reporting period "
        context['back_url'] = self.get_success_url()
        return context


class ReportingDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = ReportingPeriod
    template_name = "UdyniManagement/confirm_delete.html"

    def has_permission(self):
        if self.request.user.has_perm('Reporting.reporting_manage'):
            return True
        if self.request.user.has_perm('Reporting.reporting_manage_own'):
            period = get_object_or_404(ReportingPeriod, pk=self.kwargs['pk'])
            if period.project.pi is not None and period.project.pi.username == self.request.user:
                return True
        return False

    def get_success_url(self):
        return reverse_lazy('reporting_periods')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete reporting period"
        values = [
                context['reportingperiod'].rp_start,
                context['reportingperiod'].rp_end,
                context['reportingperiod'].project.name,
        ]
        context['message'] = "Are you sure you want to delete the reporting period from {0!s} to {1!s} for the project {2!s}?".format(*values)
        context['back_url'] = self.get_success_url()
        return context


# =============================================
# REPORTED WORK AND MISSIONS
#

class ReportingList(PermissionRequiredMixin, TemplateViewMenu):
    template_name = 'Reporting/reportingperiod_list_byproject.html'
    only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_view'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_view_own'):
            self.only_own = True
            return True
        return False

    def create_reporting_list(self):
        # Get self_rid
        if self.only_own:
            try:
                r = Researcher.objects.get(username=self.request.user)
                self_rid = r.pk
            except Researcher.DoesNotExist:
                raise PermissionDenied('User is not associated with a researcher')
            except Researcher.MultipleObjectsReturned:
                raise PermissionDenied('User is not associated with with multiple researchers. This should not happen.')

        projects = OrderedDict()
        for rp in ReportingPeriod.objects.all().order_by('project__name', 'rp_start'):
            has_own = False
            is_own = (rp.project.pi is not None and rp.project.pi.username == self.request.user)

            if rp.project.name not in projects:
                projects[rp.project.name] = {
                    'project': rp.project,
                    'periods': [],
                }
            new_period = {
                'rp': rp,
                'researchers': OrderedDict(),
            }

            work = (
                rp.reported_work
                .order_by('researcher')
                .values('researcher')
                .annotate(
                    fullname=Concat(F('researcher__name'), Value(' '), F('researcher__surname')),
                    rid=F('researcher__pk'),
                    total=Sum('hours'),
                )

            )
            for w in work:
                if not is_own and self.only_own and w['rid'] != self_rid:
                    continue
                new_period['researchers'][w['fullname']] = {
                    'name': w['fullname'],
                    'hours': w['total'],
                    'rid': w['rid'],
                    'missions': 0,
                }
                has_own = True

            missions = (
                rp.reported_missions
                .values('day__researcher')
                .annotate(
                    fullname=Concat(F('day__researcher__name'), Value(' '), F('day__researcher__surname')),
                    rid=F('day__researcher__pk'),
                    missions=Count('day'),
                    mission_hours=Coalesce(Sum('day__hours'), Value(0.0)),
                )
                .order_by('day__researcher')
            )
            for m in missions:
                if not is_own and self.only_own and m['rid'] != self_rid:
                    continue
                if m['fullname'] not in new_period['researchers']:
                    new_period['researchers'][m['fullname']] = {
                        'name': m['fullname'],
                        'rid': m['rid'],
                        'hours': 0.0,
                        'mission_hours': 0.0,
                        'missions': 0,
                    }
                new_period['researchers'][m['fullname']]['missions'] = m['missions']
                new_period['researchers'][m['fullname']]['mission_hours'] = m['mission_hours']
                has_own = True

            # Check if period has to be appended
            if self.only_own and not has_own:
                continue
            projects[rp.project.name]['periods'].append(new_period)

        # Purge empty projects
        for name in list(projects.keys()):
            if not len(projects[name]['periods']):
                del projects[name]

        return projects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.create_reporting_list()
        # Researchers with hours/missions reported
        rep_reseachers = (
            Researcher.objects
            .filter(pk__in=ReportedWork.objects.values('researcher').distinct())
            .union(
                Researcher.objects
                .filter(pk__in=ReportedMission.objects.values('day__researcher').distinct())
            )
            .order_by('surname', 'name')
        )
        # Other researchers
        other_researchers = (
            Researcher.objects
            .filter(~Q(pk__in=rep_reseachers.values('pk')))
            .order_by('surname', 'name')
        )

        context['researchers'] = rep_reseachers
        context['other_researchers'] = other_researchers
        context['title'] = "Reporting"
        return context


class ReportingByResearcher(PermissionRequiredMixin, TemplateViewMenu):  # name='reporting_byresearcher'  <int:rid>
    template_name = 'Reporting/reportingperiod_list_byresearcher.html'
    only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_view'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_view_own'):
            self.only_own = True
            return True
        return False

    def get_reporting(self, researcher):
        # Access conditions
        is_self = researcher.username == self.request.user

        ## Summary by 'project'
        periods = ReportingPeriod.objects
        if self.only_own and not is_self:
            periods = periods.filter(Q(project__pi__username=self.request.user))
        periods = periods.order_by('project__name', 'rp_start')

        work = ReportedWork.objects.filter(researcher=researcher)
        if self.only_own and not is_self:
            work = work.filter(Q(period__project__pi__username=self.request.user))
        work = (
            work
            .order_by('period')
            .values('period')
            .annotate(
                ppk=F('period__pk'),
                project=F('period__project__name'),
                hours=Coalesce(Sum('hours'), Value(0.0)),
            ).order_by()
        )

        missions = ReportedMission.objects.filter(Q(day__researcher=researcher))
        if self.only_own and not is_self:
            missions = missions.filter(Q(period__project__pi__username=self.request.user))
        missions = (
            missions
            .order_by('period__project__name', 'period__rp_start', 'day')
            .values('period')
            .annotate(
                ppk=F('period__pk'),
                project=F('period__project__name'),
                missions=Count('period'),
                mission_hours=Coalesce(Sum('day__hours'), Value(0.0)),
            )
            .order_by()
        )

        by_project = {}
        # Initialize all projects and periods
        for p in periods:
            if p.project.name not in by_project:
                by_project[p.project.name] = []
            by_project[p.project.name].append({
                'pk': p.pk,
                'rp_start': p.rp_start,
                'rp_end': p.rp_end,
                'hours': 0.0,
                'missions': 0,
                'mission_hours': 0.0,
            })

        # Add reported work
        for w in work:
            f = filter(lambda p: p['pk'] == w['ppk'], by_project[w['project']])
            try:
                period = next(f)
                period['hours'] = w['hours']
            except StopIteration:
                print("Cannot find period: {0:d}".format(w['ppk']))

        # Add missions
        for m in missions:
            f = filter(lambda p: p['pk'] == m['ppk'], by_project[m['project']])
            try:
                period = next(f)
                period['missions'] = m['missions']
                period['mission_hours'] = m['mission_hours']
            except StopIteration:
                print("Cannot find period: {0:d}".format(m['ppk']))


        ## Summary by 'year'
        work = (
            ReportedWork.objects
            .filter(researcher=researcher)
            .order_by('year')
            .values('year')
            .annotate(
                hours=Coalesce(Sum('hours'), Value(0.0)),
            ).order_by()
        )

        missions = (
            ReportedMission.objects
            .filter(Q(day__researcher=researcher))
            .annotate(year=ExtractYear('day__day'))
            .order_by('year')
            .values('year')
            .annotate(
                missions=Count('year'),
                mission_hours=Coalesce(Sum('day__hours'), Value(0.0)),
            )
            .order_by()
        )

        presences = (
            PresenceData.objects
            .filter(researcher=researcher)
            .annotate(
                year=ExtractYear('day'),
            )
            .order_by('year')
            .values('year')
            .annotate(
                tot_hours=Coalesce(Sum('hours', filter=Q(code__ts_code=EpasCode.NONE) | Q(code__isnull=True)), Value(0.0)),
            )
            .order_by()
        )

        by_year = {}
        for w in work:
            by_year[w['year']] = {
                'hours': w['hours'],
                'missions': 0,
                'mission_hours': 0.0,
                'total_hours': w['hours'],
                'worked_hours': 0.0
            }

        for p in presences:
            if p['year'] not in by_year:
                by_year[p['year']] = {
                    'hours': 0.0,
                    'missions': 0,
                    'mission_hours': 0.0,
                    'total_hours': 0.0,
                    'worked_hours': 0.0
                }
            by_year[p['year']]['worked_hours'] = p['tot_hours']

        for m in missions:
            if m['year'] not in by_year:
                by_year[m['year']] = {
                    'hours': 0.0,
                    'missions': m['missions'],
                    'mission_hours': m['mission_hours'],
                    'total_hours': m['mission_hours'],
                }
            else:
                by_year[m['year']]['missions'] = m['missions']
                by_year[m['year']]['mission_hours'] = m['mission_hours']
                by_year[m['year']]['total_hours'] += m['mission_hours']

        return OrderedDict(sorted(by_project.items(), key=lambda x: x[0])), OrderedDict(sorted(by_year.items(), key=lambda x: x[0]))

    def get_context_data(self, **kwargs):
        researcher = get_object_or_404(Researcher, pk=self.kwargs['rid'])
        context = super().get_context_data(**kwargs)
        context['title'] = "Personnel reporting for {0!s}".format(researcher)
        by_project, by_year = self.get_reporting(researcher)
        context['by_project'] = by_project
        context['by_year'] = by_year
        context['by'] = 'project'
        if 'by' in self.request.GET:
            if self.request.GET['by'].lower() == 'year':
                context['by'] = 'year'
        context['selected'] = None
        if 'selected' in self.request.GET:
            try:
                context['selected'] = int(self.request.GET['selected'])
            except:
                pass
        return context


class ReportingAjaxPeriod(PermissionRequiredMixin, View):

    http_method_names = ['get', ]
    only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_view'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_view_own'):
            self.only_own = True
            return True
        return False

    def get(self, request, *args, **kwargs):
        # Get parameters from URL
        try:
            pid = int(request.GET['pid'])
            rid = int(request.GET['rid'])
        except:
            raise Http404('Period not found')

        # Get period
        period = get_object_or_404(ReportingPeriod, pk=pid)

        # Get researcher
        researcher = get_object_or_404(Researcher, pk=rid)

        # Check access
        if self.only_own:
            if researcher.username != self.request.user and (period.project.pi is None or period.project.pi.username != self.request.user):
                raise PermissionDenied('You do not have access to this report')

        # Can edit
        can_edit = False
        if self.request.user.has_perm('Reporting.rp_work_manage'):
            can_edit = True
        else:
            if self.request.user.has_perm('Reporting.rp_work_manage_own'):
                if researcher.username == self.request.user or (period.project.pi is not None and period.project.pi.username == self.request.user):
                    can_edit = True

        # Get all work
        work = ReportedWork.objects.filter(researcher=researcher, period=period).order_by('year', 'month')
        missions = ReportedMission.objects.filter(Q(day__researcher=researcher) & Q(period=period)).annotate(year=ExtractYear('day__day'), month=ExtractMonth('day__day')).order_by('day__day')

        data = {}
        data['work'] = []
        current_year = None
        for w in work:
            line = []
            if current_year == None or w.year != current_year:
                line.append({'val': w.year})
                current_year = w.year
            else:
                line.append({'val': ''})
            line.append({'val': tr_month.month_num2en(w.month)})
            line.append({'val': w.hours})
            line.append({'wps': get_workpackages_fractions(w)})
            line.append({'pk': w.pk})
            data['work'].append(line)

        data['missions'] = []
        current_year = None
        for m in missions:
            line = []
            line.append({'date': m.day.day})
            line.append({'wp': m.workpackage.name if m.workpackage is not None else None})
            line.append({'pk': m.pk})
            data['missions'].append(line)

        context = {'details': data, 'researcher': researcher, 'period': period, 'can_edit': can_edit}
        return render(request, 'Reporting/reportingperiod_detail.html', context)


class ReportingAjaxYear(PermissionRequiredMixin, View):

    http_method_names = ['get', ]
    only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_view'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_view_own'):
            self.only_own = True
            return True
        return False

    def get(self, request, *args, **kwargs):

        # Get parameters from URL
        try:
            year = int(request.GET['year'])
            rid = int(request.GET['rid'])
        except:
            raise Http404('Period not found')

        # Get researcher
        researcher = get_object_or_404(Researcher, pk=rid)

        # Check access
        is_self = researcher.username == self.request.user
        can_edit = self.request.user.has_perm('Reporting.rp_work_manage')
        can_edit_own = self.request.user.has_perm('Reporting.rp_work_manage_own')

        # Get work
        work = ReportedWork.objects.filter(researcher=researcher, year=year)
        if self.only_own and not is_self:
            work = work.filter(Q(period__project__pi__username=self.request.user))
        work = work.order_by('month', 'period__project__name')

        # Get periods
        periods = ReportingPeriod.objects.filter(
            Q(rp_start__lte=datetime.date(year, 12, 31)) &
            Q(rp_end__gte=datetime.date(year, 1, 1))
        )
        if self.only_own and not is_self:
            periods = periods.filter(Q(project__pi__username=self.request.user))
        if can_edit or (can_edit_own and is_self):
            periods = periods.annotate(can_edit=ExpressionWrapper(Value(True), output_field=BooleanField()))
        elif can_edit_own:
            periods = periods.annotate(can_edit=ExpressionWrapper(Coalesce(Q(project__pi__username=self.request.user), Value(False)), output_field=BooleanField()))
        else:
            periods = periods.annotate(can_edit=ExpressionWrapper(Value(False), output_field=BooleanField()))
        periods = periods.order_by('project__name', 'rp_start')

        # Get missions
        missions = (
            ReportedMission.objects
            .filter(Q(day__researcher=researcher))
            .annotate(year=ExtractYear('day__day'), month=ExtractMonth('day__day'))
            .filter(year=year)
        )
        if self.only_own and not is_self:
            missions = missions.filter(Q(period__project__pi__username=self.request.user))
        missions = missions.order_by('day__day')

        # Get also the aggregate presences
        presences = (
            PresenceData.objects
            .filter(researcher=researcher)
            .annotate(
                year=ExtractYear('day'),
                month=ExtractMonth('day'),
                hd=Floor(F('hours') / Value(3.6)),
                uh=Least(F('hours'), Value(7.2)),
            )
            .filter(year=year)
            .order_by('day')
            .values('month')
            .annotate(
                tot_hours=Coalesce(Sum('hours', filter=Q(code__ts_code=EpasCode.NONE) | Q(code__isnull=True)), Value(0.0)),
                missions=Count('code', filter=Q(code__ts_code=EpasCode.MISSION)),
                half_days=Coalesce(Sum('hd', filter=Q(code__ts_code=EpasCode.NONE) | Q(code__isnull=True)), Value(0.0)),
                usable_hours=Coalesce(Sum('uh', filter=Q(code__ts_code=EpasCode.NONE) | Q(code__isnull=True)), Value(0.0))
            )
            .order_by('month')
        )

        data = {}
        data['work'] = []
        data['missions'] = []
        for j in range(12):
            line = [{'value': tr_month.month_num2en(j+1)}, ]
            for i, p in enumerate(periods):
                is_own = is_self or (p.project.pi is not None and p.project.pi.username == self.request.user)
                if self.check_month_in_period(year, j+1, p):
                    line.append({'ppk': p.pk, 'month': j+1, 'can_edit': can_edit or (can_edit_own and is_own)})
                else:
                    line.append({})
            line_m = copy.deepcopy(line)
            line += [{'value': 0.0}, {'value': 0.0}, {'value': 0.0}, {'value': 0.0}]
            line_m += [{'value': 0}, {'value': 0}, ]
            data['work'].append(line)
            data['missions'].append(line_m)

        periods_pk = [p.pk for p in periods]
        total_by_month = [0.0 for i in range(12)]

        # Reported hours
        for w in work:
            is_own = is_self or (w.period.project.pi is not None and w.period.project.pi.username == self.request.user)
            data['work'][w.month - 1][periods_pk.index(w.period.pk) + 1]['pk'] = w.pk
            data['work'][w.month - 1][periods_pk.index(w.period.pk) + 1]['can_edit'] = can_edit or (can_edit_own and is_own)
            data['work'][w.month - 1][periods_pk.index(w.period.pk) + 1]['hours'] = w.hours
            data['work'][w.month - 1][periods_pk.index(w.period.pk) + 1]['wps'] = get_workpackages_fractions(w)
            total_by_month[w.month - 1] += w.hours

        # Totals by month
        for i, t in enumerate(total_by_month):
            data['work'][i][-4]['value'] = f"{t:.1f}"

        # Total worked hours by month and total missions
        for p in presences:
            data['work'][p['month'] - 1][-3]['value'] = f"{p['usable_hours']:.1f}"
            data['work'][p['month'] - 1][-2]['value'] = f"{int(p['half_days']):d} ({int(p['half_days']) * 3.6:.1f})"
            data['work'][p['month'] - 1][-1]['value'] = f"{p['tot_hours']:.1f}"
            data['missions'][p['month'] - 1][-1]['value'] = f"{p['missions']:d}"

        totals = []
        totals.append('Totals')
        for i in range(1, len(data['work'][0])):
            s = 0.0
            for m in range(12):
                if 'hours' in data['work'][m][i]:
                    s += data['work'][m][i]['hours']
            totals.append("{0:.1f}".format(s))

        # Add missions
        for m in missions:
            is_own = is_self or (m.period.project.pi is not None and m.period.project.pi.username == self.request.user)
            if 'missions' not in data['missions'][m.month - 1][periods_pk.index(m.period.pk) + 1]:
                data['missions'][m.month - 1][periods_pk.index(m.period.pk) + 1]['missions'] = []
            data['missions'][m.month - 1][periods_pk.index(m.period.pk) + 1]['missions'].append({'pk': m.pk, 'day': m.day.day, 'wp': m.workpackage, 'can_edit': can_edit or (can_edit_own and is_own)})
            data['missions'][m.month - 1][-2]['value'] += 1

        context = {
            'year': year,
            'details': data,
            'researcher': researcher,
            'periods': periods,
            'totals': totals,
        }
        return render(request, 'Reporting/reportingperiod_detailyear.html', context)

    def check_month_in_period(self, y, m, p):
        ndays = calendar.monthrange(y, m)[1]
        if p.rp_start < datetime.date(y, m, ndays) and p.rp_end > datetime.date(y, m, 1):
            return True
        else:
            return False


class ReportingAddWork(ObjectValidationMixin, AjaxPermissionRequiredMixin, CreateView):
    model = ReportedWork
    form_class = ReportedWorkForm
    template_name = 'UdyniManagement/ajax_form.html'
    input_objects = {
        'researcher': {'class': Researcher, 'pk': 'rid'},
        'period': {'class': ReportingPeriod, 'pk': 'pid'},
    }

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_manage'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_manage_own'):
            if self.researcher.username == self.request.user:
                return True
            if self.period.project.pi is not None and self.period.project.pi.username == self.request.user:
                return True
        return False

    def available_months(self):
        # Months that already have work reported
        already_reported = (
            ReportedWork.objects
            .filter(researcher=self.researcher, period=self.period)
            .order_by('year', 'month')
            .annotate(year_month=Concat(F('year'), Value("_"), F('month'), output_field=CharField()))
            .values_list('year_month', flat=True)
        )

        # Available months
        year_month = []
        for y in range(self.period.rp_start.year, self.period.rp_end.year + 1):
            if y == self.period.rp_start.year:
                if y == self.period.rp_end.year:
                    year_month += [(f"{y:d}_{m:d}", f"{tr_month.month_num2en(m)} {y:d}") for m in range(self.period.rp_start.month, self.period.rp_end.month + 1)]
                else:
                    year_month += [(f"{y:d}_{m:d}", f"{tr_month.month_num2en(m)} {y:d}") for m in range(self.period.rp_start.month, 13)]

            elif y == self.period.rp_end.year:
                year_month += [(f"{y:d}_{m:d}", f"{tr_month.month_num2en(m)} {y:d}") for m in range(1, self.period.rp_end.month + 1)]
            else:
                year_month += [(f"{y:d}_{m:d}", f"{tr_month.month_num2en(m)} {y:d}") for m in range(1, 13)]

        # Return filtered list
        return list(filter(lambda x: x[0] not in already_reported, year_month))

    def get(self, request, *args, **kwargs):
        if not len(self.available_months()):
            # Return error if there's no available period
            rsp = JsonResponse(data={'status': 'error', 'message': f"No available months to report"})
            rsp.status_code = 400
            return rsp
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['researcher'] = self.researcher
        kwargs['period'] = self.period
        kwargs['available_months'] = self.available_months()
        if 'year' in self.request.GET and 'month' in self.request.GET:
            try:
                kwargs['year'] = int(self.request.GET['year'])
                kwargs['month'] = int(self.request.GET['month'])
            except:
                pass
        return kwargs

    def form_valid(self, form):
        try:
            self.object = form.save()
            return JsonResponse(data={'status': 'ok', 'year': self.object.year})
        except Exception as e:
            rsp = JsonResponse(data={'status': 'error', 'message': f"Failed to add reported work (Error: {e})"})
            rsp.status_code = 500
            return rsp


class ReportingAddMission(ObjectValidationMixin, AjaxPermissionRequiredMixin, CreateView):
    model = ReportedMission
    form_class = AddReportedMissionForm
    template_name = 'UdyniManagement/ajax_form.html'
    input_objects = {
        'researcher': {'class': Researcher, 'pk': 'rid'},
        'period': {'class': ReportingPeriod, 'pk': 'pid'},
    }

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_manage'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_manage_own'):
            if self.researcher.username == self.request.user:
                return True
            if self.period.project.pi is not None and self.period.project.pi.username == self.request.user:
                return True
        return False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['researcher'] = self.researcher
        kwargs['period'] = self.period
        try:
            kwargs['year'] = int(self.request.GET['year'])
        except:
            pass
        return kwargs

    def form_valid(self, form):
        try:
            self.object = form.save()
            return JsonResponse(data={'status': 'ok', 'year': self.object.day.day.year})
        except Exception as e:
            rsp = JsonResponse(data={'status': 'error', 'message': f"Failed to add reported mission (Error: {e})"})
            rsp.status_code = 500
            return rsp


class ReportingModWork(ObjectValidationMixin, AjaxPermissionRequiredMixin, UpdateView):
    model = ReportedWork
    pk_url_kwarg = 'wid'
    form_class = ReportedWorkForm
    template_name = 'UdyniManagement/ajax_form.html'
    only_own = False
    input_objects = {
        'researcher': {'class': Researcher, 'pk': 'rid'},
    }

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_manage'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_manage_own'):
            self.only_own = True
            return True
        return False

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.only_own and obj.period.project.pi is not None and obj.period.project.pi.username != self.request.user and obj.researcher.username != self.request.user:
            raise PermissionDenied('You do not have permission to edit this report')
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['researcher'] = None
        kwargs['period'] = None
        return kwargs

    def form_valid(self, form):
        try:
            self.object = form.save()
            return JsonResponse(data={'status': 'ok', 'year': self.object.year})
        except Exception as e:
            rsp = JsonResponse(data={'status': 'error', 'message': f"Failed to modify reported work (Error: {e})"})
            rsp.status_code = 500
            return rsp


class ReportingDelWork(ObjectValidationMixin, AjaxPermissionRequiredMixin, DeleteView):
    model = ReportedWork
    pk_url_kwarg = 'wid'
    template_name = 'UdyniManagement/ajax_form.html'
    only_own = False
    input_objects = {
        'researcher': {'class': Researcher, 'pk': 'rid'},
    }

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_manage'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_manage_own'):
            self.only_own = True
            return True
        return False

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.only_own and obj.period.project.pi is not None and obj.period.project.pi.username != self.request.user and obj.researcher.username != self.request.user:
            raise PermissionDenied('You do not have permission to edit this report')
        return obj

    def delete(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            y = self.object.year
            self.object.delete()
            return JsonResponse(data={'status': 'ok', 'year': y})
        except Exception as e:
            log = logging.getLogger('django')
            log.exception(f"Failed to delete reported work (Error: {e})")
            rsp = JsonResponse(data={'status': 'error', 'message': f"Failed to delete reported work (Error: {e})"})
            rsp.status_code = 500
            return rsp


class ReportingModMission(ObjectValidationMixin, AjaxPermissionRequiredMixin, UpdateView):
    model = ReportedMission
    pk_url_kwarg = 'mid'
    fields = ['workpackage', ]
    template_name = 'UdyniManagement/ajax_form.html'
    only_own = False
    input_objects = {
        'researcher': {'class': Researcher, 'pk': 'rid'},
    }

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_manage'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_manage_own'):
            self.only_own = True
            return True
        return False

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.only_own and obj.period.project.pi is not None and obj.period.project.pi.username != self.request.user and obj.day.researcher.username != self.request.user:
            raise PermissionDenied('You do not have permission to edit this report')
        return obj

    def get_form(self, *args):
        form = super().get_form(*args)
        wps = WorkPackage.objects.filter(project=self.object.period.project)
        form.fields['workpackage'].queryset = wps
        return form

    def form_valid(self, form):
        try:
            self.object = form.save()
            return JsonResponse(data={'status': 'ok', 'year': self.object.day.day.year})
        except Exception as e:
            rsp = JsonResponse(data={'status': 'error', 'message': f"Failed to modify reported mission (Error: {e})"})
            rsp.status_code = 500
            return rsp


class ReportingDelMission(ObjectValidationMixin, AjaxPermissionRequiredMixin, DeleteView):
    model = ReportedMission
    pk_url_kwarg = 'mid'
    template_name = 'UdyniManagement/ajax_form.html'
    only_own = False
    input_objects = {
        'researcher': {'class': Researcher, 'pk': 'rid'},
    }

    def has_permission(self):
        if self.request.user.has_perm('Reporting.rp_work_manage'):
            return True
        if self.request.user.has_perm('Reporting.rp_work_manage_own'):
            self.only_own = True
            return True
        return False

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.only_own and obj.period.project.pi is not None and obj.period.project.pi.username != self.request.user and obj.day.researcher.username != self.request.user:
            raise PermissionDenied('You do not have permission to edit this report')
        return obj

    def delete(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            y = self.object.day.day.year
            self.object.delete()
            return JsonResponse(data={'status': 'ok', 'year': y})
        except Exception as e:
            log = logging.getLogger('django')
            log.exception(f"Failed to delete reported work (Error: {e})")
            rsp = JsonResponse(data={'status': 'error', 'message': f"Failed to delete reported mission (Error: {e})"})
            rsp.status_code = 500
            return rsp


# =============================================
# TIMESHEETS
#

class TimeSheetsView(PermissionRequiredMixin, TemplateViewMenu):
    template_name = 'Reporting/timesheet_list.html'
    only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.timesheet_view'):
            return True
        if self.request.user.has_perm('Reporting.timesheet_view_own'):
            self.only_own = True
            return True
        return False

    def get_list(self):
        out = {}
        # We need to get the list of researcher that have reported work/missions and for which years
        work = ReportedWork.objects
        if self.only_own:
            # Filter on username
            work = work.filter(Q(researcher__username=self.request.user))
        work = (
            work
            .annotate(
                name=F('researcher__name'),
                surname=F('researcher__surname'),
                rid=F('researcher__pk'),
            )
            .values('name', 'surname', 'rid', 'year')
            .order_by('surname', 'name', 'year')
            .distinct()
        )
        for w in work:
            full_name = "{0:s} {1:s}".format(w['name'], w['surname'])
            if full_name not in out:
                out[full_name] = {'rid': w['rid'], 'years': []}
            out[full_name]['years'].append(w['year'])

        missions = ReportedMission.objects
        if self.only_own:
            # Filter on username
            missions = missions.filter(Q(day__researcher__username=self.request.user))
        missions = (
            missions
            .annotate(
                name=F('day__researcher__name'),
                surname=F('day__researcher__surname'),
                rid=F('day__researcher__pk'),
                year=ExtractYear('day__day'),
            )
            .values('name', 'surname', 'rid', 'year')
            .order_by('surname', 'name', 'year')
            .distinct()
        )
        for m in missions:
            full_name = "{0:s} {1:s}".format(m['name'], m['surname'])
            if full_name not in out:
                out[full_name] = {'rid': m['rid'], 'years': []}
            if m['year'] not in out[full_name]['years']:
                out[full_name]['years'].append(m['year'])
                out[full_name]['years'].sort()
        return out

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Timesheets"
        context['list'] = self.get_list()
        return context


class TimeSheetsGenerate(PermissionRequiredMixin, TemplateViewMenu):
    """ Show a page for the selection of the month
        Generation, modification and save is handled through Ajax
    """
    template_name = 'Reporting/timesheet_generate.html'

    def has_permission(self):
        self.researcher = get_object_or_404(Researcher, pk=self.kwargs['rid'])
        if self.request.user.has_perm('Reporting.timesheet_manage'):
            return True
        if self.request.user.has_perm('Reporting.timesheet_manage_own') and self.researcher.username == self.request.user:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Timesheets generation for {0!s} for year {1:d}".format(self.researcher, self.kwargs['year'])
        context['researcher'] = self.researcher
        context['year'] = self.kwargs['year']
        try:
            m = int(self.request.GET.get('month'))
            if m >= 1 and m <= 12:
                context['month'] = m
        except Exception:
            pass
        context['months'] = list(range(1, 13, 1))
        return context


class TimesheetAjaxDenied(View):
    http_method_names = ['get', ]
    def get(self, request, *args, **kwargs):
        raise PermissionDenied('Resource not available')


class TimeSheetsAjaxGenerate(PermissionRequiredMixin, View):
    """ Handle the data exchange to generate a timesheet for a given month
    """

    http_method_names = ['get', 'post']

    def has_permission(self):
        self.researcher = get_object_or_404(Researcher, pk=self.kwargs['rid'])
        if self.request.user.has_perm('Reporting.timesheet_manage'):
            return True
        if self.request.user.has_perm('Reporting.timesheet_manage_own') and self.researcher.username == self.request.user:
            return True
        return False

    def get(self, request, *args, **kwargs):
        year = self.kwargs['year']
        month = self.kwargs['month']
        ndays = calendar.monthrange(year, month)[1]

        try:
            data = GetTimesheetData(self.researcher.pk, year, month, generate=True)
            return JsonResponse({'error': False, 'year': year, 'month': month, 'ts': data})

        except ReportingError as e:
            return JsonResponse({'error': True, 'year': year, 'month': month, 'message': 'There are inconsistencies in the reported work (Error: {0!s})'.format(e)})

        except AssertionError as e:
            return JsonResponse({'error': True, 'year': year, 'month': month, 'message': 'Assertion failed: {0!s}'.format(e)})

    def post(self, request, *args, **kwargs):
        # Kwargs
        year = self.kwargs['year']
        month = self.kwargs['month']
        log = logging.getLogger('diango')

        # Decode json data submitted
        try:
            data = json.loads(request.body.decode("utf-8"))
            for k, v in data['projects'].items():
                used_days = Q()
                pid = int(k)
                for d, h in v.items():
                    day = datetime.date(year, month, int(d) + 1)
                    print("Saving project {0:d}, day {1!s}".format(pid, day))
                    used_days |= Q(day=day)
                    try:
                        ts = (
                            TimesheetHours.objects
                            .get(
                                Q(report__researcher=self.researcher) &
                                Q(day=day) &
                                Q(report__period__project__pk=pid)
                            )
                        )
                        if ts.hours != h:
                            ts.hours = h
                            ts.save()
                    except TimesheetHours.DoesNotExist:
                        # Get report
                        try:
                            report = (
                                ReportedWork.objects.get(
                                    Q(researcher=self.researcher) &
                                    Q(year=year) &
                                    Q(month=month) &
                                    Q(period__project__pk=pid) &
                                    Q(period__rp_start__lte=day) &
                                    Q(period__rp_end__gte=day)
                                )
                            )
                        except ReportedWork.DoesNotExist:
                            return JsonResponse({'saveok': False, 'error': "Cannot find corresponding reported work for project ID {0:d}, day {1!s}".format(pid, day)})
                        except MultipleObjectsReturned:
                            return JsonResponse({'saveok': False, 'error': "Found more than one corresponding reported work for project ID {0:d}, day {1!s}".format(pid, day)})

                        ts = TimesheetHours()
                        ts.report = report
                        ts.report_wp = None
                        ts.day = day
                        ts.hours = h
                        ts.save()

                    except MultipleObjectsReturned:
                        return JsonResponse({'saveok': False, 'error': "Got multiple elements for project ID {0:d}, day {1!s}".format(pid, day)})

                # Delete old unused days from TimesheetHours
                (
                    TimesheetHours.objects
                    .annotate(
                        year=ExtractYear('day'),
                        month=ExtractMonth('day'),
                    )
                    .filter(
                        Q(report__researcher=self.researcher) &
                        Q(year=year) &
                        Q(month=month) &
                        Q(report__period__project__pk=pid) &
                        ~used_days
                    )
                    .delete()
                )

            for k, v in data['workpackages'].items():
                used_days = Q()
                wid = int(k)
                try:
                    wp = WorkPackage.objects.get(pk=wid)
                except WorkPackage.DoesNotExist:
                    return JsonResponse({'saveok': False, 'error': "Failed to retrieve workpackage with ID {0:d}".format(wid)})

                for d, h in v.items():
                    day = datetime.date(year, month, int(d) + 1)
                    log.info(f"Saving workpackage {wp}, day {day}")
                    used_days |= Q(day=day)
                    try:
                        ts = (
                            TimesheetHours.objects
                            .get(
                                Q(report__researcher=self.researcher) &
                                Q(day=day) &
                                Q(report_wp__workpackage=wp)
                            )
                        )
                        if ts.hours != h:
                            ts.hours = h
                            ts.save()
                    except TimesheetHours.DoesNotExist:
                        # Get report
                        try:
                            report = (
                                ReportedWork.objects.get(
                                    Q(researcher=self.researcher) &
                                    Q(year=year) &
                                    Q(month=month) &
                                    Q(period__project=wp.project) &
                                    Q(period__rp_start__lte=day) &
                                    Q(period__rp_end__gte=day)
                                )
                            )
                        except ReportedWork.DoesNotExist:
                            msg = f"Cannot find corresponding reported work for project {wp.project.name} (ID: {wp.project.pk}), day {day}"
                            log.exception(msg)
                            return JsonResponse({'saveok': False, 'error': msg})
                        except MultipleObjectsReturned:
                            msg = f"Found more than one corresponding reported work for project {wp.project.name} (ID: {wp.project.pk}), day {day}"
                            log.exception(msg)
                            return JsonResponse({'saveok': False, 'error': msg})

                        # Get report WP
                        try:
                            report_wp = ReportedWorkWorkpackage.objects.get(report=report, workpackage=wp)
                        except ReportedWork.DoesNotExist:
                            msg = f"Cannot find corresponding reported work for workpackage {wp.name} (ID: {wp.pk}) of project {wp.project.name} (ID: {wp.project.name}), day {day}"
                            log.exception(msg)
                            return JsonResponse({'saveok': False, 'error': msg})
                        except MultipleObjectsReturned:
                            msg = f"Found more than one corresponding reported work for workpackage {wp.name} (ID: {wp.pk}) of project {wp.project.name} (ID: {wp.project.name}), day {day}"
                            log.exception(msg)
                            return JsonResponse({'saveok': False, 'error': msg})

                        ts = TimesheetHours()
                        ts.report = report
                        ts.report_wp = report_wp
                        ts.day = day
                        ts.hours = h
                        ts.save()

                    except MultipleObjectsReturned:
                        msg = f"Got multiple elements for workpackage ID {wid}, day {day}"
                        log.exception(msg)
                        return JsonResponse({'saveok': False, 'error': msg})

                # Delete old unused days from TimesheetHours
                (
                    TimesheetHours.objects
                    .annotate(
                        year=ExtractYear('day'),
                        month=ExtractMonth('day'),
                    )
                    .filter(
                        Q(report__researcher=self.researcher) &
                        Q(year=year) &
                        Q(month=month) &
                        Q(report_wp__workpackage=wp) &
                        ~used_days
                    )
                    .delete()
                )

        except json.JSONDecodeError:
            msg = "Failed to decode JSON submitted"
            log.exception(msg)
            return JsonResponse({'saveok': False, 'error': msg})

        except ValueError as e:
            log.exception(f"Failed to convert number")
            # Forward exception after logging
            raise e

        # Save successful
        return JsonResponse({'saveok': True, 'error': None})


class TimeSheetsAjaxCheck(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Reporting.timesheet_view'):
            return True
        if self.request.user.has_perm('Reporting.timesheet_view_own'):
            self.only_own = True
            return True
        return False

    def get(self, request, *args, **kwargs):
        # Get rid and year from request
        researcher = get_object_or_404(Researcher, pk=request.GET.get('rid'))
        is_self = researcher.username == self.request.user
        if self.only_own and not is_self:
            raise PermissionDenied("You're not allowed to check these timesheets")

        can_edit = self.request.user.has_perm('Reporting.timesheet_manage')
        can_edit_own = self.request.user.has_perm('Reporting.timesheet_manage_own')

        try:
            year = int(request.GET.get('year'))
        except:
            raise Http404('Invalid year')

        out = []
        allgood = True
        for m in range(1, 13, 1):
            ok, reported, projects = CheckTimesheetData(researcher.pk, year, m)
            if not ok:
                allgood = False
            out.append({
                'month': m,
                'ok': ok,
                'reported': reported,
                'can_generate': can_edit or (can_edit_own and is_self),
                'projects': OrderedDict(sorted(projects.items())),
            })

        # Create a list of projects with TS
        projects = {}
        for o in out:
            for k, v in o['projects'].items():
                if k not in projects:
                    projects[k] = v[1]

        context = {
            'researcher': researcher,
            'projects': OrderedDict(sorted(projects.items())),
            'ts': out,
            'year': year,
            'allgood': allgood,
        }

        return render(request, 'Reporting/timesheet_list_byyear.html', context)


class TimeSheetsPrint(PermissionRequiredMixin, View):

    http_method_names = ['get', 'post']

    def has_permission(self):
        # Get researcher
        self.researcher = get_object_or_404(Researcher, pk=self.kwargs['rid'])
        if self.request.user.has_perm('Reporting.timesheet_view'):
            return True
        if self.request.user.has_perm('Reporting.timesheet_view_own') and self.researcher.username == self.request.user:
            return True
        return False

    def get(self, request, *args, **kwargs):
        # Get year
        try:
            year = int(self.kwargs['year'])
        except:
            raise Http404('Invalid year')

        # Get months to report
        try:
            months = [int(request.GET.get('month')), ]
        except:
            months = list(range(1, 13))

        # Get project ID if we are printing individual timesheets
        try:
            pid = int(request.GET.get('pid'))
            project = get_object_or_404(Project, pk=pid)
        except:
            project = None

        good_months = []
        for month in months:
            ok, reported, projects = CheckTimesheetData(self.researcher.pk, year, month)

            # Timesheet is not complete
            if not ok:
                raise Http404(f"Timesheet not available for {tr_month.month_num2en(month)}/{year}. Please generate it.")

            # Add month only if there's something reported
            if reported and (project is None or project.name in projects):
                good_months.append(month)

        if not len(good_months):
            raise Http404('Nothing to report')

        # Function to check the incompatibility between a researcher and the director
        # TODO: what we do when the director and the researcher are the same person?
        def check_incompatibility(researcher, director, year, month):
            s = datetime.date(year, month, 1)
            e = datetime.date(year, month, calendar.monthrange(year, month)[1])
            q = (
                ConflictOfInterest.objects
                .filter(researcher=researcher, director=director)
                .filter(Q(start_date__lte=e) | (Q(end_date__isnull=True) | Q(end_date__gte=s)))
            )
            if len(q):
                return (str(q[0].delegate), 'Delegate of IFN Director')
            else:
                return (str(director), 'IFN Director')

        try:
            context = []
            for month in good_months:
                print("Processing month", month)

                # Get number of days in month
                ndays = calendar.monthrange(year, month)[1]

                # Get role from ResearcherRole table
                current_role = None
                roles = ResearcherRole.objects.filter(researcher=self.researcher).order_by('start_date')
                for role in roles:
                    # TODO: check criteria to switch to another role based on date
                    if role.start_date <= datetime.date(year, month, 1):
                        current_role = role.get_role_display()
                    else:
                        break
                # Default to researcher if nothing is set in ResearcherRole
                if current_role is None:
                    current_role = "Researcher"

                # Load timesheet data
                ts_data = GetTimesheetData(self.researcher.pk, year, month, project)

                # Director
                director = (
                    ResearcherRole.objects
                    .filter(role=ResearcherRole.INSTITUTE_DIRECTOR)
                    .filter(start_date__lt=datetime.date(year, month, ndays))
                    .order_by('-start_date')
                    .first()
                    .researcher
                )

                # Check incompatibilities
                supervisor_signer = check_incompatibility(self.researcher, director, year, month)

                # Check needed signatures
                signatures = {}
                for p in ts_data['projects']:
                    if 'pi_id' in p:
                        try:
                            pi = Researcher.objects.get(pk=p['pi_id'])
                        except Researcher.DoesNotExist:
                            pi = None

                        if pi is not None and pi != self.researcher:
                            name = str(pi)
                            if name not in signatures:
                                signatures[name] = []
                            signatures[name].append(p['name'])

                for k, v in signatures.items():
                    signatures[k] = ", ".join(sorted(v))

                # Search for a proper signature day
                sign_day = (
                    PresenceData.objects
                    .filter(
                        Q(researcher=self.researcher) &
                        Q(day__gt=datetime.date(year, month, ndays)) &
                        (Q(code=None) | Q(code__ts_code=EpasCode.NONE)) &
                        Q(hours__gt=0)
                    )
                    .order_by('day')
                    .first()
                )
                if sign_day:
                    sign_day = sign_day.day
                else:
                    sign_day = None

                context.append({
                    'title': f"Timesheets for {self.researcher} for year {year}",
                    'month': month,
                    'year': year,
                    'researcher': f"{self.researcher.name} {self.researcher.surname}",
                    'director': supervisor_signer,
                    'employment': current_role,
                    'beneficiary': "CNR-IFN",
                    'ts': ts_data,
                    'signatures': signatures,
                    'sign_day': sign_day,
                })

            if len(context) == 1:
                return FileResponse(PrintPFDTimesheet(context), as_attachment=True, filename='{0:s}_{1:04d}_{2:02d}.pdf'.format(self.researcher.surname.lower(), year, good_months[0]))
            else:
                return FileResponse(PrintPFDTimesheet(context), as_attachment=True, filename='{0:s}_{1:04d}.pdf'.format(self.researcher.surname.lower(), year))

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Http404(str(e))
