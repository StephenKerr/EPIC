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
#            --heads 50,100 \
#            --plot annual_revenue,capacity \
#            --interest 0.05 | less

from math import sin, cos, tan, ceil, pi
from math import radians as rad
from optparse import OptionParser
from prettytable import PrettyTable
import sys
import matplotlib.pyplot as p
import datetime

# other EPIC files
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
parser.add_option('--plots', dest='plots',
                  help='Plots to make.')
parser.add_option('--heads', dest='heads',
                  help='Head values to test.')
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
if opts.plots: opts.plots = str(opts.plots)
if opts.heads: opts.heads = str(opts.heads)

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

# There are optimum schemes to be chosen, each for a different economic factor.
# Cost/kW, Payback Period, Annual ROI, Annual Revenue, Capacity
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

scheme_capacity         = {'diameter'              : 0.0,
                           'material'              : '',
                           'head'                  : 0.0,
                           'capacity'              : 0.0,
                           'project_cost'          : 0.0,
                           'cost_per_kw'           : 999999999.9,
                           'payback_period'        : 999999999.9,
                           'annual_roi'            : 0.0,
                           'annual_revenue'        : 0.0}
# }}} Initialise optimum schemes

# If no heads are specified then just compare all possible heads up to the maximum
if opts.plots:
    plots = opts.plots.split(',')

# If no heads are specified then just compare all possible heads up to the maximum
if opts.heads:
    heads = str(opts.heads).split(',')
    head_schemes = []
    for i, h in enumerate(heads):
        heads[i] = int(h)
        if heads[i] > max_H:
            print 'Error: Head is too large for catchment area. Exiting'
            sys.exit(1)

else:
    heads = range(1, int(ceil(max_H)))

# Initialise plot axis {{{
x_axis = []
penstock_length_y_axis = []
avg_flow_rate_y_axis = []
design_flow_y_axis = []
fit_y_axis = []
capacity_y_axis = []
total_penstock_cost_y_axis = []
total_project_cost_y_axis = []
annual_revenue_y_axis = []
payback_period_y_axis = []
cost_per_kw_y_axis = []
annual_roi_y_axis = []
# }}} End of Initialise plot axis

