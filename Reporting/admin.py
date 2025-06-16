from django.contrib import admin
from Reporting.models import BankHoliday, EpasCode, PersonnelCost, PresenceData, ReportingPeriod, ReportedWork, ReportedMission, ReportedWorkWorkpackage, TimesheetHours

# Register your models here.
admin.site.register(BankHoliday)
admin.site.register(EpasCode)
admin.site.register(PersonnelCost)
admin.site.register(PresenceData)
admin.site.register(ReportingPeriod)
admin.site.register(ReportedWork)
admin.site.register(ReportedWorkWorkpackage)
admin.site.register(ReportedMission)
admin.site.register(TimesheetHours)
