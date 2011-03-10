#!/usr/bin/env python
# EPIC.py
# Stephen Kerr 2010-12-13
# This file contains the main logic of the program and uses the constants from constants.py and
# functions from hydro_utils.py.
#
# The following is the preliminary logic that has been written in the Python language for the EPIC
# (Economic Positioning of Intake Calculator) program. The output from the following process gives
# both the pay back period and the cost/KW of a hydro scheme and chooses the optimum values of each.
# This allows a user to read off the two head values that correspond to these ecomomic indicators.
# The cost/diameter matrix for different pipe types is given in a Comma Separated Variable file
# which is passed as a parameter.

# Run with something like:
# ./EPIC.py --catchment_type 1 \
#            --slope 45 \
#            --catchment_length 13 \
#            --rainfall 1000 \
#            --evaporation 400 \
#            --catchment_area 1000000 \
#            --pipe_file pipes_0.csv \
#            --pvc_rn 80000 \
#            --grp_rn 80000 \
#            --di_rn 80000 \
#            --reliability 0.7 \
#            --flow_frac 0.5 \
#            --market_price 0.03 \
#            --interest 0.05 | less

from math import sin, cos, tan, ceil, pi
from math import radians as rad
from optparse import OptionParser
from prettytable import PrettyTable
import sys

from hydro_utils import *
from constants import *

### Take options {{{
usage = """
    EPIC ... some big helpful string for the user.
    Maybe Name and Copyright notice
"""
# Take the options from the command line. All are required.
parser = OptionParser(version='0.1', usage=usage)
parser.add_option('--verbose', dest='v', action='store_true', default=False,
                  help='Verbose output. Prints optimums for every head.')
parser.add_option('--catchment_area', dest='ca',
                  help='Total area of catchment upstream of powerhouse.')
parser.add_option('--catchment_type', dest='catch_type',
                  help='See writeup for different area types.', metavar='INT')
parser.add_option('--catchment_length', dest='cl',
                  help='The length from the powerhouse to the furthest point of the catchment area')
parser.add_option('--slope', dest='slope',
                  help='General slopiness of the pipe.')
parser.add_option('--rainfall', dest='aar',
                  help='Anticipated annual rainfall')
parser.add_option('--evaporation', dest='aae',
                  help='Anticipated annual evaporation')
parser.add_option('--pipe_file', dest='pipe_file',
                  help='PATH to file containing pipe costs.')
parser.add_option('--pvc_rn', dest='pvc_rn',
                  help='Renauld\'s number for PVC pipe.')
parser.add_option('--grp_rn', dest='grp_rn',
                  help='Renauld\'s number for Glass Reinforced Plastic pipe.')
parser.add_option('--di_rn', dest='di_rn',
                  help='Renauld\'s number for Ductile Iron pipe.')
parser.add_option('--reliability', dest='reliability',
                  help='Relability Factor')
parser.add_option('--flow_fraction', dest='flow_frac',
                  help='Fraction of the river we are allowed to take.')
parser.add_option('--market_price', dest='market_price',
                  help='Fluctuant value per kW in GBP')
parser.add_option('--interest', dest='interest',
                  help='Rate of interest charged on project loan.')
(opts, args) = parser.parse_args()

# Ensure passed parameters are the correct type
opts.ca = float(opts.ca)
opts.cl = float(opts.cl)
opts.slope = float(opts.slope)
opts.catch_type = int(opts.catch_type)
opts.aar = float(opts.aar)
opts.aae = float(opts.aae)
opts.pipe_file = str(opts.pipe_file)
opts.pvc_rn = float(opts.pvc_rn)
opts.grp_rn = float(opts.grp_rn)
opts.di_rn = float(opts.di_rn)
opts.reliability = float(opts.reliability)
opts.flow_frac = float(opts.flow_frac)
opts.market_price = float(opts.market_price)
opts.interest = float(opts.interest)

### }}} End of Take options

# Maximum height
max_H = tan(rad(opts.slope)) * opts.cl

# Read in pipe diameter/cost table from a comma separated values file
try:
    pipe_file = open(opts.pipe_file, 'r')
    pipe_string = pipe_file.read()
    pipe_file.close()
except:
    print 'Something went wrong with pipe file.'
    sys.exit(1)
pipe_table = []
i = 0
for line in pipe_string.splitlines():
    if i > 0:
        (diameter, pvc, di, grp) = line.split(',')
        table_line = [diameter, pvc, di, grp]
        pipe_table.append(table_line)
    i += 1

optimum_h_payback = []
lowest_payback_period = 99999999999999 # Big number that the period will never be higher than

