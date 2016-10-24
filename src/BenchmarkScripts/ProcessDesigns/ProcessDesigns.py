import subprocess
import re
import argparse as ap
import sys

import jinja2
import os
from jinja2 import Template

jinja_env = jinja2.Environment(
	loader = jinja2.FileSystemLoader(os.path.abspath('.'))
)

# Exit codes.  See ACSLabSharedLibrary/interactive_tools.h
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BADARGUMENT = 2

def MakeFilenameFriendly(str):
    keepcharacters = (' ','.','_')
    return "".join(c for c in str if c.isalnum() or c in keepcharacters).rstrip()

def GetDesignName(data):
    return "{0}_{1}_i{2}_d{3}".format(data['lane_config'],data['stop_bit'],data['icache_size'],data['dcache_size'])    

def MakeConfigurationRVEX(main_dir, design, data):
    print('Making configuration.rvex from configuration.rvex.j2')
    template = jinja_env.get_template('configuration.rvex.j2')
    configfile = template.render(lane_config=data['lane_config'],stop_bit=data['stop_bit'],icache_size=data['icache_size'],dcache_size=data['dcache_size'])
    config_dir = os.path.join(main_dir,design)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    with open(os.path.join(config_dir,'configuration.rvex'.format(job_title)),'w') as file:
        file.write(configfile)
          
def MakeConfigCompile(main_dir, design, data):
    print('Making src/config.compile from config.compile.j2')    
    template = jinja_env.get_template('config.compile.j2')
    configfile = template.render(main_flags=data['main_flags'],lib_flags=data['lib_flags'],flag_sets=data['flag_sets'])
    config_dir_src = os.path.join(main_dir,design,'src')
    if not os.path.exists(config_dir_src):
        os.makedirs(config_dir_src)
    with open(os.path.join(config_dir_src,'config.compile'.format(job_title)),'w') as file:
        file.write(configfile)             

def Configure(main_dir, design):
    print('Run `configure`')
    result = subprocess.run(["configure"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,cwd="{0}/configurations/{1}/output-{2}.c/".format(main_dir,configuration,benchmark))
    if result.returncode != EXIT_SUCCESS:
        print("ERROR configure returned {0}. Output below.\n".format(result.returncode))
        error_occured = True                
        print("StdOut:")
        print(result.stdout)
        print("StdErr:")
        print(result.stderr)
        return False
    with open(os.path.join(main_dir,design,'configure.log'), 'w') as log:
        log.write(result.stdout);
        print("Written configure log.")
    return True
    
def Compile(main_dir, design):
    print('Run `make compile`')
    result = subprocess.run(["make",'compile'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,cwd="{0}/configurations/{1}/output-{2}.c/".format(main_dir,configuration,benchmark))
    if result.returncode != EXIT_SUCCESS:
        print("ERROR make compile returned {0}. Output below.\n".format(result.returncode))
        error_occured = True                
        print("StdOut:")
        print(result.stdout)
        print("StdErr:")
        print(result.stderr)
        return False
    with open(os.path.join(main_dir,design,'compile.log'), 'w') as log:
        log.write(result.stdout);
        print("Written compile log.")
    return True
    
def Synthesize(main_dir, design):
    print('Run `make synth`')
    result = subprocess.run(["make",'synth'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,cwd="{0}/configurations/{1}/output-{2}.c/".format(main_dir,configuration,benchmark))
    if result.returncode != EXIT_SUCCESS:
        print("ERROR make synth returned {0}. Output below.\n".format(result.returncode))
        error_occured = True                
        print("StdOut:")
        print(result.stdout)
        print("StdErr:")
        print(result.stderr)
        return False
    with open(os.path.join(main_dir,design,'synth.log'), 'w') as log:
        log.write(result.stdout);
        print("Written synth log.")
    return True
    
def Simulate(main_dir, design):
    print('Run `make sim`')
    result = subprocess.run(["make",'sim'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,cwd="{0}/configurations/{1}/output-{2}.c/".format(main_dir,configuration,benchmark))
    if result.returncode != EXIT_SUCCESS:
        print("ERROR make sim returned {0}. Output below.\n".format(result.returncode))
        error_occured = True                
        print("StdOut:")
        print(result.stdout)
        print("StdErr:")
        print(result.stderr)
        return False
    with open(os.path.join(main_dir,design,'sim.log'), 'w') as log:
        log.write(result.stdout);
        print("Written sim log.")
    return True

def Run(main_dir, design):
    print('Run `make run`')
    result = subprocess.run(["make",'run'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,cwd="{0}/configurations/{1}/output-{2}.c/".format(main_dir,configuration,benchmark))
    if result.returncode != EXIT_SUCCESS:
        print("ERROR make run returned {0}. Output below.\n".format(result.returncode))
        error_occured = True                
        print("StdOut:")
        print(result.stdout)
        print("StdErr:")
        print(result.stderr)
        return False
    with open(os.path.join(main_dir,design,'run.log'), 'w') as log:
        log.write(result.stdout);
        print("Written run log.")
    return True

if __name__ == '__main__':
    parser = ap.ArgumentParser(prog='MCARunBenchmarks',description='MCA Benchmark Runner Script')
    parser.add_argument('--sim-designs', action="store_true", help='Sim all designs')
    parser.add_argument('--synth-designs', action="store_true", help='Synth all designs')
    parser.add_argument('--boardserver-run', action="store_true", help='Run all designs on boardserver')
    #TODO report making
    parser.add_argument('--designs-file', action="store", help='Main designs list (csv)',default="design-settings.csv")
    parser.add_argument('--main-dir', action="store", help='Main working directory',default="/home/user/workspace/assignment1")
    #parser.add_argument('--output-dir', action="store", help='Output directory',default=".")
    try:
        opts = parser.parse_args(sys.argv[1:])        

        main_dir = opts.main_dir
        designs_file = opts.designs_file

        benchmarks = ['engine','fir','adpcm','pocsag']
        configurations = ['assignment2']
        main_flags = '-O4'
        lib_flags = '-O4'
        flag_sets = {'engine':'-O4 -autoinline -d -fexpand-div -fdag-file=trace1 -fdraw-dag=1',
                     'fir':'-O4 -autoinline -d -fexpand-div -fdag-file=trace1 -fdraw-dag=1',
                     'adpcm':'-O4 -autoinline -d -fdag-file=trace1 -fdraw-dag=1',
                     'pocsag':'-O4 -autoinline -d -fdag-file=trace1 -fdraw-dag=1'}



        with open(designs_file,'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                design_name = GetDesignName(row)
                design_filename = MakeFilenameFriendly(design_name)
                MakeConfigurationRVEX(main_dir,design_filename,row)
                Configure(main_dir,design_filename)
                MakeConfigCompile(main_dir,design_filename,row)
                Compile(main_dir,design_filename)
                if opts.sim_designs:
                    Simulate(main_dir,design_filename)

                if opts.synth_designs:
                    Synthesize(main_dir,design_filename)

                if opts.boardserver_run:
                    Run(main_dir,design_filename)   


        ## Task 1
        RunBenchmark(main_dir, configurations, benchmarks, flag_sets)

        print("Done.")
    except SystemExit:
        print('Bad Arguments')