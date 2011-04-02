# constants.py
# Stephen Kerr 2010-12-13
# This file contains constants which are used throughout the calculations

GTHigh  = 0.17      # Generation tarrif in GBP (high)
GTLow   = 0.135     # Generation tarrif in GBP (low)
G       = 9.81      # Gravity
V_H2O   = 10**-6    # Kinematic Viscosity of Water
E_PVC   = 0.003     # Suface Roughness of Poly Vinyl Chloride
E_DI    = 0.15      # Suface Roughness of Ductile Iron
E_GRP   = 0.029     # Surface Roughness of Glass Reinforced Plastic
DWater  = 1000      # Density of water
RnFric  = 0.079     # To convert a Renauld's number into a friction factor
HEP     = 8.0       # Hydro Estimation Parameter

# These fractions must add up to 1.0
PenFrac = 0.2   # Average fraction of project cost which is from the penstock TODO Explain
CivFrac = 0.5   # 
TurbFrac = 0.2  # 
GridFrac = 0.1  # 
# assert int(PenFrac + CivFrac + TurbFrac + GridFrac) == 1, 'Fractions of cost do not add up to 1.0: %s' % int(PenFrac + CivFrac + TurbFrac + GridFrac)

# PVC can only be used under certain conditions
PVC_Constraint_MaxHead     = 120    # Meters
PVC_Constraint_MaxDiameter = 0.5    # Meters

