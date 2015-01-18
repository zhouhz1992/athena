#!/usr/lib/python2.7/bin/python
#---------------------------------------------------------------------------------------
# configure.py: Athena++ configuration script in python.  Original version by CJW.
#
# When configure.py is run, it uses the command line options and default settings to
# create custom versions of the files Makefile and src/defs.hpp from the template files
# Makefile.in and src/defs.hpp.in repspectively.
#
# The following options are implememted:
#   -h  --help        help message
#   --prob=name       use src/pgen/name.cpp as the problem generator
#   --coord=choice    use choice as the coordinate system
#   --eos=choice      use choice as the equation of state
#   --flux=choice     use choice as the Riemann solver
#   -b                enable magnetic fields
#   -s                enable special relativity
#   -g                enable general relativity
#   -t                enable interface frame transformations for GR
#   --order=choice    use choice as the spatial reconstruction algorithm
#   --fint=choice     use choice as the fluid time-integration algorithm
#   --cxx=choice      use choice as the C++ compiler
#   --ifov=N          enable N internal fluid output variables 
#   -mpi              enable parallelization with MPI
#   -omp              enable parallelization with OpenMP
#   --idlength=N      specify the length of the Block UID (default=1)
#   -debug            enable debug flags (-g -O0); override other compiler options
#---------------------------------------------------------------------------------------

# Modules
import argparse
import glob
import re

# Set template and output filenames
makefile_input = 'Makefile.in'
makefile_output = 'Makefile'
defsfile_input = 'src/defs.hpp.in'
defsfile_output = 'src/defs.hpp'

#--- Step 1.  Prepare parser, add each of the arguments --------------------------------
parser = argparse.ArgumentParser()

# --prob=[name] argument
pgen_directory = 'src/pgen/'
# set pgen_choices to list of .cpp files in src/pgen/
pgen_choices = glob.glob(pgen_directory + '*.cpp')
# remove 'src/pgen/' prefix and '.cpp' extension from each filename 
pgen_choices = [choice[len(pgen_directory):-4] for choice in pgen_choices]
parser.add_argument('--prob',
    default='shock_tube',
    choices=pgen_choices,
    help='select problem generator')

# --coord=[name] argument
parser.add_argument('--coord',
    default='cartesian',
    choices=['cartesian','cylindrical','spherical_polar',\
        'minkowski','schwarzschild'],
    help='select coordinate system')

# --eos=[name] argument
parser.add_argument('--eos',
    default='adiabatic',
    choices=['adiabatic','isothermal'],
    help='select equation of state')

# --flux=[name] argument
parser.add_argument('--flux',
    default='hlle',
    choices=['hlle','hllc','hlld','roe','llf'],
    help='select Riemann solver')

# -b argument
parser.add_argument('-b',
    action='store_true',
    default=False,
    help='enable magnetic field')

# -s argument
parser.add_argument('-s',
    action='store_true',
    default=False,
    help='enable special relativity')

# -g argument
parser.add_argument('-g',
    action='store_true',
    default=False,
    help='enable general relativity')

# -t argument
parser.add_argument('-t',
    action='store_true',
    default=False,
    help='enable interface frame transformations for GR')

# --order=[name] argument
parser.add_argument('--order',
    default='plm',
    choices=['plm'],
    help='select spatial reconstruction algorithm')

# --fint=[name] argument
parser.add_argument('--fint',
    default='vl2',
    choices=['vl2'],
    help='select fluid time-integration algorithm')

# --cxx=[name] argument
parser.add_argument('--cxx',
    default='g++',
    choices=['g++','icc','cray'],
    help='select C++ compiler')

# -mpi argument
parser.add_argument('-mpi',
    action='store_true',
    default=False,
    help='enable parallelization with MPI')

# -omp argument
parser.add_argument('-omp',
    action='store_true',
    default=False,
    help='enable parallelization with OpenMP')

# -ifov=N argument
parser.add_argument('--ifov',
    type=int,
    default=0,
    help='number of internal fluid output variables')

# -idlength=N argument
parser.add_argument('--idlength',
    type=int,
    default=1,
    help='length of the block UID, default=1 ')

# -debug argument
parser.add_argument('-debug',
    action='store_true',
    default=False,
    help='enable debug flags; override other compiler options')

# Parse command-line inputs
args = vars(parser.parse_args())

# Prepare dictionaries of substitutions to be made
definitions = {}
makefile_options = {}

#--- Step 3.  Test for incompatible arguments ------------------------------------------

