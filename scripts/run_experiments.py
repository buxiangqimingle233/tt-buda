import argparse
import os, os.path, sys
import torch
import subprocess

# BUDA_HOME = "/usr/local/lib/python3.8/dist-packages/budabackend"
PROJECT_HOME = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))       # The root directory of the project
RESULT_HOME = os.path.join(PROJECT_HOME, "results")                               # The directory to store the results
NET2PIPE_PATH = os.path.join(PROJECT_HOME, "pybuda/pybuda/tools/run_net2pipe.py")
BUDA_HOME = os.path.join(PROJECT_HOME, "env/lib/python3.8/site-packages/budabackend")

sys.path.append(PROJECT_HOME)

import pybuda
from netlist_parser.gen_nt_trace import generate_trace
from netlist_parser.tt_simple_netlist import SimpleNetList
from netlist_parser.tt_device import Device
from benchmarks import benchmark_map
from benchmarks import arch_name_to_pybuda, find_yaml_files


if not os.path.exists(RESULT_HOME):
    os.mkdir(RESULT_HOME)
    

def gen_netlist(task_name: str, model: torch.nn.Module, inputs, arch_pybuda, workdir):
    org_path = os.getcwd()
    os.chdir(workdir)
    
    compiler_cfg = pybuda.config._get_global_compiler_config()
    compiler_cfg.default_df_override = pybuda._C.DataFormat.Float16_b
    compiler_cfg.default_dram_parameters = False
    compiler_cfg.balancer_policy = "Ribbon"
    os.environ["PYBUDA_RIBBON2"] = "1"
    os.environ["TT_BACKEND_OVERLAY_MAX_EXTRA_BLOB_SIZE"] = "73728"
    os.environ["BUDA_HOME"] = BUDA_HOME

    # enable net2pipe
    os.environ["PYBUDA_VERIFY_NET2PIPE"] = "3"                  # pipegen = 2, blobgen = 3, statsgen = 4
    os.environ["PYBUDA_AUTO_RECOMPILE"] = "1"                   # enable recompile if the blob size is not enough
    os.environ["PYBUDA_AUTO_RECOMPILE_TARGET_CYCLES"] = "1"     

    # enable reportify
    os.environ["LOGURU_LEVEL"] = "ERROR"
    os.environ['LOGGER_LEVEL'] = 'Error'
    os.environ["HOME"] = workdir
    os.environ["PYBUDA_DISABLE_REPORTIFY_DUMP"] = "0"
    


    tt0 = pybuda.TTDevice(
        name="tt_device_0",  # here we can give our device any name we wish, for tracking purposes
        arch=arch_pybuda,  # we set the target device architecture to compile for
        devtype=pybuda.BackendType.Golden  # we set the target backend type to be Golden for running off device
    )

    pybuda_module = pybuda.PyTorchModule(name=task_name, module=model)

    tt0.place_module(module=pybuda_module)
    tt0.push_to_inputs(inputs)
    
    pybuda.initialize_pipeline(training=False)
    pybuda.shutdown()

    os.chdir(org_path)


def parse_netlist(task_name: str, arch_name: str, devconfig_path: str, workdir: str):
    # netlist_file_path = os.path.join(workdir, f"{task_name}_netlist.yaml")  # FIXME: the netlist file path is not exactly the concatanation

    netlist_file_path = find_yaml_files(workdir)[0]

    # Execute tt-buda backend to generate pipe and blob files
    # We have compiled it at the gen_netlist step
    # cmd = f"python {NET2PIPE_PATH} --run-pipegen --run-blobgen --device-yaml={devconfig_path} {netlist_file_path}"
    # # print(cmd)
    # print(f"Invoke pybuda backend, executing command: {cmd}")
    
    # process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # output, err = process.communicate()

    # if "OK" not in output.decode("utf-8"):
    #     print(err.decode("utf-8"))
    #     raise ValueError(f"Failed to generate file {netlist_file_path}")

    # Parse the netlist as well as pipes then generate netrace files
    simple_list = SimpleNetList(
        netlist_filepath=netlist_file_path,
        rundir=os.path.join(workdir, "net2pipe_output"),
        devices=Device.create(arch_name, 0, {}, devconfig_path, None)
    )

    with open("netrace.trace", "w") as of: 
        generate_trace(simple_list, of)


def run_single_task(model, inputs, arch_name, envs):
    os.environ["BUDA_HOME"] = BUDA_HOME

    task_name = envs["task_name"]

    print("Running test for job: {}".format(task_name))
    
    workdir = os.path.join(RESULT_HOME, task_name)
    if not os.path.exists(workdir):
        os.mkdir(workdir)
    
    arch_pybuda = arch_name_to_pybuda[arch_name]
    gen_netlist(task_name, model, inputs, arch_pybuda, workdir)

    devconfig_path = find_yaml_files(os.path.join(workdir, "tt_build/test_out/device_descs"))[0]
    parse_netlist(task_name, arch_name, devconfig_path, workdir)


# def run_all(benchmark_name):
#     tasks = benchmark_map[benchmark_name]()

#     for model, arch, envs in tasks:
#         print(f"Running benchmark {envs["task_name"]}")
#         run_single_task(model, arch, envs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run an experiment.')
    parser.add_argument('experiment', type=str, help='The name of the experiment to run')

    args = parser.parse_args()

    if args.experiment in benchmark_map:
        # run_all(args.experiment)
        run_single_task(*benchmark_map[args.experiment]())
    else:
        print(f"Experiment {args.experiment} not found. Available experiments are: {list(benchmark_map.keys())}")
