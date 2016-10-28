import subprocess
import re
import argparse as ap
import sys
import csv
import jinja2
import os
import shutil
import colorama
from terminaltables import AsciiTable
from jinja2 import Template
import multiprocessing as mp
import traceback

import time

colorama.init(autoreset=True)

C_RED = colorama.Fore.RED + colorama.Style.BRIGHT
C_YELLOW = colorama.Fore.YELLOW + colorama.Style.BRIGHT
C_GREEN = colorama.Fore.GREEN + colorama.Style.BRIGHT
C_CYAN = colorama.Fore.CYAN + colorama.Style.BRIGHT


jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(os.path.abspath('.')))

# Exit codes.  See ACSLabSharedLibrary/interactive_tools.h
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BADARGUMENT = 2

lock = mp.Lock()

results_lock = mp.Lock()

def ParPrint(str):
    lock.acquire()
    try:
        sys.stdout.write(str)
        sys.stdout.write('\n')
        sys.stdout.flush()
    finally:
        lock.release()

def PrintResults(designs, results):
    display_results = []
    display_results.append(sorted([''] + designs))

    for result in sorted(results):
        display_line = [result]
        for design in sorted(results[result]):
            display_line.append(results[result][design])
        display_results.append(display_line)

    results_table = AsciiTable(display_results)
    ParPrint(results_table.table)

def execute(command,cwd,logfile=None,design_num=0):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd, universal_newlines=True)

    # Poll process for new output until finished
    if logfile != None:
        file_stdout = open("{0}.out.log".format(logfile),'w')
    while True:
        nextline = process.stdout.readline()
        #nextline_err = process.stderr.readline()
        if nextline == '' and process.poll() is not None:
            break
        if not nextline == '':
            sys.stdout.write("{0} > ".format(design_num))
            if 'license' in nextline:
                sys.stdout.write(C_YELLOW + nextline)
            else:
                sys.stdout.write(nextline)
            if file_stdout:
                file_stdout.write(nextline)
            sys.stdout.flush()


    #output = process.communicate()[0]
    exitCode = process.returncode

    file_stdout.close()
    #if (exitCode == 0):
    with open("{0}.exitcode".format(logfile),'w') as exitcode_file:
        exitcode_file.write("{0}\n".format(exitCode))

    return exitCode
    #else:
    #    return exitCode
        #raise ProcessException(command, exitCode, output)
def MakeFilenameFriendly(str):
    str = str.replace(':','-')
    keepcharacters = (' ','.','_','-')
    return "".join(c for c in str if c.isalnum() or c in keepcharacters).rstrip()

def GetDesignName(data):
    return "lc{0}_sb{1}_ic{2}_dc{3}".format(data['lane_config'],data['stop_bit'],data['icache_size'],data['dcache_size'])

def MakeConfigurationRVEX(main_dir, design, data, design_num=0):
    ParPrint(C_CYAN + '{1} > Making configuration.rvex from configuration.rvex.j2 for {0}'.format(design,design_num))
    template = jinja_env.get_template('configuration.rvex.j2')
    configfile = template.render(lane_config=data['lane_config'],stop_bit=data['stop_bit'],icache_size=data['icache_size'],dcache_size=data['dcache_size'])
    config_dir = os.path.join(main_dir,design)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    with open(os.path.join(config_dir,'configuration.rvex'),'w') as file:
        file.write(configfile)
        return True