for h in heads: ### for each head {{{
    if opts.v: print 'Head = %d' % h
    x_axis.append(h)
    
    # penstock_length {{{
    penstock_length = float(h) / sin(rad(opts.slope))
    penstock_length_y_axis.append(penstock_length)
    Hz = float(h) / tan(rad(opts.slope))
    # }}} penstock_length
    
    # Flow rate {{{
    area_frac = get_area(opts.catch_type, opts.cl, Hz, opts.v)
    avail_ca = opts.ca * area_frac
    
    # Now that the area of the catchment area has been calculated
    # catchment_vol is the annual total volume of precipitation which enters the catchment.
    catchment_vol = avail_ca * ((opts.aar - opts.aae) / 1000) # Divide by 1000 to put mm into meters
    avg_flow_rate = catchment_vol / (365 * 24 * 60 * 60) # In cumecs
    if opts.v: print '\tAverage flow rate = %(flow)s' % {'flow': avg_flow_rate}
    avg_flow_rate_y_axis.append(avg_flow_rate)
    # }}} Flow rate
    
    # Design flow {{{
    design_flow = avg_flow_rate * flow_duration_curve[opts.fdc_index]
    if opts.v: print '\tDesign flow = %(flow)s' % {'flow': design_flow}
    design_flow_y_axis.append(design_flow)
    # }}} End of Design flow

    # FIT {{{
    # The Hydro Estimation Parameter (HEP) is just a number used to quickly estimate the
    #   installed power capacity in kW.
    # It comes from a combination of G(9.81) and an efficiency of around 82%.
    capacity_estimate = design_flow * h * HEP
    if capacity_estimate <= 100: FIT = GTHigh
    else: FIT = GTLow
    fit_y_axis.append(FIT)
    # }}} FIT
    
    # Get optimum pipe {{{
    pipe = get_optimum_pipe_for_head(head            = h,
                                     pipe_table      = pipe_table,
                                     design_flow     = design_flow,
                                     penstock_length = penstock_length,
                                     FIT             = FIT,
                                     efficiency      = opts.efficiency,
                                     market_price    = opts.market_price, 
                                     interest        = opts.interest,
                                     verbose         = False)
    if opts.v: print '\tOptimum pipe for this head = ', pipe
    # }}} End of Get optimum pipe
    
    # capacity {{{
    capacity = get_scheme_capacity(head = h,
                                   head_loss = pipe['head_loss'],
                                   Q = design_flow,
                                   efficiency = opts.efficiency)
    if opts.v: print '\tCapacity = %f' % capacity
    capacity_y_axis.append(capacity)
    #if capacity < 15: continue # 15kW is the minimum threshold for a small hydroscheme (rather than a pico,
                               #   which has different equations relating to cost, and methodologies associated).
    # }}} End of capacity
    
    # Total project cost {{{
    # Capital expenditure of penstock
    total_penstock_cost = pipe['annual_capital_cost'] / opts.interest
    if opts.v: print '\tTotal Penstock cost = %f' % total_penstock_cost
    total_penstock_cost_y_axis.append(total_penstock_cost)
    
    # The total project cost has quite a predicable breakdown for hydro schemes.
    # Therefore the rough fraction is stored as a constant.
    total_project_cost = total_penstock_cost / PenFrac
    if opts.v: print '\tTotal Project Cost = %f' % total_project_cost
    total_project_cost_y_axis.append(total_project_cost)
    # }}} End of Total project cost
    
    # Annual Revenue {{{
    annual_revenue = get_scheme_annual_revenue(C = capacity,
                                               FIT = FIT,
                                               P = opts.market_price,
                                               R = opts.reliability,
                                               interest = opts.interest,
                                               total = total_project_cost)
    
    if opts.v: print '\tScheme Annual Revenue = %f' % annual_revenue
    annual_revenue_y_axis.append(annual_revenue)
    # }}} Annual Revenue

    # Payback period {{{
    # The payback period, cost/kW and return are the main economic factors of a scheme.
    payback_period = total_project_cost / annual_revenue
    if opts.v: print '\tScheme Payback Period = %f' % payback_period
    payback_period_y_axis.append(payback_period)
    # }}} Payback period
    
    # Cost/kW {{{
    cost_per_kw = total_project_cost / capacity
    if opts.v: print '\tScheme Cost/kW = %f' % cost_per_kw
    cost_per_kw_y_axis.append(cost_per_kw)
    # }}} Cost/kW

    # Annual RIO {{{
    annual_return_on_investment = annual_revenue / total_project_cost * 100
    if opts.v: print '\tScheme annual ROI = %f' % annual_return_on_investment 
    annual_roi_y_axis.append(annual_return_on_investment)
    # }}} Annual RIO
    
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
    
    if payback_period > 0 and payback_period < scheme_payback_period['payback_period']: # {{{
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
    
    if annual_return_on_investment > scheme_annual_roi['annual_roi']: # {{{
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
    
    if annual_revenue > scheme_annual_revenue['annual_revenue']: # {{{
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
    
    if capacity > scheme_capacity['capacity']: # {{{
        scheme_capacity['diameter']       = pipe['diameter']
        scheme_capacity['material']       = pipe['material']
        scheme_capacity['head']           = h
        scheme_capacity['capacity']       = capacity
        scheme_capacity['project_cost']   = total_project_cost
        scheme_capacity['cost_per_kw']    = cost_per_kw
        scheme_capacity['payback_period'] = payback_period
        scheme_capacity['annual_roi']     = annual_return_on_investment
        scheme_capacity['annual_revenue'] = annual_revenue
        # }}} End of Capacity
    
    if opts.heads:
        head_scheme = {'diameter'       :   pipe['diameter'],
                       'material'       :   pipe['material'],
                       'head'           :   h,
                       'capacity'       :   capacity,
                       'project_cost'   :   total_project_cost,
                       'cost_per_kw'    :   cost_per_kw,
                       'payback_period' :   payback_period,
                       'annual_roi'     :   annual_return_on_investment,
                       'annual_revenue' :   annual_revenue}
        head_schemes.append(head_scheme)

