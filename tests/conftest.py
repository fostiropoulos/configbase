import copy
import inspect
import io
import logging
import random
import typing as ty
from collections import abc
from pathlib import Path

import numpy as np
import pytest



def _capture_logger():
    out = io.StringIO()
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler(out))
    return out


@pytest.fixture
def capture_logger():
    return _capture_logger


def fns_requires_kwargs(
    test_fns: list[abc.Callable], *kwarg_names, **existing_kwargs
) -> bool:
    """
    Check whether the fns require any of the `kwargs_names` that is not
    present in the `existing_kwargs`. Used when a kwarg_name is missing to
    create it.

    Parameters
    ----------
    test_fns : list[abc.Callable]
        the functions inspect and determine their arguments
    kwarg_names : tuple[str]
        name of the kwarg arguments to find in the function signature
    existing_kwargs : dict[str, ty.Any]
        the existing kwargs provided

    Returns
    -------
    bool
        whether any of the kwarg_names is required by any of the test_fns.
    """
    return any([
        p in list(kwarg_names) and p not in existing_kwargs
        for fn in test_fns
        for p in inspect.signature(fn).parameters
    ])


def run_tests_local(
    locals: dict,
    conftest: ty.Type,
    kwargs: dict[str, ty.Any] = None,
    unpickable_kwargs: dict[str, ty.Any] = None,
    tmp_path: Path | None = None,
):
    """
    Meant as a helper function for debugging tests. This helper also
    contains logic on how the tests are expected to run and how
    ablator is meant to be used. i.e. we first set-up the cluster and
    then run experiments. Essentially re-implements `pytest` but with
    the ability to run using a debugger. It can be difficult to debug
    tests and test-fixtures using debugging in pytest.

    Parameters
    ----------
    test_fns : list[abc.Callable]
        the functions to test
    kwargs : dict[str, ty.Any], optional
        the kwargs to pass to the functions. If a key matches that of the
        function signature parameter it is passed. These arguments are `deepcopy`'d for
        each function call, by default None
    unpickable_kwargs : dict[str, ty.Any], optional
        Similar to `kawrgs` but these kwargs can not be `deepcopy`d since they are not pickable
        hence they are passed unchanged on every test_fn call, by default None

    Raises
    ------
    ValueError
        If there is a missing keyword-argument in the `kwargs`
    """
    random.seed(1)
    np.random.seed(1)
    import shutil

    fn_names = [fn for fn in locals if fn.startswith("test_")]
    test_fns = [locals[fn] for fn in fn_names]
    if kwargs is None:
        kwargs = {}

    if unpickable_kwargs is None:
        unpickable_kwargs = {}

    for fn in test_fns:
        parameters = inspect.signature(fn).parameters
        if tmp_path is None:
            tmp_path = Path("/tmp/test_exp")

        default_kwargs = {
            "tmp_path": tmp_path,
        }

        if hasattr(fn, "pytestmark"):
            for mark in fn.pytestmark:
                if mark.name == "parametrize":
                    k, v = mark.args
                    default_kwargs[k] = v

        for k, v in kwargs.items():
            unpickable_kwargs[k] = lambda: copy.deepcopy(kwargs[k])

        _run_args = [{}]

        for k, v in parameters.items():
            if k in unpickable_kwargs:
                continue
            if k not in default_kwargs and v.default != inspect._empty:
                default_kwargs[k] = v.default
                for _args in _run_args:
                    _args[k] = default_kwargs[k]
            elif k not in default_kwargs and hasattr(conftest, f"_{k}"):
                _args[k] = getattr(conftest, f"_{k}")
            elif k not in default_kwargs and hasattr(conftest, k):
                _args[k] = getattr(conftest, k)
            elif k not in default_kwargs:
                raise ValueError(f"Missing kwarg {k}.")
            elif isinstance(default_kwargs[k], (list, tuple, set, dict)):
                __run_args = copy.deepcopy(_run_args)
                _run_args = []
                for _args in __run_args:
                    for _v in default_kwargs[k]:
                        _args[k] = _v
                        _run_args.append(copy.deepcopy(_args))
            else:
                for _args in _run_args:
                    _args[k] = default_kwargs[k]

        for _args in _run_args:
            shutil.rmtree(tmp_path, ignore_errors=True)
            tmp_path.mkdir()
            for k, v in unpickable_kwargs.items():
                if k in parameters:
                    _args[k] = unpickable_kwargs[k]()
            fn(**_args)