def MakeConfigCompile(main_dir, design, data, benchmark_data, contexts=1, design_num=0):
    template_file = 'config.compile.multi.j2'   
    ParPrint(C_CYAN + '{2} > Making src/config.compile from {1} for {0}'.format(design,template_file,design_num))
    template = jinja_env.get_template(template_file)

    configfile = template.render(main_flags=data['main_flags'],lib_flags=data['lib_flags'],flag_sets=data['flag_sets'],contexts=range(0,contexts))
    config_dir_src = os.path.join(main_dir,design,'src')
    if not os.path.exists(config_dir_src):
        os.makedirs(config_dir_src)
    with open(os.path.join(config_dir_src,'config.compile'),'w') as file:
        file.write(configfile)
    
    shutil.copy('reconfigure.h',os.path.join(main_dir,design,'src','reconfigure.h'))
    shutil.copy('reconfigure.c',os.path.join(main_dir,design,'src','reconfigure.c'))
    
    base_address = 0x3F000000
    context_offset = 0x100000

    context_benches = benchmark_data['contexts'] 

    # Collapse all into first context if there are too many contexts defined
    if len(benchmark_data['contexts']) > contexts:
        tmp = []
        for c in context_benches:
            for bench in c:
                tmp.append(bench)

        context_benches = [] 
        context_benches.append(tmp)     
    print(context_benches)
    ParPrint("{0}, {1}, {2}".format(contexts,len(benchmark_data['contexts']),len(context_benches)))
    #ParPrint(', '.join(context_benches))

    template_mc = jinja_env.get_template('main-core.c.j2') 
    for context in range(0,contexts):
               
        ParPrint("{0}".format(context))
        maincore_file = template_mc.render(record_ptr="0x{0:02X}".format(base_address + context * context_offset),benchmarks=context_benches[context],benchmark_data=benchmark_data['benchmarks'])
        with open(os.path.join(config_dir_src,'main-core0-ctxt{0}.c'.format(context)),'w') as file_mc:
            file_mc.write(maincore_file)


    return True

def Clean(main_dir, design, design_num=0):
    ParPrint(C_CYAN + '{1} > Clean {0}'.format(design,design_num))
    config_dir = os.path.join(main_dir,design)
    if os.path.exists(config_dir):
        shutil.rmtree(config_dir)
    return True

def Configure(main_dir, design, design_num=0):
    ParPrint(C_CYAN + '{1} > Running `configure` for {0} ({1})'.format(design,design_num))
    config_dir = os.path.join(main_dir,design)
    result = execute("configure",cwd=config_dir,logfile=os.path.join(config_dir,'configure'),design_num=design_num)
    if result != EXIT_SUCCESS:
        ParPrint(C_RED + "ERROR configure returned {0}.\n".format(result))
        error_occured = True
        return False
    #with open(os.path.join(main_dir,design,'configure.log'), 'w') as log:
    #    log.write(result.stdout);
     #   ParPrint("Written configure log.")
    return True

def Compile(main_dir, design, design_num=0):
    ParPrint(C_CYAN + '{1} > Running `make compile` for {0} ({1})'.format(design,design_num))
    config_dir = os.path.join(main_dir,design)
    result = execute(["make","compile"],cwd=config_dir,logfile=os.path.join(config_dir,'make-compile'),design_num=design_num)
    if result != EXIT_SUCCESS:
        ParPrint(C_RED + "ERROR make compile returned {0}.\n".format(result))
        error_occured = True
        return False
    #with open(os.path.join(main_dir,design,'compile.log'), 'w') as log:
     #   log.write(result.stdout);
    #    ParPrint("Written compile log.")
    return True

def Synthesize(main_dir, design, design_num=0):
    ParPrint(C_CYAN + '{1} > Running `make synth` for {0} ({1})'.format(design,design_num))
    config_dir = os.path.join(main_dir,design)
    result = execute(["make","synth"],cwd=config_dir,logfile=os.path.join(config_dir,'make-synth'),design_num=design_num)
    if result != EXIT_SUCCESS:
        ParPrint(C_RED + "ERROR make synth returned {0}.\n".format(result))
        error_occured = True
        return False
   # with open(os.path.join(main_dir,design,'synth.log'), 'w') as log:
   #     log.write(result.stdout);
   #     ParPrint("Written synth log.")
    return True

def Simulate(main_dir, design, design_num=0):
    ParPrint(C_CYAN + '{1} > Running `make sim` for {0} ({1})'.format(design,design_num))
    config_dir = os.path.join(main_dir,design)
    result = execute(["make","sim"],cwd=config_dir,logfile=os.path.join(config_dir,'make-sim'),design_num=design_num)
    if result != EXIT_SUCCESS:
        ParPrint(C_RED + "ERROR make sim returned {0}.\n".format(result))
        error_occured = True
        return False
   # with open(os.path.join(main_dir,design,'sim.log'), 'w') as log:
    #    log.write(result.stdout);
    #    ParPrint("Written sim log.")
    return True

