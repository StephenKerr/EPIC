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
#            --flow_duration_curve 5 \
#            --precipitation 1000 \
#            --potential_evaporation 400 \
#            --catchment_area 1000000 \
#            --pipe_file pipes_0.csv \
#            --reliability 0.7 \
#            --efficiency 0.82 \
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
parser.add_option('--flow_duration_curve', dest='fdc_index',
                  help='Flow duration curve selected by user based on knowledge of catchment geology.')
parser.add_option('--slope', dest='slope',
                  help='General slopiness of the pipe.')
parser.add_option('--precipitation', dest='aar',
                  help='Anticipated annual rainfall')
parser.add_option('--potential_evaporation', dest='aae',
                  help='Anticipated annual evaporation')
parser.add_option('--pipe_file', dest='pipe_file',
                  help='PATH to file containing pipe costs.')
parser.add_option('--reliability', dest='reliability',
                  help='Relability Factor')
parser.add_option('--efficiency', dest='efficiency',
                  help='Efficiency. Normally 0.82', default=0.82)
parser.add_option('--market_price', dest='market_price',
                  help='Fluctuant value per kW in GBP')
parser.add_option('--interest', dest='interest',
                  help='Rate of interest charged on project loan.')
(opts, args) = parser.parse_args()

# Ensure passed parameters are the correct type
opts.ca = float(opts.ca)
opts.cl = float(opts.cl)
opts.fdc_index = int(opts.fdc_index) - 1 # Minus one for array access.
opts.slope = float(opts.slope)
opts.catch_type = int(opts.catch_type)
opts.aar = float(opts.aar)
opts.aae = float(opts.aae)
opts.pipe_file = str(opts.pipe_file)
opts.reliability = float(opts.reliability)
opts.efficiency = float(opts.efficiency)
opts.market_price = float(opts.market_price)
opts.interest = float(opts.interest)

### }}} End of Take options

# Maximum height
max_H = tan(rad(opts.slope)) * opts.cl

# Get Pipe Table {{{
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
# }}} Get Pipe Table

# Potential evaporation calculated from Layman's Guidebook - On How
# To Develop A Small Hydro Site, Chapter 3, page 69.
if opts.aar < 850:
    opts.aae = (0.00061 * aar + 0.475) * aae

# There are four optimum schemes to be chosen, each for a different economic factor.
# Cost/kW, Payback Period, Annual ROI, Annual Revenue
# Initialise optimum schemes {{{
scheme_cost_per_kw      = {'diameter'              : 0.0,
                           'material'              : '',
                           'head'                  : 0.0,
                           'capacity'              : 0.0,
                           'project_cost'          : 0.0,
                           'cost_per_kw'           : 999999999.9,
                           'payback_period'        : 999999999.9,
                           'annual_roi'            : 0.0,
                           'annual_revenue'        : 0.0}

scheme_payback_period   = {'diameter'              : 0.0,
                           'material'              : '',
                           'head'                  : 0.0,
                           'capacity'              : 0.0,
                           'project_cost'          : 0.0,
                           'cost_per_kw'           : 999999999.9,
                           'payback_period'        : 999999999.9,
                           'annual_roi'            : 0.0,
                           'annual_revenue'        : 0.0}

scheme_annual_roi       = {'diameter'              : 0.0,
                           'material'              : '',
                           'head'                  : 0.0,
                           'capacity'              : 0.0,
                           'project_cost'          : 0.0,
                           'cost_per_kw'           : 999999999.9,
                           'payback_period'        : 999999999.9,
                           'annual_roi'            : 0.0,
                           'annual_revenue'        : 0.0}

scheme_annual_revenue   = {'diameter'              : 0.0,
                           'material'              : '',
                           'head'                  : 0.0,
                           'capacity'              : 0.0,
                           'project_cost'          : 0.0,
                           'cost_per_kw'           : 999999999.9,
                           'payback_period'        : 999999999.9,
                           'annual_roi'            : 0.0,
                           'annual_revenue'        : 0.0}
# }}} Initialise optimum schemes

