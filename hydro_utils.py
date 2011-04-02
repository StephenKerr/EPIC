# hydro_utils.py
# Stephen Kerr 2010-12-13
# This file contains utility functions used by EPIC.py.
# This allows EPIC to be easier to read
from constants import *
from math import pi, sqrt, log

def get_area(catch_type, cl, Hz, verbose): # {{{
    '''
    get_area() returns the fractional area of a catchment above the intake.
    Catchment type is an integer which indicates the shape.
    1: Triangle
    2: Rectangle
    3: Pentagon
    4: Hexagon
    
    cl - catchment length
    Hz - Horizontal distance upstream from powerhouse
    '''
    
    if catch_type == 1: # Triangle
        area = ((cl**2 * 0.5) - (Hz**2 * 0.5)) / (cl**2 * 0.5)
        if verbose: print '\tcatch 1'
        if verbose: print '\tArea = %(a)f' % {'a': area}
    # End of Triangle
    
    elif catch_type == 2: # Rectangle c by c/2
        area = ((cl**2 * 0.5) - (Hz * cl * 0.5)) / (cl**2 * 0.5)
        if verbose: print '\tcatch 2'
        if verbose: print '\tArea = %(a)f' % {'a': area}
    # End of Rectangle
    
    elif catch_type == 3: # Pentagon
        
        if Hz <= cl / 2: # Intake is within rectangular section boundary
            area = ((3 * cl**2 / 8) - (Hz * cl * 0.5)) / (3 * cl**2 / 8)
            if verbose: print '\tcatch 3.1'
            if verbose: print '\tArea = %(a)f' % {'a': area}
        
        else: # Intake is past rectangular section boundary
            area = ((3 * cl**2 / 8) - (cl**2 / 4) - ((cl**2 / 8) - (cl - Hz)**2 * 0.5)) / (3 * cl**2 / 8)
            if verbose: print '\tcatch 3.2'
            if verbose: print '\tArea = %(a)f' % {'a': area}
    # End of Pentagon
    
    
    elif catch_type == 4: # Hexagon
        
        if Hz <= cl / 3:
            area = ((2 * cl**2 / 9) - (Hz**2 * 0.5)) / (2 * cl**2 / 9)
            if verbose: print '\tcatch 4.1'
            if verbose: print '\tArea = %(a)f' % {'a': area}
        
        elif (cl / 3) < Hz and Hz <= (2 * cl / 3):
            area = ((2 * cl**2 / 9) - (cl**2 / 18) - ((Hz - cl / 3) * (cl / 3))) / (2 * cl**2 / 9)
            if verbose: print '\tcatch 4.2'
            if verbose: print '\tArea = %(a)f' % {'a': area}
        
        else:
            area = ((cl - Hz)**2 * 0.5) / (2 * cl**2 / 9)
            if verbose: print '\tcatch 4.3'
            if verbose: print '\tArea = %(a)f' % {'a': area}
    # End of Hexagon
    
    else:
        print 'We don\'t have that catchment type'
        sys.exit(1) # We don't have that catchment type
    
    return area
    # }}} End of get_area

def get_scheme_capacity(head        = 0.0, # {{{
                        head_loss   = 0.0,
                        Q           = 0.0,
                        efficiency  = 0.0):
    '''
    This returns the capacity of a scheme in kW
    '''
    c = (head - head_loss) * Q * G * efficiency * DWater / 1000
    return c
    # }}} End of get_scheme_capacity

def get_scheme_annual_revenue(C     = 0.0, # {{{
                              FIT   = 0.0,
                              P     = 0.0,
                              R     = 0.0,
                              interest = 0.0,
                              total = 0.0):
    '''
    This returns the annual revenue for a scheme in GBP.
    '''
    # The whole scheme is on a loan which has annual servicing costs which must
    #   be taken from the annual revenue.
    r = C * (365 * 24) * (FIT + P) * R - (interest * total)
    return r
    # }}} End of get_scheme_capacity

def get_head_loss(F=0.0, L=0.0, D=0.0, Q=0.0): # {{{
    '''
    F = Friction Coefficient
    L = Penstock Length
    Q = Design Flow
    D = Diameter
    '''
    h = F * L / D * Q**2 / (2 * G * (pi * (D / 2)**2 )**2)
    return h
    # }}} End of get_head_loss

def get_renaulds_number(Q=0.0, D=0.0): # {{{
    '''
    Q = Design Flow
    D = Diameter
    '''
    area_of_pipe = pi * (D / 2)**2
    r = (Q * D) / (area_of_pipe * V_H2O)
    return r
    # }}} End of get_friction_coeff

def get_friction_coeff(Q=0.0, D=0.0, E=0.0, M=''): # {{{
    '''
    Q = Design Flow
    D = Diameter
    E = Surface Roughness of pipe
    M = Material of pipe (PVC, DI, GRP)
    '''
    f = 0.0
    Rn = get_renaulds_number(Q = Q, D = D)

    if   M == 'PVC':
        # This friction coeff comes from the Blasius equation
        f = 0.0079 * Rn**0.25
    
    elif M == 'DI' or M == 'GRP':
        area_of_pipe = pi * (D / 2)**2
        
        seed = 1
        iterations = 100

        fl = []
        fl.append(float(seed))
        for i in range(1, iterations):
            f = ((1) - (-2 * log((  (E / 3.7 * D) + (2.51 / (Rn * sqrt(fl[i-1])))   ), 10)))**2
            fl.append(f)

    return f
    # }}} End of get_friction_coeff
    