def Run(main_dir, design, design_num=0):
    ParPrint(C_CYAN + '{1} > Running `make run` for {0} ({1})'.format(design,design_num))
    config_dir = os.path.join(main_dir,design)
    result = execute(["make","run"],cwd=config_dir,logfile=os.path.join(config_dir,'make-run'),design_num=design_num)
    if result != EXIT_SUCCESS:
        ParPrint(C_RED + "ERROR make run returned {0}.\n".format(result))
        error_occured = True
        return False
   # with open(os.path.join(main_dir,design,'run.log'), 'w') as log:
    #    log.write(result.stdout);
    #    ParPrint("Written run log.")
    return True


def RunDesign(run):
    try:
        t_start = time.time()
        row = run['row']
        design_num = run['design_num']
        results = {}

        design_name = GetDesignName(row)
        contexts = len(row['lane_config'].split(':'))
        ParPrint(C_CYAN + '{2} > Found {0} context(s) for design {1} ({2})'.format(contexts,design_name,design_num))
        design_filename = MakeFilenameFriendly(design_name)
        run['design_name'] = design_name
        run['contexts'] = contexts

        if opts.clean_designs:
            results['Clean'] = Clean(main_dir,design_filename)
        if opts.setup_designs:
            results['MakeConfigurationRVEX'] = MakeConfigurationRVEX(main_dir,design_filename,row,design_num)
            results['Configure'] = Configure(main_dir,design_filename,design_num)
            flags = {'main_flags': main_flags,
            'lib_flags': lib_flags,
                'flag_sets':flag_sets  }
            results['MultiContext'] = 'Yes' if contexts != 1 else 'No'
            results['MakeConfigCompile'] = MakeConfigCompile(main_dir,design_filename,flags,run['benchmarks'],contexts,design_num)
        if opts.compile_designs:
            t1 = time.time()
            results['Compile'] = Compile(main_dir,design_filename,design_num)
            results['CompileTime'] = time.time() - t1

        if opts.sim_designs:
            t1 = time.time()
            results['Simulate'] = Simulate(main_dir,design_filename,design_num)
            results['SimulateTime'] = time.time() - t1

        if opts.synth_designs:
            t1 = time.time()
            results['Synthesize'] = Synthesize(main_dir,design_filename,design_num)
            results['SynthesizeTime'] = time.time() - t1
            parsedArea = ParseAreaTxt(main_dir,design_filename,design_num)
            results['SynthesizeArea'] = GetAreaNumber(parsedArea);

        if opts.boardserver_run:
            t1 = time.time()
            results['Run'] = Run(main_dir,design_filename,design_num)
            results['RunTime'] = time.time() - t1
            
        if opts.collect_results:
            t1 = time.time()
            results['CollectResults'] = CollectResults(main_dir,design_filename,design_num)
            results['CollectResultsTime'] = time.time() - t1

        results['TotalTime'] = time.time() - t_start
        ParPrint(C_GREEN + '{1} > Returning run variables for {0} ({1})'.format(design_name,design_num))

        run['results'] = results
        return run
    except:
        ParPrint("{1} > Unexpected error: {0}".format(sys.exc_info()[0],design_num))
        ParPrint(traceback.format_exc())
        raise

def ParseAreaTxt(main_dir, design, design_num=0):
    pattern = '\s*Number of\s*([a-zA-Z0-9/ ]+):\s*([0-9,]+)\s*out of'
    comp_patt = re.compile(pattern);
    parsed = {}
    config_dir_result = os.path.join(main_dir,design,'results')
    aera_filename = os.path.join(config_dir_result,'area.txt')
    if os.path.exists(aera_filename):
        with open(aera_filename,'r') as area_file:
            for line in area_file:
                match = comp_patt.search(line)
                if match: 
                    parsed[match.group(1)] = match.group(2).replace(',','')  
    return parsed           
                
def GetAreaNumber(parsed):
    if isinstance(parsed, dict):
        if 'Slice Registers' in parsed:
            return parsed['Slice Registers']*1+parsed['Slice LUTs']*1+parsed['RAMB36E1/FIFO36E1s']*3600+parsed['RAMB18E1/FIFO18E1s']*1800+parsed['DSP48E1s']*1200
    
    return 0