### }}} End of for each head loop

# Print results {{{
# Now we have finished the calculations we can print the results in a table
results = PrettyTable(['Scheme',
                       'Head (m)',
                       'Mat',
                       'Diam (m)',
                       'Cap (kW)',
                       'Rev/Yr (GBP)',
                       'Proj Cost (GBP)',
                       'Payback Period (Yr)',
                       'Cost/kW (GBP/kW)'])

results.add_row(['Optimum Capacity',
                 scheme_capacity['head'],
                 scheme_capacity['material'],
                 '%.02f' % scheme_capacity['diameter'],
                 '%.02f' % scheme_capacity['capacity'],
                 '%.02f' % scheme_capacity['annual_revenue'],
                 '%.02f' % scheme_capacity['project_cost'],
                 '%.02f' % scheme_capacity['payback_period'],
                 '%.02f' % scheme_capacity['cost_per_kw']])

results.add_row(['Optimum Revenue',
                 scheme_annual_revenue['head'],
                 scheme_annual_revenue['material'],
                 '%.02f' % scheme_annual_revenue['diameter'],
                 '%.02f' % scheme_annual_revenue['capacity'],
                 '%.02f' % scheme_annual_revenue['annual_revenue'],
                 '%.02f' % scheme_annual_revenue['project_cost'],
                 '%.02f' % scheme_annual_revenue['payback_period'],
                 '%.02f' % scheme_annual_revenue['cost_per_kw']])
if opts.heads:
    for scheme in head_schemes:
        results.add_row(['User Specified',
                         scheme['head'],
                         scheme['material'],
                         '%.02f' % scheme['diameter'],
                         '%.02f' % scheme['capacity'],
                         '%.02f' % scheme['annual_revenue'],
                         '%.02f' % scheme['project_cost'],
                         '%.02f' % scheme['payback_period'],
                         '%.02f' % scheme['cost_per_kw']])

print 'Input file: ', opts.pipe_file
print results
# }}} End of Print results

# Plot results {{{
# Name the files correctly so I can find them easily
datestring = '_' + datetime.datetime.now().strftime('%Y%m%d-%H%M')
if opts.heads:
    typestring = '_discrete'
else:
    typestring = '_continuous'

# Now make the plots
if plots.count('penstock_length'): # {{{
# TODO Make penstock_length look pretty
    f_penstock_length = p.figure()
    p_penstock_length = f_penstock_length.add_subplot(111)
    
    if opts.heads: p_penstock_length.plot(x_axis, penstock_length_y_axis, 'bo')
    else:          p_penstock_length.plot(x_axis, penstock_length_y_axis, '-')
    
    p_capacity.set_title('Capacity')
    p_capacity.set_ylabel('Capacity (kW)')
    p_capacity.set_xlabel('Head (m)')
    
    p_penstock_length.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(penstock_length_y_axis) - 5, max(penstock_length_y_axis) * 1.05])
    
    # finally save the plot
    penstock_length_filename = 'plots/penstock_length' + typestring + datestring
    f_penstock_length.savefig(penstock_length_filename)
# }}} End of penstock_length

if plots.count('avg_flow_rate'): # {{{
# TODO Make avg_flow_rate look pretty
    f_avg_flow_rate = p.figure()
    p_avg_flow_rate = f_avg_flow_rate.add_subplot(111)
    
    if opts.heads: p_avg_flow_rate.plot(x_axis, avg_flow_rate_y_axis, 'bo')
    else:          p_avg_flow_rate.plot(x_axis, avg_flow_rate_y_axis, '-')
    
    p_capacity.set_title('Capacity')
    p_capacity.set_ylabel('Capacity (kW)')
    p_capacity.set_xlabel('Head (m)')
    
    p_avg_flow_rate.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(avg_flow_rate_y_axis) - 5, max(avg_flow_rate_y_axis) * 1.05])
    
    # finally save the plot
    avg_flow_rate_filename = 'plots/avg_flow_rate' + typestring + datestring
    f_avg_flow_rate.savefig(avg_flow_rate_filename)
