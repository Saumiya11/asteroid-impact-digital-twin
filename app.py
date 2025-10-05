# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from simulation import simulate_impact, apply_kinetic_impactor, apply_nuclear_deflection, apply_fragmentation
from utils import (estimate_population_affected, results_to_dataframe,
                   create_folium_map, export_results_csv, export_results_json, SAMPLE_COUNTRY_DENSITY)
from streamlit_folium import folium_static

# APP CONFIG
st.set_page_config(page_title="Asteroid Impact Digital Twin", layout="wide", initial_sidebar_state="expanded")

import base64
from pathlib import Path

# Encode the logo to base64 so Streamlit always finds it
def get_base64_image(image_path):
    img_bytes = Path(image_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return f"data:image/png;base64,{encoded}"

logo_data = get_base64_image("logo.png")

st.markdown(
    f"""
    <style>
        .header-container {{
            display: flex;
            align-items: center;
            justify-content: left;
            background-color: #0b3d91;
            padding: 10px 20px;
            border-radius: 12px;
            color: white;
        }}
        .header-container img {{
            height: 60px;
            margin-right: 20px;
        }}
        .header-container h1 {{
            font-size: 26px;
            margin: 0;
        }}
    </style>
    <div class="header-container">
        <img src="{logo_data}" alt="Logo">
        <h1>Asteroid Impact Digital Twin — NASA Space Apps Challenge 2025</h1>
    </div>
    """,
    unsafe_allow_html=True
)


# --- Sidebar: Project Info / Inputs / Mitigation selection ---
with st.sidebar:
    st.title("Asteroid Impact DT")
    st.markdown("**Meteor Madness — NASA Space Apps Challenge 2025**")
    st.markdown("---")
    st.subheader("Input asteroid parameters")
    diameter = st.number_input("Diameter (m)", value=50.0, min_value=0.1, step=0.1, format="%.2f",
                               help="Diameter of asteroid in meters")
    velocity = st.number_input("Velocity (km/s)", value=20.0, min_value=1.0, step=0.1, format="%.2f",
                               help="Velocity in km/s; will be converted to m/s")
    density = st.number_input("Density (kg/m³)", value=3000.0, min_value=500.0, step=10.0)
    angle = st.slider("Impact angle (degrees)", min_value=15, max_value=90, value=45)
    lat = st.number_input("Impact latitude", value=0.0, format="%.6f")
    lon = st.number_input("Impact longitude", value=0.0, format="%.6f")
    population_density = st.number_input("Population density for estimation (people/km²)", 
                                         value=float(SAMPLE_COUNTRY_DENSITY['default']),
                                         min_value=0.0, step=1.0)

    st.markdown("---")
    st.subheader("Mitigation options")
    mitigation_choice = st.selectbox("Strategy", ["None", "Kinetic Impactor (reduce velocity %)",
                                                  "Nuclear (reduce energy %)", "Fragmentation (split)"])
    # mitigation parameters
    if mitigation_choice == "Kinetic Impactor (reduce velocity %)":
        kin_reduce = st.slider("Velocity reduction (%)", min_value=1, max_value=99, value=20)
    elif mitigation_choice == "Nuclear (reduce energy %)":
        nuc_reduce = st.slider("Energy reduction (%)", min_value=1, max_value=99, value=60)
    elif mitigation_choice == "Fragmentation (split)":
        frag_count = st.slider("Fragment count (N)", min_value=2, max_value=50, value=4)
    else:
        kin_reduce = nuc_reduce = frag_count = None

    st.markdown("---")
    st.write("Export / Run")
    run_button = st.button("Run Simulation")
    st.write("Download snapshot after run in the Results section")

# --- Main layout ---
st.header("Asteroid Impact Digital Twin — Meteor Madness (NASA Space Apps Challenge 2025)")
st.markdown("""
This app simulates asteroid impacts using empirical physics-based formulas, visualizes damage zones on a map,
and allows you to test mitigation strategies (kinetic impactor, nuclear deflection, fragmentation).
**Units:** diameter in meters, velocity in km/s (converted internally to m/s).
**Note:** Results are approximations for demonstration and decision-support only.
""")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Simulation Inputs")
    st.write(f"**Diameter:** {diameter:.2f} m")
    st.write(f"**Velocity:** {velocity:.2f} km/s -> {velocity*1000.0:.2f} m/s")
    st.write(f"**Density:** {density:.1f} kg/m³")
    st.write(f"**Angle:** {angle}°")
    st.write(f"**Impact location:** lat {lat:.4f}, lon {lon:.4f}")
    st.write(f"**Population density (fallback):** {population_density:.1f} people/km²")

with col2:
    st.subheader("Mitigation (selected)")
    st.write(f"**Strategy:** {mitigation_choice}")
    if mitigation_choice == "Kinetic Impactor (reduce velocity %)":
        st.write(f"Velocity reduction: {kin_reduce}%")
    elif mitigation_choice == "Nuclear (reduce energy %)":
        st.write(f"Energy reduction: {nuc_reduce}%")
    elif mitigation_choice == "Fragmentation (split)":
        st.write(f"Fragments: {frag_count}")

# Run simulation if user clicks
if run_button:
    with st.spinner("Running simulation..."):
        # Convert velocity from km/s to m/s
        velocity_m_s = float(velocity) * 1000.0
        sim_before = simulate_impact(diameter, velocity_m_s, density_kg_m3=density, impact_angle_deg=angle, lat=lat, lon=lon)

        # apply mitigation if any
        if mitigation_choice == "None":
            sim_after = None
        elif mitigation_choice == "Kinetic Impactor (reduce velocity %)":
            sim_after = apply_kinetic_impactor(sim_before, velocity_reduction_pct=kin_reduce)
        elif mitigation_choice == "Nuclear (reduce energy %)":
            sim_after = apply_nuclear_deflection(sim_before, energy_reduction_pct=nuc_reduce)
        elif mitigation_choice == "Fragmentation (split)":
            sim_after = apply_fragmentation(sim_before, fragment_count=frag_count)
        else:
            sim_after = None

    # Display summary cards
    st.markdown("## Results Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Energy (megatons TNT)", f"{sim_before['energy_megatons']:.3e}")
    c2.metric("Crater diameter (m)", f"{sim_before['crater_diameter_m']:.1f}")
    c3.metric("Lethal radius (km)", f"{sim_before['damage_radii_m']['lethal_m']/1000.0:.2f}")
    c4.metric("Estimated affected pop (lethal zone)", 
              f"{estimate_population_affected(sim_before['affected_areas_km2']['lethal_m'], population_density):.0f}"
              if sim_before['affected_areas_km2']['lethal_m'] else "0")

    st.markdown("### Detailed numeric results (Before)")
    df_before = results_to_dataframe(sim_before, label="before")
    st.dataframe(df_before, height=220)

    if sim_after is not None:
        st.markdown("### Detailed numeric results (After mitigation)")
        df_after = results_to_dataframe(sim_after, label="after")
        st.dataframe(df_after, height=220)

    # Prepare CSV/JSON export
    if sim_after is None:
        df_all = df_before
        json_blob = [sim_before]
    else:
        df_all = pd.concat([df_before, df_after], ignore_index=True)
        json_blob = [sim_before, sim_after]

    # Export buttons
    st.download_button("Download results CSV", data=export_results_csv(df_all), file_name=f"impact_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
    st.download_button("Download results JSON", data=export_results_json(json_blob), file_name=f"impact_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json")

    # Map visualization: show both before and after side-by-side
    st.markdown("## Map visualization")
    map_col1, map_col2 = st.columns(2)
    with map_col1:
        st.markdown("**Before**")
        folium_map_before = create_folium_map(sim_before)
        folium_static(folium_map_before, width=700, height=450)
    with map_col2:
        st.markdown("**After**")
        if sim_after is not None:
            folium_map_after = create_folium_map(sim_after)
            folium_static(folium_map_after, width=700, height=450)
        else:
            st.info("No mitigation selected; after-map would be identical to before.")

    # Comparison charts
    st.markdown("## Comparison")
    comp_col1, comp_col2 = st.columns(2)
    with comp_col1:
        st.write("Radius comparison (m)")
        comp_df = pd.DataFrame({
            'zone': ['lethal', 'severe', 'moderate'],
            'before_m': [sim_before['damage_radii_m']['lethal_m'], sim_before['damage_radii_m']['severe_m'], sim_before['damage_radii_m']['moderate_m']],
            'after_m': [sim_after['damage_radii_m']['lethal_m'] if sim_after else None,
                        sim_after['damage_radii_m']['severe_m'] if sim_after else None,
                        sim_after['damage_radii_m']['moderate_m'] if sim_after else None]
        })
        st.bar_chart(comp_df.set_index('zone'))
    with comp_col2:
        st.write("Population affected (estimate)")
        pop_before = {k: estimate_population_affected(sim_before['affected_areas_km2'][k], population_density) for k in sim_before['affected_areas_km2']}
        pop_after = {k: estimate_population_affected(sim_after['affected_areas_km2'][k], population_density) if sim_after else None for k in sim_before['affected_areas_km2']}
        pop_df = pd.DataFrame({
            'zone': list(pop_before.keys()),
            'before': list(pop_before.values()),
            'after': list(pop_after.values()) if sim_after else None
        })
        st.bar_chart(pop_df.set_index('zone'))

    st.success("Simulation complete — use downloads to save results. Scroll for optional advanced features.")

