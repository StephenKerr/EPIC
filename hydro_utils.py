# hydro_utils.py
# Stephen Kerr 2010-12-13
# This file contains utility functions used by EPIC.py.
# This allows EPIC to be easier to read
from constants import *
from math import pi

def get_area(catch_type, cl, slope, Hz, verbose): # {{{
    '''
    get_area() returns the fractional area of a catchment above the intake.
    Catchment type is an integer which indicates the shape.
    1: Triangle
    2: Rectangle
    3: Pentagon
    4: Hexagon
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
    
def get_optimum_pipe(h, pipe_table, design_flow, penstock_length, FIT, pvc_rn, grp_rn, di_rn, reliability, market_price, interest, verbose): # {{{
    '''
    get_optimum_pipe() returns a list containing the optimum type of pipe for a given head.
    '''
    optimum = []
    lowest_total = 99999999999999 # Big number that the cost will never be higher than
    if h < 120: # TODO Explain where 120 comes from
        if verbose: print '\tHead is less than 120 so use PVC'
        for (diameter, pvc, di, grp) in pipe_table:
            diameter = float(diameter)
            pvc = float(pvc)
            grp = float(grp)
            di = float(di)
            # TODO  Explain where this formula comes from
            head_loss_pvc = (
                         (((4 * RnFric / (pvc_rn)**0.25) * penstock_length) / diameter) *
                         (design_flow**2 / (2 * G * (pi * (diameter / 2)**2)**2))
                        )
            
            # Annual Energy Loss Cost
            aelc = design_flow * head_loss_pvc * reliability * G * DWater * (365 * 24) * (FIT + market_price)
            # Annual Construction Cost of Penstock (from interest)
            accp = pvc * penstock_length * interest
            total = aelc + accp
            
            # Update the lowest total
            if total < lowest_total:
                lowest_total = total
                optimum = [diameter, aelc, accp, head_loss_pvc, 'PVC']
    
    else:
        if verbose: print '\tHead is greater than 120 so use either Glass Reinforced Plastic or Ductile Iron'
        for (diameter, pvc, di, grp) in pipe_table:
            diameter = float(diameter)
            pvc = float(pvc)
            grp = float(grp)
            di = float(di)
            # TODO Explain where this formula comes from
            head_loss_grp = (
                         (((4 * RnFric / (grp_rn)**0.25) * penstock_length) / diameter) *
                         (design_flow**2 / (2 * G * (pi * (diameter / 2)**2)**2))
                        )
            head_loss_di = (
                         (((4 * RnFric / (di_rn)**0.25) * penstock_length) / diameter) *
                         (design_flow**2 / (2 * G * (pi * (diameter / 2)**2)**2))
                        )
            
            # Annual Energy Loss Cost
            aelc_grp = design_flow * head_loss_grp * reliability * G * DWater * (365 * 24) * (FIT + market_price)
            # Annual Construction Cost of Penstock (from interest)
            accp_grp = grp * penstock_length * interest
            total_grp = aelc_grp + accp_grp
            if verbose: print '\tFor diameter=%f, total cost of GRP penstock is: %f' % (diameter, total_grp)
            
            # Annual Energy Loss Cost
            aelc_di = design_flow * head_loss_di * reliability * G * DWater * (365 * 24) * (FIT + market_price)
            # Annual Construction Cost of Penstock (from interest)
            accp_di = di * penstock_length * interest
            total_di = aelc_di + accp_di
            if verbose: print '\tFor diameter=%f, total cost of DI penstock is: %f' % (diameter, total_di)
            
            # Update the lowest total
            if total_grp < lowest_total:
                lowest_total = total_grp
                optimum = [diameter, aelc_grp, accp_grp, head_loss_grp, 'GRP']
            
            if total_di < lowest_total:
                lowest_total = total_di
                optimum = [diameter, aelc_di, accp_di, head_loss_di, 'DI']
    
    return optimum
    # }}} End of get_optimum_pipe 
