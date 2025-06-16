import datetime
import calendar

from django.db.models import Q, F, Sum, Value, Subquery, OuterRef
from django.db.models.functions import ExtractYear, ExtractMonth, Coalesce
from Reporting.models import EpasCode, PresenceData, ReportedWork, ReportedMission, TimesheetHours
from Reporting.utils import check_bank_holiday, get_workpackages_fractions
from Reporting.utils import ReportingError
from Tags.templatetags import tr_month


# Structure of TS data for display/printing
#
# ts = {
#   'numdays': n         # Number of days in month
#   'days': [            # Array of data for each day
#       {
#           'n': n,
#           'holiday': True/False
#       },
#       ...
#   ],
#   'absence_code': [   # Absence code for every day
#       {
#           'a': code,
#           'holiday': True/False
#       },
#       ...
#   ],
#   'projects': [
#       {
#           'has_wps': True,
#           'name':,
#           'refe':,
#           'wps': [
#               {
#                   'name': wp name,
#                   'desc': wp desc,
#                   'id':   wp pk   ???,
#                   'days': [
#                        {
#                            'h': hours,
#                            'mission': True/False,
#                            'holiday': True/False,
#                        },
#                        ...
#                   ]
#                   'sum': hours already in TS,
#                   'total': total hours on WP,
#                   'last': False,
#               },
#               ...
#               {
#                   'name': wp name,
#                   'desc': wp desc,
#                   'id':   wp pk   ???,
#                   'days': [
#                       {
#                           'h': hours,
#                           'mission': True/False,
#                           'holiday': True/False,
#                       },
#                       ...
#                   ]
#                   'sum': hours already in TS,
#                   'total': total hours on WP,
#                   'last': True,
#               },
#           ],
#           'days': [
#               {
#                   'h': hours,
#                   'mission': True/False,
#                   'holiday': True/False,
#               },
#               ...
#           ],
#           'sum': hours already in TS,
#           'total': total hours on project,
#
#       },
#       {
#
#       },
#       ...
#       NOTE: last project is 'internal activities' with all the left hours and missions
#   ],
#   'grand_total': total hours
# }


def round2first(value):
    """ Round the number to the first decimal digit (used to remove rounding errors in sums)
    """
    return round(value * 10.0) / 10.0


def CheckTimesheetData(rid, year, month):
    """ Check that the TS data is consistent with the reported work and returns:
     - ok: true if TS data is consistent
     - reported: true if month has anything reported
     - projects: projects IDs that have something reported in the month
    """

    # Get reported work
    work = (
        ReportedWork.objects
        .filter(
            researcher=rid,
            year=year,
            month=month,
        )
        .order_by(
            'period__project__name',
            'period__rp_start',
        )
    )

    # Count reported missions
    missions = (
        ReportedMission.objects
        .annotate(
            year=ExtractYear('day__day'),
            month=ExtractMonth('day__day'),
        )
        .filter(Q(day__researcher=rid) & Q(year=year) & Q(month=month))
        .annotate(
            project_id=F('period__project__id'),
            project_name=F('period__project__name'),
        )
        .distinct()
    )

    # Get timesheet hours summary
    ts_data_summary = (
        TimesheetHours.objects
        .annotate(
            year=ExtractYear('day'),
            month=ExtractMonth('day')
        )
        .filter(
            Q(report__researcher=rid) &
            Q(year=year) &
            Q(month=month)
        )
        .order_by(
            'report__period__project__name',
            'report__period__rp_start',
            'report_wp__workpackage__name',
            'day',
        )
        .values('report', 'report_wp')
        .annotate(total_hours=Coalesce(Sum('hours'), Value(0.0)))
        .order_by()
    )

    all_good = True
    projects_good = {}

    # Check that TS hours match reported work
    for w in work:
        pname = w.period.project.name
        if pname not in projects_good:
            projects_good[pname] = [True, w.period.project.pk]
        elif not projects_good[pname][0]:
            # Skip incomplete project
            continue

        # Get WPs
        wps = get_workpackages_fractions(w)
        f = list(filter(lambda x: x['report'] == w.pk, ts_data_summary))

        if not len(f):
            # Work reported but no TS data
            projects_good[pname][0] = False
            all_good = False
            continue

        if wps:
            # Splitted on WPs
            for wp in wps:
                for ts in f:
                    if ts['report_wp'] == wp['pk']:
                        if abs(w.hours * wp['fraction'] - ts['total_hours']) > 0.01:
                            print("TS hours does not match report. Project: {0:s}, Workpackage: {1:s} ({2:.1f} != {3:.1f})".format(w.period.project.name, wp['wp'], w.hours * wp['fraction'], ts['total_hours']))
                            # Failed!
                            projects_good[pname][0] = False
                            all_good = False
                        break
                if not projects_good[pname][0]:
                    # Check failed on a previous WP, skip the others
                    break
        else:
            ts = f[0]
            if abs(ts['total_hours'] - w.hours) > 0.01:
                projects_good[pname][0] = False
                all_good = False

    # We also need to check that we havent reported more hours in a day that worked hours
    worked_and_reported_hours = (
        PresenceData.objects
        .annotate(
            year=ExtractYear('day'),
            month=ExtractMonth('day')
        )
        .filter(
            Q(researcher=rid) &
            Q(year=year) &
            Q(month=month)
        )
        .order_by('day')
        .annotate(
            ts_hours=Coalesce(
                Subquery(
                    TimesheetHours.objects
                    .filter(Q(report__researcher=rid) & Q(day=OuterRef('day')))
                    .values('day')
                    .annotate(tot_hours=Sum('hours'))
                    .values('tot_hours')
                ),
                Value(0.0),
            )
        )
    )

    # If any day has more hours reported that worked, we return false but cannot link the error to a specific project
    for day in worked_and_reported_hours:
        # We need to approximate worked hours to one decimal digit
        if abs(round2first(day.hours) - round2first(day.ts_hours)) < -0.01:
            all_good = False

    # Check missions
    for m in missions:
        if m.project_name not in projects_good:
            projects_good[m.project_name] = [True, m.project_id]

    # Everything matched!
    return (all_good, len(projects_good) > 0, projects_good)


