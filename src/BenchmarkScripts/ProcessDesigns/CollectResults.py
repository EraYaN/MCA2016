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