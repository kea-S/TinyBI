UNDERPERFORMING_LOGISTICS_BY_TOTAL_PARCELS = lambda view_name: \
    f"""
    select logistics_provider, sum(parcel_qty) as total_parcel_qty_jan
    from {view_name}
    where is_valid_pdt = True
    and month(dt) = 1
    group by logistics_provider
    order by total_parcel_qty_jan asc
    """


UNDERPERFORMING_LOGISTICS_BY_AVG_BWT = lambda view_name: \
    f"""
    select
        logistics_provider,
        round(sum(sum_bwt)/sum(parcel_qty), 3) as avg_bwt_jan
    from {view_name}
    where is_valid_pdt = True
    and month(dt) = 1
    group by logistics_provider
    order by avg_bwt_jan desc
    """

# sample query format ideation

# f"""
# select
#     {subject},
#     {metric}
# from {view_name}
# where is_valid_pdt = True
# and dt between {date_start} and {date_end}
# {extra_conditions}
# group by {subject}
# order by {sort_on} {order}
# """

AVG_BWT_OVER_MONTHS = lambda view_name: \
    f"""
    select
        month(dt) as month,
        round(sum(sum_bwt)/sum(parcel_qty), 3) as avg_bwt
    from {view_name}
    where is_valid_pdt = True
    group by month(dt)
    order by month(dt) asc
    """


TOTAL_PARCELS_OVER_MONTHS = lambda view_name: \
    f"""
    select
        month(dt) as month,
        sum(parcel_qty) as total_parcels
    from {view_name}
    where is_valid_pdt = True
    group by month(dt)
    order by month(dt) asc
    """


def get_query(view_name, query):
    if query == "UNDERPERFORMING_LOGISTICS_BY_TOTAL_PARCELS":
        return UNDERPERFORMING_LOGISTICS_BY_TOTAL_PARCELS(view_name)
    elif query == "UNDERPERFORMING_LOGISTICS_BY_AVG_BWT":
        return UNDERPERFORMING_LOGISTICS_BY_AVG_BWT(view_name)
    elif query == "AVG_BWT_OVER_MONTHS":
        return AVG_BWT_OVER_MONTHS(view_name)
