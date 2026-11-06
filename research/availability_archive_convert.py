import pyarrow.parquet as pq, json, sys, collections
# Run with any Python that has pyarrow; the model's own environment stays untouched.
for y in (2019,2021,2022,2023,2024,2025,2026):
    t=pq.read_table(f"data/history/espn_box/player_box_{y}.parquet")
    keep=[c for c in ("game_id","game_date","season","season_type","team_id","team_display_name","team_location","team_short_display_name","athlete_id","athlete_display_name","minutes","did_not_play","active","starter") if c in t.column_names]
    rows=t.select(keep).to_pylist()
    for r in rows: r["game_date"]=str(r["game_date"])[:10]
    json.dump(rows,open(f"data/history/espn_box/{y}.json","w")); 
    print(y,len(rows),rows[0] if y==2019 else "", "games",len({r['game_id'] for r in rows}),"null min",sum(r.get('minutes') is None for r in rows),"dnp",sum(bool(r.get('did_not_play')) for r in rows))
