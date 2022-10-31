from datetime import date as dt

def year(request):
    return {'year': dt.today().year}