if args['eos']=='isothermal' and args['flux']=='hllc':
  raise SystemExit('### CONFIGURE ERROR: isothermal EOS cannot be used with HLLC flux')

if args['flux']=='hllc' and args['b']:
  raise SystemExit('### CONFIGURE ERROR: HLLC flux cannot be used with MHD')

#--- Step 4.  Set definitions and Makefile options based on above arguments ------------

# --prob=[name] argument
definitions['PROBLEM'] = args['prob']
makefile_options['PROBLEM_FILE'] = args['prob']

# --coord=[name] argument
definitions['COORDINATE_SYSTEM'] = args['coord']
makefile_options['COORDINATES_FILE'] = args['coord']

# --eos=[name] argument
definitions['NON_BAROTROPIC_EOS'] = '1' if args['eos'] == 'adiabatic' else '0'
makefile_options['EOS_FILE'] = args['eos']
# set number of fluid variables for adiabatic/isothermal
if args['eos'] == 'adiabatic':
  definitions['NFLUID_VARIABLES'] = '5'
if args['eos'] == 'isothermal':
  definitions['NFLUID_VARIABLES'] = '4'

# --flux=[name] argument
definitions['RSOLVER'] = args['flux']
makefile_options['RSOLVER_FILE'] = args['flux']

# -b argument
definitions['MAGNETIC_FIELDS_ENABLED'] = '1' if args['b'] else '0'
makefile_options['EOS_FILE'] += '_mhd' if args['b'] else '_hydro'
# set variety of macros based on whether MHD/hydro or adi/iso are defined
if args['b']:
  definitions['NFIELD_VARIABLES'] = '3'
  makefile_options['RSOLVER_DIR'] = 'mhd/'
  if args['flux'] == 'hlle' or args['flux'] == 'llf':
    makefile_options['RSOLVER_FILE'] += '_mhd'
  if args['eos'] == 'adiabatic':
    definitions['NWAVE_VALUE'] = '7'
  else:
    definitions['NWAVE_VALUE'] = '6'
    if args['flux'] == 'hlld':
      makefile_options['RSOLVER_FILE'] += '_iso'
else:
  definitions['NFIELD_VARIABLES'] = '0'
  makefile_options['RSOLVER_DIR'] = 'hydro/'
  if args['eos'] == 'adiabatic':
    definitions['NWAVE_VALUE'] = '5'
  else:
    definitions['NWAVE_VALUE'] = '4'

# -s and -g arguments
definitions['RELATIVISTIC_DYNAMICS'] = '1' if args['s'] or args['g'] else '0'
definitions['GENERAL_RELATIVITY'] = '1' if args['g'] else '0'
if args['s']:
  makefile_options['EOS_FILE'] += '_sr'
  makefile_options['RSOLVER_FILE'] += '_rel'
if args['g']:
  makefile_options['EOS_FILE'] += '_gr'
  makefile_options['RSOLVER_FILE'] += '_rel'
  if not args['t']:
    makefile_options['RSOLVER_FILE'] += '_no_transform'

# --order=[name] argument
definitions['RECONSTRUCT'] = args['order']
makefile_options['RECONSTRUCT_FILE'] = args['order']

# --fint=[name] argument
definitions['FLUID_INTEGRATOR'] = args['fint']
makefile_options['FLUID_INT_FILE'] = args['fint']

# --cxx=[name] argument
definitions['COMPILER_CHOICE'] = args['cxx']
makefile_options['COMPILER_CHOICE'] = args['cxx']
if args['cxx'] == 'icc':
  makefile_options['COMPILER_FLAGS'] = '-O3 -xhost -ipo'
  definitions['COMPILER_FLAGS'] = '-O3 -xhost -ipo'
if args['cxx'] == 'g++':
  makefile_options['COMPILER_FLAGS'] = '-O3'
  definitions['COMPILER_FLAGS'] = '-O3'
if args['cxx'] == 'cray':
  makefile_options['COMPILER_CHOICE'] = 'CC'
  makefile_options['COMPILER_FLAGS'] = '-O3 -lm -h aggress -h vector3 -hfp3'
  definitions['COMPILER_FLAGS'] = '-O3 -lm -h aggress -h vector3 -hfp3'
  

definitions['MPI_OPTION'] = 'MPI_PARALLEL' if args['mpi'] \
    else 'NOT_MPI_PARALLEL'