# }}} End of avg_flow_rate

if plots.count('design_flow'): # {{{
# TODO Make design_flow look pretty
    f_design_flow = p.figure()
    p_design_flow = f_design_flow.add_subplot(111)
    
    if opts.heads: p_design_flow.plot(x_axis, design_flow_y_axis, 'bo')
    else:          p_design_flow.plot(x_axis, design_flow_y_axis, '-')
    
    p_capacity.set_title('Capacity')
    p_capacity.set_ylabel('Capacity (kW)')
    p_capacity.set_xlabel('Head (m)')
    
    p_design_flow.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(design_flow_y_axis) - 5, max(design_flow_y_axis) * 1.05])
    
    # finally save the plot
    design_flow_filename = 'plots/design_flow' + typestring + datestring
    f_design_flow.savefig(design_flow_filename)
# }}} End of design_flow

if plots.count('fit'): # {{{
# TODO Make fit look pretty
    f_fit = p.figure()
    p_fit = f_fit.add_subplot(111)
    
    if opts.heads: p_fit.plot(x_axis, fit_y_axis, 'bo')
    else:          p_fit.plot(x_axis, fit_y_axis, '-')
    
    p_capacity.set_title('Capacity')
    p_capacity.set_ylabel('Capacity (kW)')
    p_capacity.set_xlabel('Head (m)')
    
    p_fit.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(fit_y_axis) - 5, max(fit_y_axis) * 1.05])
    
    # finally save the plot
    fit_filename = 'plots/fit' + typestring + datestring
    f_fit.savefig(fit_filename)
# }}} End of fit

if plots.count('capacity'): # {{{
# TODO Make capacity look pretty
    f_capacity = p.figure()
    p_capacity = f_capacity.add_subplot(111)
    
    if opts.heads: p_capacity.plot(x_axis, capacity_y_axis, 'bo')
    else:          p_capacity.plot(x_axis, capacity_y_axis, '-')
    
    p_capacity.set_title('Capacity')
    p_capacity.set_ylabel('Capacity (kW)')
    p_capacity.set_xlabel('Head (m)')
    
    p_capacity.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(capacity_y_axis) - 5, max(capacity_y_axis) * 1.05])
    
    # finally save the plot
    capacity_filename = 'plots/capacity' + typestring + datestring
    f_capacity.savefig(capacity_filename)
# }}} End of capacity

if plots.count('total_penstock_cost'): # {{{
# TODO Make total_penstock_cost look pretty
    f_total_penstock_cost = p.figure()
    p_total_penstock_cost = f_total_penstock_cost.add_subplot(111)
    
    if opts.heads: p_total_penstock_cost.plot(x_axis, total_penstock_cost_y_axis, 'bo')
    else:          p_total_penstock_cost.plot(x_axis, total_penstock_cost_y_axis, '-')
    
    p_total_penstock_cost.set_title('Total_penstock_cost')
    p_total_penstock_cost.set_ylabel('Total_penstock_cost (GBP)')
    p_total_penstock_cost.set_xlabel('Head (m)')
    
    p_total_penstock_cost.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(total_penstock_cost_y_axis) - 5, max(total_penstock_cost_y_axis) * 1.05])
    
    # finally save the plot
    total_penstock_cost_filename = 'plots/total_penstock_cost' + typestring + datestring
    f_total_penstock_cost.savefig(total_penstock_cost_filename)
# }}} End of total_penstock_cost

if plots.count('total_project_cost'): # {{{
# TODO Make total_project_cost look pretty
    f_total_project_cost = p.figure()
    p_total_project_cost = f_total_project_cost.add_subplot(111)
    
    if opts.heads: p_total_project_cost.plot(x_axis, total_project_cost_y_axis, 'bo')
    else:          p_total_project_cost.plot(x_axis, total_project_cost_y_axis, '-')
    
    p_total_project_cost.set_title('Total_project_cost')
    p_total_project_cost.set_ylabel('Total_project_cost (GBP)')
    p_total_project_cost.set_xlabel('Head (m)')
    
    p_total_project_cost.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(total_project_cost_y_axis) - 5, max(total_project_cost_y_axis) * 1.05])
    
    # finally save the plot
    total_project_cost_filename = 'plots/total_project_cost' + typestring + datestring
    f_total_project_cost.savefig(total_project_cost_filename)