def RunDesignResult(run):
    results_lock.acquire()
    try:
        ParPrint(C_GREEN + "Design {0} {1} complete".format(run['design_num'],run['design_name']))
        for result in run['results']:
            ParPrint(C_GREEN + "Collecting {0} for {1}".format(result,run['design_num']))
            if result not in main_results:
                main_results[result] = {}
            main_results[result][run['design_name']] = run['results'][result]
        ParPrint(C_GREEN + "Collected results for {0}.".format(run['design_num']))
    except:
        ParPrint("Unexpected error: {0}".format(sys.exc_info()[0]))
        ParPrint(sys.exc_info())
        raise
    finally:
        results_lock.release()

if __name__ == '__main__':
    t_launch = time.time()
    parser = ap.ArgumentParser(prog='MCARunBenchmarks',description='MCA Benchmark Runner Script')
    parser.add_argument('--setup-designs', action="store_true", help='Setup all designs')
    parser.add_argument('--clean-designs', action="store_true", help='Clean all designs')
    parser.add_argument('--compile-designs', action="store_true", help='Compile all designs')
    parser.add_argument('--sim-designs', action="store_true", help='Sim all designs')
    parser.add_argument('--synth-designs', action="store_true", help='Synth all designs')
    parser.add_argument('--boardserver-run', action="store_true", help='Run all designs on boardserver')
    parser.add_argument('--instances', action="store", help='Number of instances; think about license limitations. The max is the number of processors.',default=8)
    parser.add_argument('--designs-file', action="store", help='Main designs list (csv)',default="designs.csv")
    parser.add_argument('--main-dir', action="store", help='Main working directory',default="/home/user/workspace/assignment2/configurations")

    try:
        opts = parser.parse_args(sys.argv[1:])

        main_dir = os.path.abspath(opts.main_dir)
        designs_file = opts.designs_file

        
        benchmarks = {
            'contexts':[
                ['engine','fir'],
                ['adpcm','pocsag']                
            ],
            'benchmarks':{
                'engine':{
                    'reconfigure_on_finish':False
                    
                },
            'fir':{
                    'reconfigure_on_finish':False
                    
                },
            'adpcm':{
                    'reconfigure_on_finish':False
                    
                },
                'pocsag':{
                    'reconfigure_on_finish':'0x0'
                    
                }            
            }
        }
        configurations = ['assignment2']
        main_flags = '-O4'
        lib_flags = '-O4'
        flag_sets = {'engine':'-O4 -autoinline -d -fexpand-div -fdag-file=trace1 -fdraw-dag=1',
                     'fir':'-O4 -autoinline -d -fexpand-div -fdag-file=trace1 -fdraw-dag=1',
                     'adpcm':'-O4 -autoinline -d -fdag-file=trace1 -fdraw-dag=1',
                     'pocsag':'-O4 -autoinline -d -fdag-file=trace1 -fdraw-dag=1'}
        designs = []
        main_results = {}
        with open(designs_file,'r') as csvfile:
            #q = mp.Queue()
            #p = mp.Pool(mp.cpu_count(),RunDesignPar,(q,results))
            instances = min(mp.cpu_count(),int(opts.instances))
            p = mp.Pool(instances)
            #parr_data=[]
            #dialect = csv.Sniffer().sniff(csvfile.read(1024), delimiters=";,")
            #print(dialect)
            #csvfile.seek(0)
            #reader = csv.DictReader(csvfile,dialect)
            reader = csv.DictReader(csvfile,delimiter=';')
            design_num = 0
            for row in reader:
                designs.append(GetDesignName(row))
                #parr_data.append({'row':row,'design_num':design_num})
                p.apply_async(RunDesign, args = ({'row':row,'design_num':design_num,'benchmarks':benchmarks},), callback = RunDesignResult)
                design_num += 1

            p.close()
            p.join()





        PrintResults(designs,main_results)

        

        print("Done. Run time is: {0} minutes".format((time.time() - t_launch) / 60))
    except SystemExit:
        print('Bad Arguments')