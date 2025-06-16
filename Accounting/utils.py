import datetime
from collections import OrderedDict
from django.db.models import Q, F, Sum
from Accounting.models import SplitBudget, SplitVariazione, SplitImpegno

def create_split_accounting_detail(contab):
    # First we get the budget
    split_accounting = {}
    budget = (
        SplitBudget.objects
        .filter(contab=contab)
        .values('voce')
        .order_by('voce')
        .annotate(
            total=Sum('importo'),
            voce_num=F('voce__voce'),
            voce_desc=F('voce__description')
        )
        .order_by('voce_num')
    )

    for b in budget:
        split_accounting[b['voce_num']] = {
            'desc': b['voce_desc'],
            'stanziamento': b['total'],
            'variazioni': 0,
            'assestato': 0,
            'impegnato': 0,
            'residuo': 0,
        }

    # Check variazioni
    variazioni = SplitVariazione.objects.filter(Q(src_contab=contab) | Q(dst_contab=contab))
    for var in variazioni:
        if var.src_contab == contab:
            split_accounting[var.src_voce.voce]['variazioni'] -= var.importo
        if var.dst_contab == contab:
            if var.dst_voce.voce not in split_accounting:
                split_accounting[var.dst_voce.voce] = {
                    'desc': var.dst_voce.description,
                    'stanziamento': 0,
                    'variazioni': 0,
                    'assestato': 0,
                    'impegnato': 0,
                    'residuo': 0,
                }
            split_accounting[var.dst_voce.voce]['variazioni'] += var.importo

    # Check impegni
    impegni_raw = SplitImpegno.objects.filter(contab=contab)
    impegni = {}

    # Merge 'impegni' over years
    current_year = datetime.date.today().year
    for im in impegni_raw:
        label = "{0:d}_{1:d}".format(im.impegno.esercizio_orig, im.impegno.numero)
        if label not in impegni:
            impegni[label] = {
                'esercizio_orig': im.impegno.esercizio_orig,
                'numero': im.impegno.numero,
                'voce': im.impegno.voce,
                'description': im.impegno.description,
                'importo': 0.0,
                'pagato': 0.0,
            }
        
        if im.impegno.esercizio < current_year:
            impegni[label]['importo'] += im.impegno.pagato_competenza + im.impegno.pagato_residui
            impegni[label]['pagato'] += im.impegno.pagato_competenza + im.impegno.pagato_residui

        else:
            impegni[label]['importo'] += im.impegno.im_competenza + im.impegno.im_residui
            impegni[label]['pagato'] += im.impegno.pagato_competenza + im.impegno.pagato_residui

    # Add impegni to accounting data
    for label, im in impegni.items():
        if im['voce'].voce not in split_accounting:
            split_accounting[im['voce'].voce] = {
                'desc': im['voce'].description,
                'stanziamento': 0.0,
                'variazioni': 0.0,
                'assestato': 0.0,
                'impegnato': 0.0,
                'residuo': 0.0,
            }
        split_accounting[im['voce'].voce]['impegnato'] += im['importo']

    # Assestato e residui
    totals = {
        'stanziamento': 0.0,
        'variazioni': 0.0,
        'assestato': 0.0,
        'impegnato': 0.0,
        'residuo': 0.0,
    }
    for voce, s in split_accounting.items():
        s['assestato'] = s['stanziamento'] + s['variazioni']
        s['residuo'] = s['assestato'] - s['impegnato']
        totals['stanziamento'] += s['stanziamento']
        totals['variazioni'] += s['variazioni']
        totals['assestato'] += s['assestato']
        totals['impegnato'] += s['impegnato']
        totals['residuo'] += s['residuo']

    return {'accounting': OrderedDict(sorted(split_accounting.items(), key=lambda x: x[0])), 'variazioni': variazioni, 'impegni': impegni, 'totals': totals}