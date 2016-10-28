import os
import sys
import argparse as ap
import distutils.dir_util
import colorama
import re
import csv
import glob
import copy
import pprint
import time
import locale
from collections import OrderedDict

colorama.init(autoreset=True)

C_RED = colorama.Fore.RED + colorama.Style.BRIGHT
C_YELLOW = colorama.Fore.YELLOW + colorama.Style.BRIGHT
C_GREEN = colorama.Fore.GREEN + colorama.Style.BRIGHT
C_CYAN = colorama.Fore.CYAN + colorama.Style.BRIGHT

# Exit codes.  See ACSLabSharedLibrary/interactive_tools.h
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BADARGUMENT = 2

def ParseEnergyTxt(collection_dir, design):
    pattern = '\s*([a-zA-Z0-9/ ]+):\s*([0-9\.,]+)\s*m[jJ]'
    comp_patt = re.compile(pattern)
    parsed = {}
    config_dir = os.path.join(collection_dir,design)
    energy_filename = os.path.join(config_dir,'energy.txt')
    if os.path.exists(energy_filename):
        with open(energy_filename,'r') as energy_file:
            for line in energy_file:
                match = comp_patt.search(line)
                if match:
                    parsed[match.group(1)] = float(match.group(2).replace(',',''))
    return parsed

def GetListAverage(list_of_lists):
    num_lists = len(list_of_lists)

    if num_lists >0:
        length = len(list_of_lists[0])
        average_list = [0] * length

        for sublist in list_of_lists:
            for ind in range(0,length):
                average_list[ind] += sublist[ind]*(1/num_lists)
        return average_list
    else:
        return None

def GetEnergy(parsed):
    if isinstance(parsed, dict):
        if 'Average' in parsed:
            return parsed['Average']

    return 0

def ParsePerformanceTxt(collection_dir, design):
    pattern = '\s*([a-zA-Z0-9/ ]+):\s*([0-9\.,]+)\s*cycles'
    comp_patt = re.compile(pattern)
    parsed = {}
    config_dir = os.path.join(collection_dir,design)
    performance_filename = os.path.join(config_dir,'performance.txt')
    if os.path.exists(performance_filename):
        with open(performance_filename,'r') as performance_file:
            for line in performance_file:
                match = comp_patt.search(line)
                if match:
                    parsed[match.group(1)] = float(match.group(2).replace(',',''))
    return parsed

def GetPerformance(parsed):
    if isinstance(parsed, dict):
        if 'Average' in parsed:
            return parsed['Average']

    return 0

def ParseTimingTxt(collection_dir, design):
    pattern = 'All timing constraints were met\.'
    comp_patt = re.compile(pattern)
    config_dir = os.path.join(collection_dir,design)
    timing_filename = os.path.join(config_dir,'timing.txt')
    if os.path.exists(timing_filename):
        with open(timing_filename,'r') as timing_file:
            for line in timing_file:
                match = comp_patt.search(line)
                if match:
                    return True
    return False

def ParseAreaTxt(collection_dir, design):
    pattern = '\s*Number of\s*([a-zA-Z0-9/ ]+):\s*([0-9,]+)\s*out of'
    comp_patt = re.compile(pattern)
    parsed = {}
    config_dir = os.path.join(collection_dir,design)
    area_filename = os.path.join(config_dir,'area.txt')
    if os.path.exists(area_filename):
        with open(area_filename,'r') as area_file:
            for line in area_file:
                match = comp_patt.search(line)
                if match:
                    parsed[match.group(1)] = int(match.group(2).replace(',',''))
    return parsed

def GetAreaNumber(parsed):
    if isinstance(parsed, dict):
        if 'Slice Registers' in parsed:
            return parsed['Slice Registers'] * 5 + parsed['Slice LUTs'] * 60 + parsed['RAMB36E1/FIFO36E1s'] * 216000 + parsed['RAMB18E1/FIFO18E1s'] * 108000 + parsed['DSP48E1s'] * 250000

    return 0

def ParseRunLog(run_log):
    pattern = '\s*([a-zA-Z0-9/ ]+):\s*([0-9,]+)\s*$'
    comp_patt = re.compile(pattern)
    parsed = {}
    parts = ['init','engine','fir','adpcm','pocsag']
    current_part = ''
    if os.path.exists(run_log):
        with open(run_log,'r') as runlog_file:
            for line in runlog_file:
                line = line.strip()
                if line in parts:
                    current_part = line
                    continue
                match = comp_patt.search(line)
                if match:
                    if current_part not in parsed:
                        parsed[current_part] = {}
                    parsed[current_part][match.group(1)] = int(match.group(2))
    return parsed

def CleanupRunLog(parsed):
    parts = ['init','engine','fir','adpcm','pocsag']
    total = copy.deepcopy(parsed[parts[-1]])
    prev_part = False
    for part in parts:
        if prev_part != False:
            for metric in parsed[part]:
                parsed[part][metric] -= parsed[prev_part][metric]
        prev_part = part

    parsed['total'] = total
    return parsed

