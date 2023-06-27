"""benchmark various types of object containers"""

import dataclasses
import json
import sys
import timeit
from collections import namedtuple, defaultdict
from typing import Callable

import arguably
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pydantic

RUNS = 1000
data: tuple[tuple[int], tuple[int], tuple[int], tuple[int]] | None = None

results: dict[str, list[float]] = defaultdict(list)


def inject_pydantic_v2_results():
    raise Exception("Pydantic V2 numbers will need to be updated if you run on your machine!!!")
    # To get results for V2: `poetry remove pydantic` && `poetry add --allow-prereleases pydantic`
    results["pydantic-v2"].extend([1.56, 0.531, 0.594])


def data_to_items(t, f, g, h, i):
    return [t(x=fi.item(), y=gi.item(), z=hi.item(), heading=ii.item()) for fi, gi, hi, ii in zip(f, g, h, i)]


def time_run(group: str, trial: str, func: Callable) -> float:
    duration = timeit.Timer(func).timeit(number=RUNS)
    avg_duration = duration / RUNS
    print(f"{group} - {trial}: {duration:.3} total, {avg_duration:.3} avg")
    results[group].append(duration)
    return duration


########################################################################################################################
# dataclasses

@dataclasses.dataclass
class DCCoord:
    x: int
    y: int
    z: int
    heading: int


@dataclasses.dataclass
class DCCoords:
    coords: list[DCCoord]


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


@arguably.command
def dataclass_():
    """benchmark dataclasses"""
    global data
    if data is None:
        data = np.random.randint(0, 100, size=(4, 15), dtype=int)
    xs, ys, zs, headings = data

    create = lambda: DCCoords(coords=data_to_items(DCCoord, xs, ys, zs, headings))
    serialize = lambda: json.dumps(coords, separators=(",", ":"), cls=EnhancedJSONEncoder)
    deserialize = lambda: DCCoords(coords=[DCCoord(**x) for x in json.loads(serialized)["coords"]])

    coords = create()
    serialized = serialize()
    print(f"{sys.getsizeof(coords)=}")
    print(coords)
    print(deserialize())

    time_run("dataclass", "create", create)
    time_run("dataclass", "serialize", serialize)
    time_run("dataclass", "deserialize", deserialize)
    print()


########################################################################################################################
# pydantic

@pydantic.dataclasses.dataclass
class PDCoord:
    x: int
    y: int
    z: int
    heading: int


@pydantic.dataclasses.dataclass
class PDCoords:
    coords: list[PDCoord]


@arguably.command
def pydantic_():
    """benchmark pydantic (can be v1 or v2)"""
    global data
    if data is None:
        data = np.random.randint(0, 100, size=(4, 15), dtype=int)
    xs, ys, zs, headings = data

    create = lambda: PDCoords(coords=data_to_items(PDCoord, xs, ys, zs, headings))
    if hasattr(pydantic, "RootModel"):
        group = "pydantic-v2"
        serialize = lambda: pydantic.RootModel[PDCoords](coords).model_dump_json()
        deserialize = lambda: pydantic.RootModel[PDCoords].model_validate_json(serialized)
    else:
        inject_pydantic_v2_results()
        from pydantic.json import pydantic_encoder
        group = "pydantic-v1"
        serialize = lambda: json.dumps(coords, default=pydantic_encoder)
        deserialize = lambda: PDCoords.__pydantic_model__.parse_raw(serialized)

    coords = create()
    serialized = serialize()
    print(f"{sys.getsizeof(coords)=}")
    print(coords)
    print(deserialize())

    time_run(group, "create", create)
    time_run(group, "serialize", serialize)
    time_run(group, "deserialize", deserialize)
    print()


########################################################################################################################
# namedtuple

NTCoord = namedtuple("NTCoord", "x y z heading")
NTCoords = namedtuple("NTCoords", "coords")


@arguably.command
def namedtuple_():
    """benchmark namedtuple"""
    global data
    if data is None:
        data = np.random.randint(0, 100, size=(4, 15), dtype=int)
    xs, ys, zs, headings = data

    create = lambda: NTCoords(coords=data_to_items(NTCoord, xs, ys, zs, headings))
    serialize = lambda: json.dumps(coords._asdict(), separators=(",", ":"))
    deserialize = lambda: NTCoords(coords=[NTCoord(*x) for x in json.loads(serialized)["coords"]])

    coords = create()
    serialized = serialize()
    print(f"{sys.getsizeof(coords)=}")
    print(coords)
    print(deserialize())

    time_run("namedtuple", "create", create)
    time_run("namedtuple", "serialize", serialize)
    time_run("namedtuple", "deserialize", deserialize)
    print()


########################################################################################################################
# all

@arguably.command
def __root__(*, runs: int = 50000):
    global RUNS
    RUNS = runs

    if arguably.is_target:
        namedtuple_()
        dataclass_()
        pydantic_()


if __name__ == "__main__":
    arguably.run()

    df = pd.DataFrame(
        [[group, *data] for group, data in results.items()],
        columns=["Implementation", "create", "serialize", "deserialize"]
    )

    df.plot(
        x="Implementation",
        kind="bar",
        stacked=False,
        title="Test results",
        rot=0,
        ylabel=f"Seconds for {RUNS} iters"
    )

    plt.show()