for h in range(1, int(ceil(max_H))): ### for each head {{{
    if opts.v: print 'Head = %d' % h
    
    penstock_length = float(h) / sin(rad(opts.slope))
    Hz = float(h) / tan(rad(opts.slope))
    
    area_frac = get_area(opts.catch_type, opts.cl, Hz, opts.v)
    avail_ca = opts.ca * area_frac
    
    # Now that the area of the catchment area has been calculated
    # catchment_vol is the annual total volume of precipitation which enters the catchment.
    catchment_vol = avail_ca * ((opts.aar - opts.aae) / 1000) # Divide by 1000 to put mm into meters
    avg_flow_rate = catchment_vol / (365 * 24 * 60 * 60) # In cumecs
    if opts.v: print '\tAverage flow rate = %(flow)s' % {'flow': avg_flow_rate}
    
    design_flow = avg_flow_rate * flow_duration_curve[opts.fdc_index]
    # The Hydro Estimation Parameter (HEP) is just a number used to quickly estimate the
    #   installed power capacity in kW.
    # It comes from a combination of G(9.81) and an efficiency of around 82%.
    capacity_estimate = design_flow * h * HEP
    if capacity_estimate <= 100: FIT = GTHigh
    else: FIT = GTLow
    
    # TODO We were doing this before we went to bed.
    pipe = get_optimum_pipe_for_head(head            = h,
                                     pipe_table      = pipe_table,
                                     design_flow     = design_flow,
                                     penstock_length = penstock_length,
                                     FIT             = FIT,
                                     efficiency      = opts.efficiency,
                                     market_price    = opts.market_price, 
                                     interest        = opts.interest,
                                     verbose         = opts.v)
        
    if opts.v: print '\tOptimum pipe for this head = ', pipe
    
    # Capital expenditure of penstock
    total_penstock_cost = pipe['annual_capital_cost'] / opts.interest
    if opts.v: print '\tTotal Penstock cost = %f' % total_penstock_cost
    
    # The total project cost has quite a predicable breakdown for hydro schemes.
    # Therefore the rough fraction is stored as a constant.
    total_project_cost = total_penstock_cost / PenFrac
    if opts.v: print '\tTotal Project Cost = %f' % total_project_cost
    
    capacity = get_scheme_capacity(head = h,
                                   head_loss = pipe['head_loss'],
                                   Q = design_flow,
                                   efficiency = opts.efficiency)
    
    annual_revenue = get_scheme_annual_revenue(C = capacity,
                                               FIT = FIT,
                                               P = opts.market_price,
                                               R = opts.reliability,
                                               interest = opts.interest,
                                               total = total_project_cost)
    
    if opts.v: print '\tScheme Annual Revenue = %f' % annual_revenue
    

    # The payback period, cost/kW and return are the main economic factors of a scheme.
    payback_period = total_project_cost / annual_revenue
    if opts.v: print '\tScheme Payback Period = %f' % payback_period
    
    cost_per_kw = total_project_cost / capacity
    if opts.v: print '\tScheme Cost/kW = %f' % cost_per_kw

    annual_return_on_investment = annual_revenue / total_project_cost * 100
    if opts.v: print '\tScheme annual ROI = %f' % annual_return_on_investment 
    
    # Now we have all the desired economic factors we can choose the optimum scheme
    #   for each.
    if cost_per_kw < scheme_cost_per_kw['cost_per_kw']: # {{{
        scheme_cost_per_kw['diameter']          = pipe['diameter']
        scheme_cost_per_kw['material']          = pipe['material']
        scheme_cost_per_kw['head']              = h
        scheme_cost_per_kw['capacity']          = capacity
        scheme_cost_per_kw['project_cost']      = total_project_cost
        scheme_cost_per_kw['cost_per_kw']       = cost_per_kw
        scheme_cost_per_kw['payback_period']    = payback_period
        scheme_cost_per_kw['annual_roi']        = annual_return_on_investment
        scheme_cost_per_kw['annual_revenue']    = annual_revenue
        # }}} End of Cost/kW
    
    if payback_period < scheme_payback_period['payback_period']: # {{{
        scheme_payback_period['diameter']       = pipe['diameter']
        scheme_payback_period['material']       = pipe['material']
        scheme_payback_period['head']           = h
        scheme_payback_period['capacity']       = capacity
        scheme_payback_period['project_cost']   = total_project_cost
        scheme_payback_period['cost_per_kw']    = cost_per_kw
        scheme_payback_period['payback_period'] = payback_period
        scheme_payback_period['annual_roi']     = annual_return_on_investment
        scheme_payback_period['annual_revenue'] = annual_revenue
        # }}} End of Payback Period
    
    if annual_return_on_investment > scheme_payback_period['annual_roi']: # {{{
        scheme_annual_roi['diameter']           = pipe['diameter']
        scheme_annual_roi['material']           = pipe['material']
        scheme_annual_roi['head']               = h
        scheme_annual_roi['capacity']           = capacity
        scheme_annual_roi['project_cost']       = total_project_cost
        scheme_annual_roi['cost_per_kw']        = cost_per_kw
        scheme_annual_roi['payback_period']     = payback_period
        scheme_annual_roi['annual_roi']         = annual_return_on_investment
        scheme_annual_roi['annual_revenue']     = annual_revenue
        # }}} End of Annual ROI
    
    if annual_revenue > scheme_payback_period['annual_revenue']: # {{{
        scheme_annual_revenue['diameter']       = pipe['diameter']
        scheme_annual_revenue['material']       = pipe['material']
        scheme_annual_revenue['head']           = h
        scheme_annual_revenue['capacity']       = capacity
        scheme_annual_revenue['project_cost']   = total_project_cost
        scheme_annual_revenue['cost_per_kw']    = cost_per_kw
        scheme_annual_revenue['payback_period'] = payback_period
        scheme_annual_revenue['annual_roi']     = annual_return_on_investment
        scheme_annual_revenue['annual_revenue'] = annual_revenue
        # }}} End of Annual Revenue
        
