import subprocess
import re

main_dir = '~/workspace/assignment1/'

def RunBenchmark(configurations,benchmarks,flag_sets):
    for configuration in configurations:
        for benchmark in benchmarks:
            for flag_set in flag_sets:
                # Metrics
                cycles = 0;

                print("Compiling and running benchmark {0} with configuration {1} and flags {2}.\n".format(benchmark,configuration,flag_set))
                result = subprocess.run(["run",benchmark,flag_set],stdout=subprocess.PIPE,universal_newlines=True,cwd="{0}/configurations/{1}/".format(main_dir,configuration))
                if result.returncode != EXIT_SUCCESS:
                    print("ERROR run returned {0}. Output below.\n".format(result.returncode))
                    error_occured = True                
                    print(result.stdout)
                    break
                success = False
                for line in result.stdout.splitlines(): #read and store result in log file
                    if re.match('/{0}\s*:\s*success/'.format(benchmark)) != None: 
                        success = True
                        break;

                if not success:
                    print("Benchmark failed.\n");
                    return;

                #Process Output
                print('Parsing TA log...')
                cycles = -1
                with open("./configurations/{0}/output-{1}.c/ta.log.000".format(configuration,benchmark), 'r') as ta_log:
                    for line in ta_log:
                        matchobj = re.match("Execution Cycles:\s*([0-9]+)\s*\(.*\)",line)
                        if matchobj:
                            cycles = matchobj.group(0)
                            break;

                print("Running GPROF...")
                result = subprocess.run(["gprof", "a.out", "gmon-nocache.out"],stdout=subprocess.PIPE,universal_newlines=True,cwd="{0}/configurations/{1}/output-{2}.c/".format(main_dir,configuration,benchmark))
                if result.returncode != EXIT_SUCCESS:
                    print("ERROR gprof returned {0}. Output below.\n".format(result.returncode))
                    error_occured = True                
                    print(result.stdout)
                    break
                print("Parsing GPROF log...")
                with open("./configurations/{0}/output-{1}.c/gprof-nocache.txt".format(configuration,benchmark), 'w') as gprof_log:
                    gprof_log.write(result.stdout);
                    print("Written GPROF text format.")

                result = subprocess.run(["pcntl", "{0}.s".format(benchmark)],stdout=subprocess.PIPE,universal_newlines=True,cwd="{0}/configurations/{1}/output-{2}.c/".format(main_dir,configuration,benchmark))
                if result.returncode != EXIT_SUCCESS:
                    print("ERROR pcntl returned {0}. Output below.\n".format(result.returncode))
                    error_occured = True                
                    print(result.stdout)
                    break
                print("Parsing PCNTL summary...")
                with open("./configurations/{0}/output-{1}.c/{1}.s".format(configuration,benchmark), 'w') as pcntl_log:
                    pcntl_log.write(result.stdout);
                    print("Written PCNTL summary.")


                print("Benchmark metrics:\nExecution cycles: {0}".format(cycles));
                         


if __name__ == '__main__':
    parser = ap.ArgumentParser(prog='MCARunBenchmarks',description='MCA Benchmark Runner Script')
    #parser.add_argument('--disable-bench', action="store_true", help='Disable the benchmarks')
    #parser.add_argument('--disable-plot', action="store_true", help='Disable the plotting')
    #TODO report making
    #parser.add_argument('--output-dir', action="store", help='Output directory',default="../../../docs/lab2")
    #parser.add_argument('--output-dir', action="store", help='Output directory',default=".")
    try:
        opts = parser.parse_args(sys.argv[1:])
        output_dir_root = opts.output_dir;

        benchmarks = ['engine','fir']
        configurations = ['example-2-issue']
        flag_sets = ['-O3']

        ## Task 1
        RunBenchmark(configurations, benchmarks, flag_sets)

        print("Done.")
    except SystemExit:
        print('Bad Arguments')