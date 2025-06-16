import re
import pandas as pd
import numpy as np
from django.db.models import Q
from Tags.templatetags.tr_month import month_num2it

from Reporting.models import BankHoliday


def process_presences(xls, researcher):
    # Cycle through sheets
    out = {}
    # First find out if the xls comes from EPAS
    if 'Riassunto RF' in xls.sheet_names:
        # Old format
        for n in xls.sheet_names:
            m = re.match(r"\d+\-(\d+)|(\d+)", n)
            if m is not None:
                month = [int(el) for el in m.groups() if el is not None]
                month = month_num2it(month[0])

                # Convert sheet to dataframe
                df = xls.parse(n, header=3, usecols="A:D")

                # Get year from date
                year = df.loc[0, 'Giorno'].year
                if year not in out:
                    out[year] = {}

                # Lines that actually had data
                good_lines = ~pd.isna(df['Giorno']).to_numpy()

                out[year][month] = pd.DataFrame()
                out[year][month]['Date'] = pd.to_datetime(df.loc[good_lines, 'Giorno'])
                # Convert working hours
                hours = df.loc[good_lines, 'Ore lavorate']
                hours[pd.isna(hours)] = 0.0
                out[year][month]['Hours'] = hours
                # Convert absence codes
                codes = df.loc[good_lines, 'Ferie/Missione']
                codes[pd.isna(codes)] = ""
                codes[codes == "Ferie"] = "32"
                codes[codes == "ferie"] = "32"
                codes[codes == "RF"] = "91"
                codes[codes == "Missione"] = "92"
                codes[codes == "missione"] = "92"
                codes[codes == "Malattia"] = "111"
                codes[codes == "malattia"] = "111"
                out[year][month]['Code'] = codes

                # Add 7.2 hours to missions (but only on working days!)
                weekday = out[year][month].loc[:, 'Date'].apply(lambda date: date.isoweekday())
                bank_holiday = out[year][month].loc[:, 'Date'].apply(check_bank_holiday)
                working_days = np.logical_and(weekday < 6, np.logical_not(bank_holiday))
                out[year][month].loc[np.logical_and(out[year][month].loc[:, 'Code'] == "92", working_days), 'Hours'] = 7.2

    else:
        # From EPAS
        for n in xls.sheet_names:
            print(n)
            m = re.match(r"([a-zA-Z \']+)_([a-z]+)(\d+)", n)
            if m is not None:
                name = ConvertApostrophe2Accent(str(m.groups()[0]))
                print(name)
                if name != researcher:
                    continue
                year = int(m.groups()[2])
                if year not in out:
                    out[year] = {}
                month = str(m.groups()[1])

                # Convert sheet to dataframe
                df = xls.parse(n)

                out[year][month] = pd.DataFrame()
                # Convert date
                out[year][month]['Date'] = pd.to_datetime(df['Data'])
                # Convert working hours
                out[year][month]['Hours'] = pd.to_timedelta(df['Lavoro effettivo (hh:mm)'] + ":00") / np.timedelta64(1, 'h')
                # Convert absence codes
                if df['Tutti i codici di assenza'].dtype == np.float64:
                    # Only numeric codes, coverted to float (will not match EpasCode)
                    out[year][month].loc[:, 'Code'] = ""
                    out[year][month].loc[~np.isnan(df.loc[:, 'Tutti i codici di assenza']), 'Code'] = \
                        df.loc[~np.isnan(df.loc[:, 'Tutti i codici di assenza']), 'Tutti i codici di assenza'].astype(int).astype(str)
                else:
                    out[year][month]['Code'] = df['Tutti i codici di assenza'].astype(str)
                out[year][month].loc[out[year][month].loc[:, 'Code'] == 'nan', 'Code'] = ""
                # Check multiple codes
                mpc = out[year][month].loc[:, 'Code'].apply(lambda code: code.find(";") != -1)
                out[year][month].loc[mpc, 'Code'] = out[year][month].loc[mpc, 'Code'].apply(get_single_code)

    return out


def get_single_code(code):
    # Return a single epas code for days with multiple codes
    # TODO: this may not be trivial
    codes = code.split(";")
    i = 0
    try:
        i = codes.index("92E")
    except ValueError:
        try:
            i = codes.index("92")
        except ValueError:
            try:
                i = codes.index("92M")
            except ValueError:
                i = 0
    return codes[i]


def summarize_presences(presences):
    out = {}
    # Cycle over years
    for year, v1 in presences.items():
        out[year] = {}
        tot_hours = 0
        # Cycle over months
        for month, v2 in v1.items():
            out[year][month] = {}
            out[year][month]['hours'] = np.sum(v2['Hours'])
            tot_hours += out[year][month]['hours']
            out[year][month]['workingdays'] = np.sum(v2['Hours'] > 0)
            out[year][month]['codes'] = {}
            uc = np.unique(v2['Code'])
            for c in uc:
                if c == "":
                    continue
                out[year][month]['codes'][c] = np.sum(v2['Code'] == c)
        out[year]['total'] = tot_hours
    return out


def serialize_presences(presences):
    out = {}
    # Cycle over years
    for year, v1 in presences.items():
        out[year] = {}
        # Cycle over months
        for month, v2 in v1.items():
            out[year][month] = v2.to_json()
    return out


def unserialize_presences(json):
    out = {}
    # Cycle over years
    for year, v1 in json.items():
        year = int(year)
        out[year] = {}
        # Cycle over months
        for month, v2 in v1.items():
            out[year][month] = pd.read_json(v2)
    return out


def check_presences_unique(presences):
    dates = []
    for year, v1 in presences.items():
        for month, v2 in v1.items():
            for i, row in v2.iterrows():
                date = row['Date'].strftime("%Y-%m-%d")
                if date in dates:
                    print("Date {0:s} is duplicated!")
                else:
                    dates.append(date)


def check_bank_holiday(date):
    try:
        BankHoliday.objects.get(year=0, month=date.month, day=date.day)
        return True
    except BankHoliday.DoesNotExist:
        try:
            BankHoliday.objects.get(year=date.year, month=date.month, day=date.day)
            return True
        except BankHoliday.DoesNotExist:
            return False


def get_workpackages_fractions(report):
    out = []
    total = 0.0
    # NOTE: filtering out WPs with a zero fraction. Easier to filter here that removing unneeded WP reports
    for wp in report.workpackages.filter(~Q(fraction=0)).order_by('workpackage__name'):
        out.append({'pk': wp.pk, 'wp_pk': wp.workpackage.pk, 'wp': wp.workpackage.name, 'desc': wp.workpackage.desc, 'fraction': wp.fraction})
        total += wp.fraction
    for o in out:
        o['fraction'] /= total
        o['percent'] = o['fraction'] * 100.0
        o['hours'] = o['fraction'] * report.hours
    return out


class ReportingError(Exception):
    """ Special class to handle reporting errors
    The behaviour is the same as a normal exception
    """
    pass


def ConvertApostrophe2Accent(name):
    vowels = 'aeiou'
    accented_vowels = {'a': 'à', 'e': 'è', 'i': 'ì', 'o': 'ò', 'u': 'ù'}
    offset = 0
    while True:
        i = name[offset:].find("'")
        if i == -1:
            return name
        i += offset

        if name[i-1] in vowels:
            name = name[0:i-1] + accented_vowels[name[i-1]] + name[i+1:]
        offset = i