def get_optimum_pipe_for_head(head               = 0.0, # {{{
                              pipe_table         = [],
                              design_flow        = 0.0,
                              penstock_length    = 0.0,
                              FIT                = 0.0,
                              efficiency         = 0.0,
                              market_price       = 0.0,
                              interest           = 0.0,
                              verbose            = True):
    '''
    This iterates through the entries in pipe_table and returns the most cost efficient diameter,
      material, and its associated cost.
    '''
    optimum_pipe = {'diameter'              : 0.0,
                    'material'              : '',
                    'head_loss'             : 0.0,
                    'annual_head_loss_cost' : 0.0,
                    'annual_capital_cost'   : 0.0,
                    'total_annual_cost'     : 999999999.9} # Total Annual Cost is just the sum
                                                   #   of head loss and capital costs.
    
    for (diameter, pvc, di, grp) in pipe_table: # {{{
        diameter    = float(diameter)
        pvc         = float(pvc)
        di          = float(di)
        grp         = float(grp)
        total_annual_cost = 0

        pipe = {'diameter'              : diameter,
                'material'              : '',
                'head_loss'             : 0.0,
                'annual_head_loss_cost' : 0.0,
                'annual_capital_cost'   : 0.0,
                'total_annual_cost'     : 0.0} # Total Annual Cost is just the sum
                                               #   of head loss and capital costs.

        # This condition means that if PVC is available (according to head and diameter constraints)
        #   then always use it.
        if head <= PVC_Constraint_MaxHead and diameter <= PVC_Constraint_MaxDiameter:
            # PVC {{{
            annual_capital_cost_pvc = penstock_length * pvc * interest

            friction_coeff = get_friction_coeff(Q = design_flow, D = diameter, M = 'PVC')
            
            head_loss_pvc = get_head_loss(F = friction_coeff, L = penstock_length, D = diameter, Q = design_flow)
            
            annual_head_loss_cost_pvc = head_loss_pvc * design_flow * G * efficiency * (365 * 24) * (FIT + market_price)

            # }}} End of PVC
            total_annual_cost = annual_capital_cost_pvc + annual_head_loss_cost_pvc
            pipe['annual_capital_cost']     = annual_capital_cost_pvc
            pipe['annual_head_loss_cost']   = annual_head_loss_cost_pvc
            pipe['head_loss']               = head_loss_pvc
            pipe['material']                = 'PVC'
        
        else:
            # Ductile Iron {{{
            annual_capital_cost_di = penstock_length * di * interest

            friction_coeff = get_friction_coeff(Q = design_flow, D = diameter, E = E_DI, M = 'DI')
            
            head_loss_di = get_head_loss(F = friction_coeff, L = penstock_length, D = diameter, Q = design_flow)
            
            annual_head_loss_cost_di = head_loss_di * design_flow * G * efficiency * (365 * 24) * (FIT + market_price)

            total_annual_cost_di = annual_capital_cost_di + annual_head_loss_cost_di
            # }}} End of Ductile Iron
            # Glass Reinforced Plastic {{{
            annual_capital_cost_grp = penstock_length * grp * interest
            
            friction_coeff = get_friction_coeff(Q = design_flow, D = diameter, E = E_GRP, M = 'GRP')
            
            head_loss_grp = get_head_loss(F = friction_coeff, L = penstock_length, D = diameter, Q = design_flow)
            
            annual_head_loss_cost_grp = head_loss_grp * design_flow * G * efficiency * (365 * 24) * (FIT + market_price)

            total_annual_cost_grp = annual_capital_cost_grp + annual_head_loss_cost_grp
            # }}} End of Glass Reinforced Plastic

            if total_annual_cost_grp > total_annual_cost_di:
                total_annual_cost = total_annual_cost_di
                pipe['annual_capital_cost']     = annual_capital_cost_di
                pipe['annual_head_loss_cost']   = annual_head_loss_cost_di
                pipe['head_loss']               = head_loss_di
                pipe['material']                = 'DI'
            else:
                total_annual_cost = total_annual_cost_grp
                pipe['annual_capital_cost']     = annual_capital_cost_grp
                pipe['annual_head_loss_cost']   = annual_head_loss_cost_grp
                pipe['head_loss']               = head_loss_grp
                pipe['material']                = 'GRP'
        
        # Now we have the total_annual_cost for a given head/diameter
        pipe['total_annual_cost'] = total_annual_cost

        # Our preferred pipe for this diameter is now chosen
        
        # Now we get the preferred pipe for the given head
        #   by choosing from a range of pipes of different diameters.
        if pipe['total_annual_cost'] < optimum_pipe['total_annual_cost']:
            optimum_pipe = pipe

        # }}} End of for each diameter

    return optimum_pipe
    # }}} End of get_optimum_pipe 

# Flow Duration Curve {{{
# Flow duration curve take from table in "Report No. 126 - Hydrology Of Soil
# Types: A Hydrologically Based Classification Of The Soils In The United Kingdom",
# Table 4.7, page 69.
flow_duration_curve = [
                       0.2049,
                       0.2269,
                       0.2510,
                       0.2786,
                       0.3082,
                       0.3411,
                       0.3781,
                       0.4182,
                       0.4510,
                       0.4864,
                       0.5246,
                       0.5657,
                       0.6101,
                       0.6579,
                       0.7100,
                       0.7657,
                       0.8260,
                       0.8991,
                       0.9786,
                       1.0649
                      ]
# }}} End of Flow Duration Curve