def GetRunLogMetrics(parsed):
    metrics = []
    for metric in runlog_metrics:
        metrics.append(parsed['total'][runlog_metrics[metric]]-parsed['init'][runlog_metrics[metric]])

    extra_metrics = []
    #extras
    total_imiss = float(parsed['total'][runlog_metrics['total_imiss']]-parsed['init'][runlog_metrics['total_imiss']])
    total_iacc = float(parsed['total'][runlog_metrics['total_iacc']]-parsed['init'][runlog_metrics['total_iacc']])
    imiss_percent = total_imiss/total_iacc*100
    extra_metrics.append(imiss_percent)

    total_drmiss = float(parsed['total'][runlog_metrics['total_drmiss']]-parsed['init'][runlog_metrics['total_drmiss']])
    total_dracc = float(parsed['total'][runlog_metrics['total_dracc']]-parsed['init'][runlog_metrics['total_dracc']])
    drmiss_percent = total_drmiss/total_dracc*100
    extra_metrics.append(drmiss_percent)

    total_dwmiss = float(parsed['total'][runlog_metrics['total_dwmiss']]-parsed['init'][runlog_metrics['total_dwmiss']])
    total_dwacc = float(parsed['total'][runlog_metrics['total_dwacc']]-parsed['init'][runlog_metrics['total_dwacc']])
    dwmiss_percent = total_dwmiss/total_dwacc*100
    extra_metrics.append(dwmiss_percent)
    return (metrics,extra_metrics)

def ProcessDesign(collection_dir,design):
    print(C_CYAN + "Processing results for design {0}".format(design))
    area_number = GetAreaNumber(ParseAreaTxt(collection_dir,design))
    print("Area Number: {0}".format(area_number))

    energy = GetEnergy(ParseEnergyTxt(collection_dir,design))
    print("Dynamic Energy: {0} mJ".format(energy))

    performance = GetPerformance(ParsePerformanceTxt(collection_dir,design))
    print("Performance: {0} cycles".format(performance))

    timing_passed = 'Yes' if ParseTimingTxt(collection_dir,design) else 'No'
    print("Timing OK: {0}".format(timing_passed))

    runlogs = FindRunLogs(collection_dir,design)
    pp = pprint.PrettyPrinter(indent=4)
    clean_runlogs = {}
    clean_runlogs_extra = {}
    for runlog in runlogs:
        (result, extra_result) = GetRunLogMetrics(CleanupRunLog(ParseRunLog(runlog)))

        core = runlog[-9:-4] # from ./run0-core0.log

        if core not in clean_runlogs:
            clean_runlogs[core] = []
        clean_runlogs[core].append(result)
        if core not in clean_runlogs_extra:
            clean_runlogs_extra[core] = []
        clean_runlogs_extra[core].append(extra_result)

    for core in clean_runlogs:
        print('Metrics for {0}'.format(core))
        pp.pprint([int(round(o)) for o in GetListAverage(clean_runlogs[core])])
        print('Extra for {0}'.format(core))
        pp.pprint(GetListAverage(clean_runlogs_extra[core]))

    core0_metrics = GetListAverage(clean_runlogs['core0'])
    core0_extra_metrics = GetListAverage(clean_runlogs_extra['core0'])

    return [o[2:].replace('-',':') for o in design.split('_')] + [area_number,energy,performance,timing_passed] + [int(round(o)) for o in core0_metrics] + core0_extra_metrics


def FindRunLogs(collection_dir,design):
    return glob.glob(os.path.join(collection_dir,design,'run*-core*.log'))

def FindDesigns(main_dir):
    return [o for o in os.listdir(main_dir) if os.path.isdir(os.path.join(main_dir,o))]

if __name__ == '__main__':
    t_launch = time.time()
    parser = ap.ArgumentParser(prog='MCAProcessBenchmarkResults',description='MCA Benchmark Result Processor Script')
    parser.add_argument('--collection-dir', action="store", help='Collection output directory',default="/home/user/workspace/assignment2/results")

    try:
        opts = parser.parse_args(sys.argv[1:])

        collection_dir = os.path.abspath(opts.collection_dir)

        designs = FindDesigns(collection_dir)

        results = []


        runlog_metrics = {
            'total_cycles':'CYC',
            'total_stalls':'STALL',
            'total_bundles':'BUN',
            'total_syllables':'SYL',
            'total_nops':'NOP',
            'total_iacc':'IACC',
            'total_imiss':'IMISS',
            'total_dracc':'DRACC',
            'total_drmiss':'DRMISS',
            'total_dwacc':'DWACC',
            'total_dwmiss':'DWMISS'
        }

        extra_runlog_metrics = ['imiss_percent','drmiss_percent','dwmiss_percent']

        runlog_metrics = OrderedDict(sorted(runlog_metrics.items(), key=lambda t: t[0]))

        if len(designs) == 0:
            print("No designs found.")
        else:

            for design in designs:
                results.append(ProcessDesign(collection_dir,design))

        print(C_CYAN + "Writing results file.")

        with open(os.path.join(collection_dir,'processed_results.csv'), 'w', newline='') as csvfile:
            with open(os.path.join(collection_dir,'processed_results_excel.csv'), 'w', newline='') as csvfile_excel:
                resultswriter = csv.writer(csvfile, delimiter=',')
                resultswriter_excel = csv.writer(csvfile_excel, delimiter=';')
                header = ['lane_config','stop_bit','icache_size','dcache_size','area_number','energy_mJ','performance_cycles','timing_passed'] + list(runlog_metrics.keys()) + extra_runlog_metrics
                resultswriter.writerow(header)
                resultswriter_excel.writerow(header)
                for result in results:
                    # Round values
                    result=[format(x,".2f").replace('.',',') if isinstance(x, float) else x for x in result]
                    resultswriter.writerow(result)
                    # Put comma for excel win
                    result=[x.replace('.',',') if isinstance(x, str) else x for x in result]
                    resultswriter_excel.writerow(result)

        print("Done. Run time is: {0} seconds".format((time.time() - t_launch)))
    except SystemExit:
        print('Bad Arguments')