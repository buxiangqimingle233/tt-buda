import pybuda
import torch
from smoke_test import PyTorchTestModule
import os


# TODO: We do not need this, the device yaml is already copied to workspace/tt_build, use a search path func instead
# arch_name_to_config_path = {
#     "Grayskull": "/home/tt-buda/third_party/budabackend/device/grayskull_10x12.yaml",
#     "Wormhole_B0": "/home/tt-buda/third_party/budabackend/device/wormhole_b0_8x10.yaml",
#     "Blackhole": "/home/tt-buda/third_party/budabackend/device/blackhole_10x14_no_eth.yaml",
# }

# No harvesting architecture for now
arch_name_to_pybuda = {
    "Grayskull": pybuda.BackendDevice.Grayskull,
    "Wormhole_B0": pybuda.BackendDevice.Wormhole_B0,
    "Blackhole": pybuda.BackendDevice.Blackhole,
}

def find_yaml_files(directory):
    return [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith(".yaml")]


def benchmark_decorator(func):
    def wrapper():
        model, inputs, arch_name, envs = func()
        if "task_name" not in envs:
            envs["task_name"] = func.__name__
        return model, inputs, arch_name, envs
    return wrapper


@benchmark_decorator
def smoke_test():
    module = PyTorchTestModule()
    input1 = torch.rand(4, 128, 32)
    input2 = torch.rand(4, 128, 32)
    arch = "Wormhole_B0"

    return module, (input1, input2), arch, {}


@benchmark_decorator
def bert_large():
    from transformers import BertForQuestionAnswering, BertTokenizer

    tokenizer = BertTokenizer.from_pretrained("google-bert/bert-large-cased-whole-word-masking-finetuned-squad")
    model = BertForQuestionAnswering.from_pretrained("google-bert/bert-large-cased-whole-word-masking-finetuned-squad")

    context = """Super Bowl 50 was an American football game to determine the champion of the National Football League
    (NFL) for the 2015 season. The American Football Conference (AFC) champion Denver Broncos defeated the
    National Football Conference (NFC) champion Carolina Panthers 24\u201310 to earn their third Super Bowl title.
    The game was played on February 7, 2016, at Levi's Stadium in the San Francisco Bay Area at Santa Clara, California.
    As this was the 50th Super Bowl, the league emphasized the \"golden anniversary\" with various gold-themed
    initiatives, as well as temporarily suspending the tradition of naming each Super Bowl game with Roman numerals
    (under which the game would have been known as \"Super Bowl L\"), so that the logo could prominently
    feature the Arabic numerals 50."""

    question = "Which NFL team represented the AFC at Super Bowl 50?"

    # Data preprocessing
    input_tokens = tokenizer(
        question,  # pass question
        context,  # pass context
        max_length=384,  # set the maximum input context length
        padding="max_length",  # pad to max length for fixed input size
        truncation=True,  # truncate to max length
        return_tensors="pt",  # return PyTorch tensor
    )

    arch = "Wormhole_B0"

    return model, input_tokens, arch, {}


benchmark_map = {
    "smoke_test": smoke_test,
    "bert_large": bert_large,
}