if args['mpi']:
  if args['cxx'] == 'cray':
    makefile_options['COMPILER_FLAGS'] += ' -h mpi1'
    definitions['COMPILER_FLAGS'] += ' -h mpi1'
  else : 
    makefile_options['COMPILER_CHOICE'] = 'mpicxx'
    definitions['COMPILER_CHOICE'] = 'mpicxx'

definitions['DEBUG'] = 'DEBUG' if args['debug'] \
    else 'NOT_DEBUG'
if args['debug']:
  if args['cxx'] == 'g++':
    makefile_options['COMPILER_FLAGS'] = '-g -O0'
    definitions['COMPILER_FLAGS'] = '-g -O0'
  if args['cxx'] == 'icc':
    makefile_options['COMPILER_FLAGS'] = '-g -O0'
    definitions['COMPILER_FLAGS'] = '-g -O0'
  if args['cxx'] == 'cray':
    makefile_options['COMPILER_FLAGS'] = '-O0'
    definitions['COMPILER_FLAGS'] = '-O0'

definitions['OPENMP_OPTION'] = 'OPENMP_PARALLEL' if args['omp'] \
    else 'NOT_OPENMP_PARALLEL'
if args['omp']:
  if args['cxx'] == 'g++':
    makefile_options['COMPILER_FLAGS'] += ' -fopenmp'
    definitions['COMPILER_FLAGS'] += ' -fopenmp'
  if args['cxx'] == 'icc':
    makefile_options['COMPILER_FLAGS'] += ' -openmp'
    definitions['COMPILER_FLAGS'] += ' -openmp'
  if args['cxx'] == 'cray':
    makefile_options['COMPILER_FLAGS'] += ' -homp'
    definitions['COMPILER_FLAGS'] += ' -homp'
else: 
  if args['cxx'] == 'cray':
    makefile_options['COMPILER_FLAGS'] += ' -hnoomp'
    definitions['COMPILER_FLAGS'] += ' -hnoomp'


# -ifov=N argument
definitions['NUM_IFOV'] = str(args['ifov'])

definitions['ID_LENGTH'] = str(args['idlength'])

#--- Step 5.  Create new files, finish up ----------------------------------------------

# terminate all filenames with .cpp extension
makefile_options['PROBLEM_FILE'] += '.cpp'
makefile_options['COORDINATES_FILE'] += '.cpp'
makefile_options['EOS_FILE'] += '.cpp'
makefile_options['RSOLVER_FILE'] += '.cpp'
makefile_options['RECONSTRUCT_FILE'] += '.cpp'
makefile_options['FLUID_INT_FILE'] += '.cpp'

# Read templates
with open(defsfile_input, 'r') as current_file:
  defsfile_template = current_file.read()
with open(makefile_input, 'r') as current_file:
  makefile_template = current_file.read()

# Make substitutions
for key,val in definitions.iteritems():
  defsfile_template = re.sub(r'@{0}@'.format(key), val, defsfile_template)
for key,val in makefile_options.iteritems():
  makefile_template = re.sub(r'@{0}@'.format(key), val, makefile_template)

# Write output files
with open(defsfile_output, 'w') as current_file:
  current_file.write(defsfile_template)
with open(makefile_output, 'w') as current_file:
  current_file.write(makefile_template)

# Finish with diagnostic output
print('Your Athena++ distribution has now been configured with the following options:')
print('  Problem generator:       ' + args['prob'])
print('  Coordinate system:       ' + args['coord'])
print('  Equation of state:       ' + args['eos'])
print('  Riemann solver:          ' + args['flux'])
print('  Reconstruction method:   ' + args['order'])
print('  Fluid integrator:        ' + args['fint'])
print('  Compiler and flags:      ' + makefile_options['COMPILER_CHOICE'] + ' ' \
    + makefile_options['COMPILER_FLAGS'])
print('  Magnetic fields:         ' + ('enabled' if args['b'] else 'disabled'))
print('  Special relativity:      ' + ('enabled' if args['s'] else 'disabled'))
print('  General relativity:      ' + ('enabled' if args['g'] else 'disabled'))
print('  Frame transformations:   ' + ('enabled' if args['t'] else 'disabled'))
print('  MPI parallelism:         ' + ('enabled' if args['mpi'] else 'disabled'))
print('  OpenMP parallelism:      ' + ('enabled' if args['omp'] else 'disabled'))
print('  Debug flags:             ' + ('enabled' if args['debug'] else 'disabled'))
print('  Internal fluid outvars:  ' + str(args['ifov']))
print('  UID Length:              ' + str(args['idlength']) \
    + '  (maximum refinement level = ' + str(20*args['idlength']) + ')')