### }}} End of for each head loop




####
##### Other costs are related to the cost of the capital expenditure of the penstock.
##### This is fairly predictable for hydro schemes so the relevant proportions
#####   of the total project cost are defined in constants.
####
##### The civil cost encompasses all costs associated with building the plant.
####civil_cost              = total_penstock_cost / PenFrac * CivFrac
####
##### The electromechanical cost is the cost of buying the turbine, generator, transformer,
#####   and related equipment.
####electromechanical_cost  = total_penstock_cost * TurbFrac
####
##### The grid connection cost
####grid_connect_cost       = total_penstock_cost / PenFrac * GridFrac
####



### Print results {{{
# Now we have finished the calculations we can print the results in a table
results = PrettyTable(['Detail',
                       'Optimum Cost/kW',
                       'Optimum Payback',
                       'Optimum Revenue',
                       'Optimal ROI'])
results.add_row(['Diameter',
                 scheme_cost_per_kw['diameter'],
                 scheme_payback_period['diameter'],
                 scheme_annual_revenue['diameter'],
                 scheme_annual_roi['diameter']])
results.add_row(['Material',
                 scheme_cost_per_kw['material'],
                 scheme_payback_period['material'],
                 scheme_annual_revenue['material'],
                 scheme_annual_roi['material']])
results.add_row(['Head',
                 scheme_cost_per_kw['head'],
                 scheme_payback_period['head'],
                 scheme_annual_revenue['head'],
                 scheme_annual_roi['head']])
results.add_row(['Capacity',
                 scheme_cost_per_kw['capacity'],
                 scheme_payback_period['capacity'],
                 scheme_annual_revenue['capacity'],
                 scheme_annual_roi['capacity']])
results.add_row(['Project Cost',
                 scheme_cost_per_kw['project_cost'],
                 scheme_payback_period['project_cost'],
                 scheme_annual_revenue['project_cost'],
                 scheme_annual_roi['project_cost']])
results.add_row(['Cost/kW',
                 scheme_cost_per_kw['cost_per_kw'],
                 scheme_payback_period['cost_per_kw'],
                 scheme_annual_revenue['cost_per_kw'],
                 scheme_annual_roi['cost_per_kw']])
results.add_row(['Payback Period',
                 scheme_cost_per_kw['payback_period'],
                 scheme_payback_period['payback_period'],
                 scheme_annual_revenue['payback_period'],
                 scheme_annual_roi['payback_period']])
results.add_row(['Annual ROI',
                 scheme_cost_per_kw['annual_roi'],
                 scheme_payback_period['annual_roi'],
                 scheme_annual_revenue['annual_roi'],
                 scheme_annual_roi['annual_roi']])
results.add_row(['Annual Revenue',
                 scheme_cost_per_kw['annual_revenue'],
                 scheme_payback_period['annual_revenue'],
                 scheme_annual_revenue['annual_revenue'],
                 scheme_annual_roi['annual_revenue']])
print results
#print 'Detail \t Optimum Payback \t Optimum kW'
#print 'Head \t %d \t %d' % (optimum_h_payback[0], optimum_h_cost_kw[0])
### }}} End of Print results






