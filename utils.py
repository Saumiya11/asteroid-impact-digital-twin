# utils.py
import json
import math
import pandas as pd
from streamlit_folium import folium_static
import folium

# small sample densities (people per km^2) for fallback if user doesn't provide population data
SAMPLE_COUNTRY_DENSITY = {
    "default": 60.0,  # global-ish average fallback
    "India": 464.0,
    "USA": 36.0,
    "China": 153.0,
    "Brazil": 25.0,
    "Australia": 3.2
}

def estimate_population_affected(area_km2, population_density_per_km2=None):
    """
    Estimate population affected given area in km^2 and a population density.
    If population_density_per_km2 is None, use default.
    """
    if population_density_per_km2 is None:
        population_density_per_km2 = SAMPLE_COUNTRY_DENSITY['default']
    return area_km2 * population_density_per_km2

def results_to_dataframe(sim_result, label="before"):
    """
    Convert sim_result dict to pandas DataFrame row for export or display.
    """
    row = {}
    row['scenario'] = label
    inp = sim_result['input']
    row.update({
        'diameter_m': inp['diameter_m'],
        'velocity_m_s': inp['velocity_m_s'],
        'density_kg_m3': inp['density_kg_m3'],
        'impact_angle_deg': inp['impact_angle_deg'],
        'mass_kg': sim_result['mass_kg'],
        'energy_joules': sim_result['energy_joules'],
        'energy_megatons': sim_result['energy_megatons'],
        'crater_diameter_m': sim_result['crater_diameter_m']
    })
    for k, v in sim_result['damage_radii_m'].items():
        row[f'{k}_radius_m'] = v
        row[f'{k}_area_km2'] = sim_result['affected_areas_km2'][k]
    # location
    row['lat'] = inp.get('lat')
    row['lon'] = inp.get('lon')
    return pd.DataFrame([row])

def create_folium_map(sim_result, map_tiles='OpenStreetMap', popup=True):
    """
    Create a folium map with concentric circles for damage zones.
    If lat/lon is missing, we return a world map centered at (0,0).
    """
    lat = sim_result['input'].get('lat')
    lon = sim_result['input'].get('lon')
    if lat is None or lon is None:
        lat, lon = 0.0, 0.0
        zoom_start = 2
    else:
        zoom_start = 5

    m = folium.Map(location=[lat, lon], tiles=map_tiles, zoom_start=zoom_start)
    # Add impact marker
    folium.CircleMarker([lat, lon], radius=5, color='black', fill=True, fill_color='black',
                        popup="Impact Point" if popup else None).add_to(m)
    # Color mapping
    colors = {'lethal_m': '#800000', 'severe_m': '#FF4500', 'moderate_m': '#FFA500'}
    for zone, radius_m in sim_result['damage_radii_m'].items():
        # convert meters to kilometers for display but folium uses meters for radius
        folium.Circle(location=[lat, lon],
                      radius=radius_m,
                      color=colors.get(zone, '#3388ff'),
                      fill=True,
                      fill_opacity=0.25,
                      popup=f"{zone}: {radius_m:.0f} m" if popup else None).add_to(m)
    # add crater marker/ellipse
    crater_radius = max(1.0, sim_result['crater_diameter_m'] / 2.0)
    folium.Circle(location=[lat, lon],
                  radius=crater_radius,
                  color='black',
                  fill=True,
                  fill_opacity=0.6,
                  popup=f"Crater radius ~ {crater_radius:.1f} m" if popup else None).add_to(m)
    return m

def export_results_csv(df_all):
    """
    Returns CSV bytes for download.
    """
    return df_all.to_csv(index=False).encode('utf-8')

def export_results_json(list_of_dicts):
    """
    Return json bytes.
    """
    return json.dumps(list_of_dicts, indent=2).encode('utf-8')
