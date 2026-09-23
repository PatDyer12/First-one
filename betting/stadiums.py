"""Home stadium location and time zone (hours from Eastern) for each team, by season."""
import math

TEAMS = {  # lat, lon, tz (hours vs Eastern, standard time)
    "ARI": (33.528, -112.263, -2), "ATL": (33.755, -84.401, 0), "BAL": (39.278, -76.623, 0),
    "BUF": (42.774, -78.787, 0), "CAR": (35.226, -80.853, 0), "CHI": (41.862, -87.617, -1),
    "CIN": (39.095, -84.516, 0), "CLE": (41.506, -81.700, 0), "DAL": (32.748, -97.093, -1),
    "DEN": (39.744, -105.020, -2), "DET": (42.340, -83.046, 0), "GB": (44.501, -88.062, -1),
    "HOU": (29.685, -95.411, -1), "IND": (39.760, -86.164, 0), "JAX": (30.324, -81.637, 0),
    "KC": (39.049, -94.484, -1), "LV": (36.091, -115.184, -3), "LA": (33.953, -118.339, -3),
    "LAC": (33.953, -118.339, -3), "MIA": (25.958, -80.239, 0), "MIN": (44.974, -93.258, -1),
    "NE": (42.091, -71.264, 0), "NO": (29.951, -90.081, -1), "NYG": (40.813, -74.074, 0),
    "NYJ": (40.813, -74.074, 0), "PHI": (39.901, -75.168, 0), "PIT": (40.447, -80.016, 0),
    "SEA": (47.595, -122.332, -3), "SF": (37.403, -121.970, -3), "TB": (27.976, -82.503, 0),
    "TEN": (36.166, -86.771, -1), "WAS": (38.908, -76.864, 0),
}
MOVED = {  # (team, before season): old home
    ("LV", 2020): (37.752, -122.201, -3),   # Oakland
    ("LAC", 2017): (32.783, -117.120, -3),  # San Diego
    ("LA", 2016): (38.633, -90.188, -1),    # St. Louis
}
ABROAD = {"LON": (51.556, -0.280, 5), "MEX": (19.303, -99.150, -1), "GER": (48.219, 11.625, 6),
          "FRA": (50.069, 8.645, 6), "MUN": (48.219, 11.625, 6), "SAO": (-23.545, -46.474, 1),
          "MAD": (40.453, -3.688, 6), "DUB": (53.335, -6.228, 5), "MEL": (-37.820, 144.983, 15),
          "RIO": (-22.912, -43.230, 1), "TOR": (43.641, -79.389, 0)}


def home_site(team, season):
    for (t, before), site in MOVED.items():
        if t == team and season < before:
            return site
    return TEAMS.get(team, (39.0, -95.0, -1))


def game_site(home, season, stadium_id, neutral):
    if isinstance(stadium_id, str) and stadium_id[:3] in ABROAD:
        return ABROAD[stadium_id[:3]]
    return home_site(home, season)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))