def GetTimesheetData(rid, year, month, project=None, generate=False):
    """ Get timesheet data for the given researcher, year, month
    Return timesheet data
    Raise ReportingError on error
    """

    # If we are not generating and the data is not consistent return
    ok, reported, projects = CheckTimesheetData(rid, year, month)
    if not ok and not generate:
        raise ReportingError(f"Timesheet data for RID {rid} for {tr_month.month_num2en(month)} {year} is not consistent")

    if not generate and (not reported or (project is not None and project.name not in projects)):
        raise ReportingError(f"Nothing to report for RID {rid} for {tr_month.month_num2en(month)} {year}.")

    if generate and project is not None:
        raise ReportingError(f"Generation cannot be done for a single project")

    # Get reported work
    work = (
        ReportedWork.objects
        .filter(
            researcher=rid,
            year=year,
            month=month,
        )
        .order_by(
            'period__project__name',
            'period__rp_start',
        )
    )

    # If project is set filter on it
    if project is not None:
        work = work.filter(Q(period__project=project))

    # Get timesheet hours
    ts_data = (
        TimesheetHours.objects
        .annotate(
            year=ExtractYear('day'),
            month=ExtractMonth('day'),
        )
        .filter(
            Q(report__researcher=rid) &
            Q(year=year) &
            Q(month=month)
        )
        .order_by(
            'report__period__project__name',
            'report__period__rp_start',
            'report_wp__workpackage__name',
            'day',
        )
    )

    # Get presences
    presences = (
        PresenceData.objects
        .filter(researcher=rid)
        .annotate(
            year=ExtractYear('day'),
            month=ExtractMonth('day'),
        )
        .filter(
            Q(year=year) &
            Q(month=month)
        )
        .order_by('day')
    )

    # Initialize data
    data = {}
    ndays = calendar.monthrange(year, month)[1]
    data['numdays'] = ndays
    data['days'] = []
    data['projects'] = []
    data['grand_total'] = 0.0
    data['ok'] = ok

    # Setup days and holiday tag
    for d in range(1, ndays + 1, 1):
        date = datetime.date(year=year, month=month, day=d)

        we = False
        # Check Saturday and Sunday
        if date.weekday() > 4:
            we = True

        # Check bank holiday
        bh = False
        if check_bank_holiday(date):
            bh = True

        # Append day with holiday tag, mission tag, absence code and total hours
        data['days'].append({
            'n': d,
            'holiday': we | bh,
            'mission': False,
            'code': "PH" if bh else "",
            'total': 0.0,
        })

    # Process presences
    available_hours = [0.0 for i in range(ndays)]
    for p in presences:
        # Day index
        d = p.day.day - 1

        # Store hours (only for working days)
        if p.hours > 0 and p.ts_code is None or p.ts_code == EpasCode.NONE:
            h = round2first(p.hours)
            data['days'][d]['total'] = h
            available_hours[d] = h

        # Set mission flag
        if p.ts_code == EpasCode.MISSION:
            data['days'][d]['mission'] = True

        # Store absence code
        if p.ts_code == EpasCode.ILLNESS:
            data['days'][d]['code'] = "IL"
        elif data['days'][d]['code'] != "PH":
            if p.ts_code == EpasCode.MISSION:
                data['days'][d]['code'] = "BT"
            elif p.ts_code == EpasCode.HOLIDAYS:
                data['days'][d]['code'] = "AH"

    # Add projects
    p_names = []
    for w in work:
        name = w.period.project.name
        if name not in p_names:
            # First time we got the project. Create new.
            p_names.append(name)

            new_p = {}
            new_p['id'] = w.period.project.pk           # Project ID
            new_p['name'] = name                        # Project name
            new_p['ref'] = w.period.project.reference   # Project reference
            new_p['pi_id'] = w.period.project.pi.pk if w.period.project.pi is not None else None    # Project PI
            new_p['days'] = [0.0 for i in range(ndays)]
            new_p['total'] = 0.0
            new_p['sum'] = 0.0
            new_p['has_wps'] = False                    # Set has_wps False by default
            data['projects'].append(new_p)

        else:
            # Project already created. We get it from the list
            new_p = data['projects'][p_names.index(name)]

        # Get report workpackages
        wps = get_workpackages_fractions(w)
        if len(wps):
            # Project has WPs
            new_p['has_wps'] = True   # Period has split over WPs
            if 'wps' not in new_p:
                # Add WP list if not present
                new_p['wps'] = []

            for wp in wps:
                # Cycle over WPs

                # First check if we already have the WP
                for new_wp in new_p['wps']:
                    if new_wp['id'] == wp['wp_pk']:
                        break
                else:
                    # New workpackage
                    new_wp = {}
                    new_wp['id'] = wp['wp_pk']   # WP ID to check for duplicates
                    new_wp['name'] = wp['wp']    # WP name
                    new_wp['desc'] = wp['desc']  # WP description
                    new_wp['days'] = [0.0 for i in range(ndays)]
                    new_wp['last'] = False       # Set by default as 'not the last' (NB: needed for rendering...)
                    new_wp['total'] = 0.0
                    new_wp['sum'] = 0.0
                    new_p['wps'].append(new_wp)  # Append WP

                # Add total hours
                new_wp['total'] += wp['hours']
                new_p['total'] += wp['hours']

                # Filter already saved TS data
                ts = ts_data.filter(Q(report=w) & Q(report_wp__workpackage__pk=new_wp['id']))

                # Store saved hours if any
                for d in ts:
                    # Add hours
                    new_wp['days'][d.day.day-1] += d.hours
                    new_p['days'][d.day.day-1] += d.hours
                    new_wp['sum'] += d.hours
                    new_p['sum'] += d.hours
                    # Subtract from available hours
                    available_hours[d.day.day-1] -= d.hours

        else:
            # Add total hours
            new_p['total'] += w.hours

            # Filter already saved TS data
            ts = ts_data.filter(report=w, report_wp=None)

            # Store saved hours if any
            for d in ts:
                h = d.hours
                # Add hours
                new_p['days'][d.day.day-1] += h
                new_p['sum'] += h
                # Subtract from available hours
                available_hours[d.day.day-1] -= h

    # Tag last WP in all projects
    for prj in data['projects']:
        if 'wps' in prj:
            # Tag last WP
            prj['wps'][-1]['last'] = True

    # Add reported missions
    rep_m = (
        ReportedMission.objects
        .filter(Q(day__researcher=rid))
        .annotate(
            year=ExtractYear('day__day'),
            month=ExtractMonth('day__day')
        )
        .filter(year=year, month=month)
        .order_by(
            'period__project__name',
            'period__rp_start',
            'day__day',
        )
    )

    # If project is set filter on it
    if project is not None:
        rep_m = rep_m.filter(Q(period__project=project))

    q = Q()  # Query used later to select business travels not reported
    for m in rep_m:
        # Add day to query
        q |= Q(day=m.day.day)
        pname = m.period.project.name
        if pname not in p_names:
            # Project has only business travels. We have to add it
            new_p = {}
            new_p['id'] = m.period.project.pk           # Project ID
            new_p['name'] = pname                       # Project name
            new_p['ref'] = m.period.project.reference   # Project reference
            new_p['pi_id'] = m.period.project.pi.pk if m.period.project.pi is not None else None     # Project PI
            if m.period.project.workpackage_set.all().count() > 0:
                new_p['has_wps'] = True   # Project has WPs
                new_p['wps'] = []
            else:
                new_p['has_wps'] = False
            new_p['days'] = [0.0 for i in range(ndays)]
            new_p['sum'] = 0.0
            new_p['total'] = 0.0

            # Insert project in the right place
            if len(p_names):
                for i, p in enumerate(p_names):
                    if pname > p:
                        continue
                    else:
                        p_names.insert(i, pname)
                        data['projects'].insert(i, new_p)
                        break
                else:
                    p_names.append(pname)
                    data['projects'].append(new_p)
            else:
                p_names.append(pname)
                data['projects'].append(new_p)

        mh = m.day.hours
        if m.workpackage is not None:
            wid = m.workpackage.pk
            for wp in data['projects'][p_names.index(pname)]['wps']:
                if wp['id'] == wid:
                    break
            else:
                # WP not found! There are no hours reported on this WP, we have to add it
                wp = {}
                wp['id'] = wid                   # WP ID to check for duplicates
                wp['name'] = m.workpackage.name  # WP name
                wp['desc'] = m.workpackage.desc  # WP description
                wp['days'] = [0.0 for i in range(ndays)]
                wp['last'] = False       # Set by default as 'not the last'
                wp['total'] = 0.0
                wp['sum'] = 0.0

                # Insert WP in the right place
                if len(data['projects'][p_names.index(pname)]['wps']):
                    for i, old_wp in enumerate(data['projects'][p_names.index(pname)]['wps']):
                        if wp['name'] > old_wp['name']:
                            continue
                        else:
                            data['projects'][p_names.index(pname)]['wps'].insert(i, wp)
                            break
                    else:
                        data['projects'][p_names.index(pname)]['wps'].append(wp)
                else:
                    data['projects'][p_names.index(pname)]['wps'].append(wp)

            # Add business travel to WP
            wp['days'][m.day.day.day - 1] = mh
            # Update WP total
            wp['total'] += mh
            wp['sum'] += mh
            # Update project day
            data['projects'][p_names.index(pname)]['days'][m.day.day.day - 1] = mh
            # Update project total
            data['projects'][p_names.index(pname)]['total'] += mh
            data['projects'][p_names.index(pname)]['sum'] += mh

        else:
            # Add business travel to project
            data['projects'][p_names.index(pname)]['days'][m.day.day.day - 1] = mh
            data['projects'][p_names.index(pname)]['total'] += mh
            data['projects'][p_names.index(pname)]['sum'] += mh

        # Update day total
        data['days'][m.day.day.day - 1]['total'] += mh

    # Add internal activities
    internal = {
        'name': 'Internal activities',
        'ref': '',
        'id': -1,
        'has_wps': False,
        'days': available_hours,
        'total': sum(available_hours),
    }

    # Add business travels not assigned to any period
    missions = presences.filter(Q(ts_code=EpasCode.MISSION) & Q(hours__gt=0) & ~q).order_by('day')
    for m in missions:
        mh = m.hours
        # Add business travel
        internal['days'][m.day.day - 1] = mh
        # Update internal activities total
        internal['total'] += mh
        # Update day total
        data['days'][m.day.day - 1]['total'] += mh

    # Add internal activities as last project
    data['projects'].append(internal)

    # Compute grand total
    for d in data['days']:
        data['grand_total'] += d['total']
    data['grand_total'] = data['grand_total']

    return data