optimum_h_cost_kw = []
lowest_cost_kw = 99999999999999 # Big number that the cost will never be higher than

for h in range(1, int(ceil(max_H))): ### for each head {{{
    if opts.v: print 'Head = %d' % h
    
    penstock_length = float(h) / sin(rad(opts.slope))
    Hz = float(h) / tan(rad(opts.slope))
    
    area_frac = get_area(opts.catch_type, opts.cl, opts.slope, Hz, opts.v)
    avail_ca = opts.ca * area_frac
    
    # Now that the area of the catchment area has been calculated
    catchment_vol = avail_ca * ((opts.aar - opts.aae) / 1000) # Divide by 1000 to put mm into meters
    avg_flow_rate = catchment_vol / (365 * 24 * 60 * 60) # In cumecs
    if opts.v: print '\tAverage flow rate = %(flow)s' % {'flow': avg_flow_rate}
    
    design_flow = avg_flow_rate * opts.flow_frac
            
    capacity_estimate = design_flow * h * HEP
    if capacity_estimate <= 100: FIT = GTHigh
    else: FIT = GTLow
    
    optimum = get_optimum_pipe(h,
                               pipe_table,
                               design_flow,
                               penstock_length,
                               FIT,
                               opts.pvc_rn,
                               opts.grp_rn,
                               opts.di_rn,
                               opts.reliability,
                               opts.market_price,
                               opts.interest,
                               opts.v)
        
    # 'optimum' now contains the lowest total cost diameter of pipe
    if opts.v: print '\tOptimum = ', optimum
    
    penstock_type = optimum[4]
    # Capital expenditure of penstock
    total_penstock_cost = optimum[2] / opts.interest
    if opts.v: print '\tTotal Penstock cost = %f' % total_penstock_cost
    
    head_loss = optimum[3]
    scheme_capacity = (h - head_loss) * design_flow * G * opts.reliability * DWater / 1000
    scheme_annual_revenue = scheme_capacity * (365 * 24) * (FIT + opts.market_price)
    if opts.v: print '\tScheme Annual Revenue = %f' % scheme_annual_revenue
    
    civil_cost = total_penstock_cost / PenFrac * CivFrac
    turbine_cost = total_penstock_cost * TurbFrac
    grid_connect_cost = total_penstock_cost / PenFrac * GridFrac
    
    total_project_cost = total_penstock_cost + civil_cost + turbine_cost + grid_connect_cost
    if opts.v: print '\tTotal Project Cost = %f' % total_project_cost
    
    scheme_payback_period = total_project_cost / scheme_annual_revenue
    if opts.v: print '\tScheme Payback Period = %f' % scheme_payback_period
    
    scheme_cost_per_kw = total_project_cost / scheme_capacity
    if opts.v: print '\tScheme Cost/kW = %f' % scheme_cost_per_kw
    
    if scheme_payback_period < lowest_payback_period:
        lowest_payback_period = scheme_payback_period
        optimum_h_payback = [h,
                             total_project_cost,
                             scheme_annual_revenue,
                             scheme_payback_period,
                             scheme_cost_per_kw,
                             penstock_type,
                             design_flow]
    
    if scheme_cost_per_kw < lowest_cost_kw:
        lowest_cost_kw = scheme_cost_per_kw
        optimum_h_cost_kw = [h,
                             total_project_cost,
                             scheme_annual_revenue,
                             scheme_payback_period,
                             scheme_cost_per_kw,
                             penstock_type,
                             design_flow]
### }}} End of for each head loop

### Print results {{{
# Now we have finished the calculations we can print the results in a table
results = PrettyTable(['Detail', 'Optimum Payback', 'Optimal kW'])
results.add_row(['Head', optimum_h_payback[0], optimum_h_cost_kw[0]])
results.add_row(['Project Cost', optimum_h_payback[1], optimum_h_cost_kw[1]])
results.add_row(['Project Revenue', optimum_h_payback[2], optimum_h_cost_kw[2]])
results.add_row(['Payback Period', optimum_h_payback[3], optimum_h_cost_kw[3]])
results.add_row(['Cost/kW', optimum_h_payback[4], optimum_h_cost_kw[4]])
results.add_row(['Penstock Type', optimum_h_payback[5], optimum_h_cost_kw[5]])
results.add_row(['Design Flow', optimum_h_payback[6], optimum_h_cost_kw[6]])
print results
#print 'Detail \t Optimum Payback \t Optimum kW'
#print 'Head \t %d \t %d' % (optimum_h_payback[0], optimum_h_cost_kw[0])
### }}} End of Print results






