conn = get_connection()  # shared in-memory connection for the test process

view_name = register_csv_as_view(CLEANED_DATASET, view_name="test_csv", conn=conn)

df = query(f"""
            select
                month(dt) as month,
                sum(parcel_qty) as total_parcels
            from {view_name}
            where is_valid_pdt = True
            group by month(dt)
            order by month(dt) asc
            """,
           conn=conn)

print(df)
