import os
import sys
import argparse as ap
import distutils.dir_util
import colorama

import time

colorama.init(autoreset=True)

C_RED = colorama.Fore.RED + colorama.Style.BRIGHT
C_YELLOW = colorama.Fore.YELLOW + colorama.Style.BRIGHT
C_GREEN = colorama.Fore.GREEN + colorama.Style.BRIGHT
C_CYAN = colorama.Fore.CYAN + colorama.Style.BRIGHT

# Exit codes.  See ACSLabSharedLibrary/interactive_tools.h
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BADARGUMENT = 2

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

def ParseAreaTxt(main_dir, design, design_num=0):
    pattern = '\s*Number of\s*([a-zA-Z0-9/ ]+):\s*([0-9,]+)\s*out of'
    comp_patt = re.compile(pattern);
    parsed = {}
    config_dir_result = os.path.join(main_dir,design)
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

def FindDesigns(main_dir):
    return [o for o in os.listdir(main_dir) if os.path.isdir(os.path.join(main_dir,o))]

if __name__ == '__main__':
    t_launch = time.time()
    parser = ap.ArgumentParser(prog='MCACollectBenchmarkResults',description='MCA Benchmark Result Collector Script')
    parser.add_argument('--main-dir', action="store", help='Main working directory',default="/home/user/workspace/assignment2/configurations")
    parser.add_argument('--collection-dir', action="store", help='Collection output directory',default="/home/user/workspace/assignment2/results")

    try:
        opts = parser.parse_args(sys.argv[1:])

        main_dir = os.path.abspath(opts.main_dir)

        collection_dir = os.path.abspath(opts.collection_dir)

        designs = FindDesigns(main_dir)
        
        if len(designs) == 0:
            print("No designs found.")
        else:
            if not os.path.exists(collection_dir):
                os.makedirs(collection_dir)
            
            for design in designs:
                if os.listdir(os.path.join(main_dir,design,'results')):
                    print(C_GREEN+"Copying results for design {0}".format(design))
                    distutils.dir_util.copy_tree(os.path.join(main_dir,design,'results'),os.path.join(collection_dir,design))
                else:
                    print(C_RED+"No results found for design {0}".format(design))


        print("Done. Run time is: {0} seconds".format((time.time() - t_launch)))
    except SystemExit:
        print('Bad Arguments')