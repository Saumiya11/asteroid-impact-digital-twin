# simulation.py
"""
Physics-based impact simulation helpers for Asteroid Impact Digital Twin.

Notes:
 - All formulas are simplified, empirical approximations meant for educational/demo purposes.
 - Units:
    diameter_m  : meters
    velocity_m_s: meters/second
    density_kg_m3: kg/m^3 (typical asteroid ~ 3000 for rocky)
    impact_angle_deg: degrees (90 vertical)
    lat/lon: decimal degrees

Outputs:
 - energy_joules
 - energy_megatons_tnt
 - crater_diameter_m
 - transient_crater_diameter_m (approx)
 - final_crater_diameter_m (approx)
 - damage_radii_m: dict of different severity radii
 - affected_area_km2 (for each radius)
"""

import math
import numpy as np

# constants
JOULES_PER_MEGATON_TNT = 4.184e15
EARTH_GRAVITY = 9.81  # m/s^2
EARTH_RADIUS_M = 6371000.0

def mass_from_diameter(diameter_m, density_kg_m3=3000.0):
    """Mass of a sphere (asteroid) in kg."""
    r = diameter_m / 2.0
    volume = (4.0/3.0) * math.pi * r**3
    return density_kg_m3 * volume

def kinetic_energy_joules(mass_kg, velocity_m_s):
    """Kinetic energy in joules."""
    return 0.5 * mass_kg * velocity_m_s**2

def energy_megatons(energy_joules):
    return energy_joules / JOULES_PER_MEGATON_TNT

def estimate_crater_diameter(energy_joules, density_impactor=3000.0, density_target=2500.0, impact_angle_deg=45.0):
    """
    Empirical approximation for crater diameter.
    This uses a simplified scaling law; not intended to replace specialized impact models.
    Returns crater diameter in meters.
    """
    # Convert to a physically plausible scaling using a power law.
    # Choose a constant to bring outputs to realistic magnitude; tuned for demo.
    E = energy_joules
    angle_factor = math.sin(math.radians(impact_angle_deg)) ** (1/3)  # shallow impacts make slightly smaller craters
    # empirical scaling: D (m) ~ C * E^(1/4)
    C = 0.035  # tuned coefficient for meters (empirical)
    crater_diameter_m = C * (E ** 0.25) * angle_factor * (density_impactor/density_target)**(1/9)
    # ensure minimum scale ~ few meters for tiny meteors
    return max(1.0, crater_diameter_m)

def estimate_damage_radii(energy_joules):
    """
    Estimate radii (in meters) for different severity zones:
    - lethal_radius: immediate catastrophic effects (blast, thermal)
    - severe_radius: heavy structural damage
    - moderate_radius: moderate damage / broken windows
    Scaling chosen as power law approximations.
    """
    # energy scale in megatons
    E_mt = energy_megatons(energy_joules)
    if E_mt <= 0:
        return {'lethal_m': 0.0, 'severe_m': 0.0, 'moderate_m': 0.0}
    # Use empirical power laws (tuned for demo):
    lethal_m = 1000.0 * (E_mt ** (1/3))        # km-scale for very large energies
    severe_m  = 2000.0 * (E_mt ** (1/3)) * 0.6
    moderate_m = 3000.0 * (E_mt ** (1/3)) * 1.2
    # The above produce meters when E_mt small/large; adjust for tiny impacts
    # Clamp and scale down for small energies
    return {
        'lethal_m': max(5.0, lethal_m),
        'severe_m': max(10.0, severe_m),
        'moderate_m': max(20.0, moderate_m)
    }

def area_from_radius_m(radius_m):
    """Area in km^2 for given radius in meters."""
    area_m2 = math.pi * (radius_m ** 2)
    return area_m2 / 1e6

def simulate_impact(diameter_m, velocity_m_s, density_kg_m3=3000.0, impact_angle_deg=45.0, lat=None, lon=None):
    """
    Main simulation function. Returns a dictionary with physics outputs.
    """
    m = mass_from_diameter(diameter_m, density_kg_m3)
    E = kinetic_energy_joules(m, velocity_m_s)
    E_mt = energy_megatons(E)
    crater_d = estimate_crater_diameter(E, density_impactor=density_kg_m3, impact_angle_deg=impact_angle_deg)
    damage_radii = estimate_damage_radii(E)
    areas_km2 = {k: area_from_radius_m(v) for k, v in damage_radii.items()}

    # Package results
    out = {
        'input': {
            'diameter_m': diameter_m,
            'velocity_m_s': velocity_m_s,
            'density_kg_m3': density_kg_m3,
            'impact_angle_deg': impact_angle_deg,
            'lat': lat,
            'lon': lon
        },
        'mass_kg': m,
        'energy_joules': E,
        'energy_megatons': E_mt,
        'crater_diameter_m': crater_d,
        'damage_radii_m': damage_radii,
        'affected_areas_km2': areas_km2
    }
    return out

# ---------------- Mitigation -----------------

def apply_kinetic_impactor(sim_result, velocity_reduction_pct=10.0):
    """
    Simulate a kinetic impactor that reduces velocity by a percentage.
    velocity_reduction_pct: 0-100
    """
    inp = sim_result['input']
    new_velocity = inp['velocity_m_s'] * (1.0 - velocity_reduction_pct/100.0)
    return simulate_impact(inp['diameter_m'], new_velocity, density_kg_m3=inp['density_kg_m3'],
                           impact_angle_deg=inp['impact_angle_deg'], lat=inp['lat'], lon=inp['lon'])

def apply_nuclear_deflection(sim_result, energy_reduction_pct=50.0):
    """
    Model a nuclear option as directly reducing effective energy by a percent.
    We approximate by reducing velocity accordingly (since E ~ v^2).
    """
    inp = sim_result['input']
    reduction = energy_reduction_pct / 100.0
    # To reduce energy by 'reduction', scale velocity by sqrt(1 - reduction)
    factor = math.sqrt(max(0.0, 1.0 - reduction))
    new_velocity = inp['velocity_m_s'] * factor
    return simulate_impact(inp['diameter_m'], new_velocity, density_kg_m3=inp['density_kg_m3'],
                           impact_angle_deg=inp['impact_angle_deg'], lat=inp['lat'], lon=inp['lon'])

def apply_fragmentation(sim_result, fragment_count=3):
    """
    Approximate fragmentation: split mass into N fragments, each with reduced energy due to atmospheric breakup.
    We approximate the result by scaling energy down (mass distributed, some slows down).
    For simplicity, we model as effective velocity reduction depending on fragment_count.
    """
    inp = sim_result['input']
    # more fragments -> more atmospheric dispersal -> effective energy reduction
    factor = 1.0 / math.sqrt(fragment_count)  # crude approx
    new_velocity = inp['velocity_m_s'] * factor
    new_diameter = inp['diameter_m'] / (fragment_count ** (1/3))  # volume conserved
    return simulate_impact(new_diameter, new_velocity, density_kg_m3=inp['density_kg_m3'],
                           impact_angle_deg=inp['impact_angle_deg'], lat=inp['lat'], lon=inp['lon'])