# }}} End of total_project_cost

if plots.count('annual_revenue'): # {{{
# TODO Make annual_revenue look pretty
    f_annual_revenue = p.figure()
    p_annual_revenue = f_annual_revenue.add_subplot(111)
    
    if opts.heads: p_annual_revenue.plot(x_axis, annual_revenue_y_axis, 'bo')
    else:          p_annual_revenue.plot(x_axis, annual_revenue_y_axis, '-')
    
    p_annual_revenue.set_title('Annual_revenue')
    p_annual_revenue.set_ylabel('Annual_revenue (GBP)')
    p_annual_revenue.set_xlabel('Head (m)')
    
    p_annual_revenue.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(annual_revenue_y_axis) - 5, max(annual_revenue_y_axis) * 1.05])
    
    # finally save the plot
    annual_revenue_filename = 'plots/annual_revenue' + typestring + datestring
    f_annual_revenue.savefig(annual_revenue_filename)
# }}} End of annual_revenue

if plots.count('payback_period'): # {{{
# TODO Make payback_period look pretty
    f_payback_period = p.figure()
    p_payback_period = f_payback_period.add_subplot(111)
    
    if opts.heads: p_payback_period.plot(x_axis, payback_period_y_axis, 'bo')
    else:          p_payback_period.plot(x_axis, payback_period_y_axis, '-')
    
    p_payback_period.set_title('payback_period')
    p_payback_period.set_ylabel('payback_period (years)')
    p_payback_period.set_xlabel('Head (m)')
    
    p_payback_period.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(payback_period_y_axis) - 5, max(payback_period_y_axis) * 1.05])
    
    # finally save the plot
    payback_period_filename = 'plots/payback_period' + typestring + datestring
    f_payback_period.savefig(payback_period_filename)
# }}} End of payback_period

if plots.count('cost_per_kw'): # {{{
# TODO Make cost_per_kw look pretty
    f_cost_per_kw = p.figure()
    p_cost_per_kw = f_cost_per_kw.add_subplot(111)
    
    if opts.heads: p_cost_per_kw.plot(x_axis, cost_per_kw_y_axis, 'bo')
    else:          p_cost_per_kw.plot(x_axis, cost_per_kw_y_axis, '-')
    
    p_cost_per_kw.set_title('Cost_per_kw')
    p_cost_per_kw.set_ylabel('Cost_per_kw (GBP/kW)')
    p_cost_per_kw.set_xlabel('Head (m)')
    
    p_cost_per_kw.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(cost_per_kw_y_axis) - 5, max(cost_per_kw_y_axis) * 1.05])
    
    # finally save the plot
    cost_per_kw_filename = 'plots/cost_per_kw' + typestring + datestring
    f_cost_per_kw.savefig(cost_per_kw_filename)
# }}} End of cost_per_kw

if plots.count('annual_roi'): # {{{
# TODO Make annual_roi look pretty
    f_annual_roi = p.figure()
    p_annual_roi = f_annual_roi.add_subplot(111)
    
    if opts.heads: p_annual_roi.plot(x_axis, annual_roi_y_axis, 'bo')
    else:          p_annual_roi.plot(x_axis, annual_roi_y_axis, '-')
    
    p_annual_roi.set_title('Annual_roi')
    p_annual_roi.set_ylabel('Annual_roi (%)')
    p_annual_roi.set_xlabel('Head (m)')
    
    p_annual_roi.axis([min(x_axis) - 5, max(x_axis) + 5,
                     min(annual_roi_y_axis) - 5, max(annual_roi_y_axis) * 1.05])
    
    # finally save the plot
    annual_roi_filename = 'plots/annual_roi' + typestring + datestring
    f_annual_roi.savefig(annual_roi_filename)
# }}} End of annual_roi

# }}} End of Plot results

