from datetime import datetime,date

def get_fy_year(ent_date):
    start_year = False
    end_year = False
    if ent_date:
        ent_date = datetime.strptime(ent_date, "%Y-%m-%d")
        if ent_date.month >= 4:
            start_year = ent_date.year
            end_year = ent_date.year + 1
        else:
            start_year = ent_date.year - 1
            end_year = ent_date.year
        
    fy_start_date = datetime(start_year, 4, 1).date()
    fy_end_date = datetime(end_year, 3, 31).date()

    return fy_start_date,fy_end_date