from collections import abc
import typing as ty


import copy

import numpy as np


class Distribution:
    """
     Distribution class that represents a numerical distribution within
     a specified range and step interval.

    Parameters
    ----------
    low : int | float
        the lower range of the distribution. It is inclusive.
    high : int | float
        the upper range of the distribution. It is inclusive.
    n_bins : int
        the number of discritization intervals, aka `bins`, from which to sample.
    log_scale : bool, optional
        whether to sample from the log-scale. It implies that there is a higher probability
        to sample values on the lower range. When setting to true, `low` must be >=0, by default False
    dtype : str, optional
        the data-type of the distribution must be `float` or `int`, by default "float"

    Raises
    ------
    ValueError
        When unsupported `dtype` is provided.
    ValueError
        When `n_bins` is not > 0
    ValueError
        When low>=high
    ValueError
        When `log_scale` is ``True`` but low is not >= 0
    """

    low: int | float
    high: int | float
    n_bins: int
    dtype: type = float
    log_scale: bool = False

    def __init__(
        self,
        low: int | float,
        high: int | float,
        n_bins: int,
        log_scale: bool = False,
        dtype: str = "float",
    ) -> None:

        if dtype not in {"float", "int"}:
            raise ValueError("Support only for `float` and `int` distribution.")
        self.n_bins = int(n_bins)
        if self.n_bins <= 0:
            raise ValueError("`n_bins` must be greater than 0.")
        # pylint: disable=eval-used
        self.dtype = eval(dtype)
        self.log_scale = log_scale

        self.low = self.dtype(low)
        self.high = self.dtype(high)
        if self.low > self.high:
            raise ValueError(f"Invalid arguments. low>=high for {type(self).__name__}.")
        if self.log_scale and self.low <= 0:
            raise ValueError(
                "Invalid arguments. low>=0 when setting `log_scale` to 'True'"
            )

    def expand(self) -> list[float | int]:
        space_fn: abc.Callable
        if not self.log_scale:
            space_fn = np.linspace
        else:
            space_fn = np.geomspace
        return sorted(
            list(
                set(
                    space_fn(self.low, self.high, num=self.n_bins + 1).astype(
                        self.dtype
                    )
                )
            )
        )

    def random_sample(self) -> float | int:
        return self.dtype(np.random.choice(self.expand()))

    def contains(self, value: int | float | str) -> bool:
        return self.dtype(value) >= self.low and self.dtype(value) <= self.high


class CategoricalDistribution:
    """
    CategoricalDistribution represents discrete outcomes that can be indepedent of each other.
    For example, one can sample two entirely different sub-configurations. It can be thought
    as implementing conditional logic.

    Parameters
    ----------
    choices : list[ty.Any]
        the number of discrete outcomes to sample from. The items can be of any type and
        inhomegenous types.

    Raises
    ------
    ValueError
        When choices does not contain any elements.
    """

    choices: list

    def __init__(self, choices: list[ty.Any]) -> None:

        self.choices = list(choices)
        if len(self.choices) == 0:
            raise ValueError(
                f"Must provide at least one item for {type(self).__name__}"
            )

    def expand(self) -> list:
        return self.choices

    def random_sample(self):
        idx = np.random.choice(np.arange(len(self.choices)))
        return self.choices[idx]

    def contains(self, value):
        return value in self.choices


class SearchSpace:
    def __init__(
        self, search_space: dict[str, Distribution | CategoricalDistribution]
    ) -> None:
        self.search_space = search_space

    def expand(self):
        return expand_dict(self.search_space)

    def sample(
        self,
        sample_fn=None,
        prefix: str = "",
    ):
        if sample_fn is None:
            sample_fn = random_sample

        def _sample_params(
            kwargs,
            prefix: str = "",
        ):
            if isinstance(kwargs, CategoricalDistribution):
                kwargs = sample_fn(name=prefix, dist=kwargs)
            if isinstance(kwargs, dict):
                return {
                    _k: _sample_params(_v, prefix=f"{prefix}.{_k}")
                    for _k, _v in kwargs.items()
                }
            if isinstance(kwargs, Distribution):
                return sample_fn(name=prefix, dist=kwargs)
            if isinstance(kwargs, SearchSpace):
                return {
                    _k: _sample_params(_v, prefix=f"{prefix}.{_k}")
                    for _k, _v in kwargs.search_space.items()
                }
            return kwargs

        return _sample_params(self, prefix=prefix)


# pylint: disable=unused-argument
def random_sample(name, dist: Distribution | CategoricalDistribution):
    return dist.random_sample()


def expand_item(
    configs: list[dict[str, str | int | float | dict]],
    value: (
        dict[str, Distribution | CategoricalDistribution | ty.Any]
        | SearchSpace
        | ty.Any
    ),
    key,
) -> list:
    _configs = []
    expanded_space: list[ty.Any]
    if isinstance(value, dict):
        expanded_space = expand_dict(value)
    elif isinstance(value, SearchSpace):
        expanded_space = expand_dict(value.search_space)
    elif isinstance(value, Distribution):
        expanded_space = value.expand()
    elif isinstance(value, CategoricalDistribution):
        return [c for i in value.expand() for c in expand_item(configs, i, key)]
    elif isinstance(value, list):
        expanded_space = value
    else:
        expanded_space = [value]
    for _config in configs:
        for _v in expanded_space:
            _config[key] = _v
            _configs.append(copy.deepcopy(_config))
    return _configs


def expand_dict(
    search_space: dict[str, Distribution | CategoricalDistribution | ty.Any]
) -> list[dict[str, str | int | float | dict]]:
    configs: list[dict[str, str | int | float | dict]] = [{}]

    for k, v in search_space.items():
        try:
            configs = expand_item(configs, v, k)
        except ValueError as e:
            raise ValueError(f"Invalid search space for {k}. {str(e)}") from e
    return configs
