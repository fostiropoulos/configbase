import typing as ty
from config.main import ConfigBase, configclass

import copy
import typing as ty
import numpy as np


class Distribution:
    low: int | float
    high: int | float
    n_bins: int | float
    dtype: ty.Type = float
    log_scale: bool = False

    def __init__(self, low, high, n_bins, log_scale=False, dtype: str = "float") -> None:

        if dtype not in {"float", "int"}:
            raise ValueError("Support only for `float` and `int` distribution.")
        self.n_bins = int(n_bins)
        if self.n_bins <= 0:
            raise ValueError("`n_bins` must be greater than 0.")
        self.dtype = eval(dtype)
        self.log_scale = log_scale

        self.low = self.dtype(low)
        self.high = self.dtype(high)
        if self.low > self.high:
            raise ValueError(f"Invalid arguments. low>=high for {type(self).__name__}.")
        if self.log_scale and self.low <= 0:
            raise ValueError("Invalid arguments. low>=0 when setting `log_scale` to 'True'")

    def expand(self) -> list[float | int]:
        if not self.log_scale:
            space_fn = np.linspace
        else:
            space_fn = np.geomspace
        return sorted(list(set(space_fn(self.low, self.high, num=self.n_bins + 1).astype(self.dtype))))

    def random_sample(self) -> float | int:
        return self.dtype(np.random.choice(self.expand()))

    def contains(self, value: int | float | str) -> bool:
        return self.dtype(value) >= self.low and self.dtype(value) <= self.high


class CategoricalDistribution:
    choices: list

    def __init__(self, choices) -> None:
        self.choices = list(choices)
        if len(self.choices) == 0:
            raise ValueError(f"Must provide at least one item for {type(self).__name__}")

    def expand(self) -> list:
        return self.choices

    def random_sample(self):
        idx = np.random.choice(np.arange(len(self.choices)))
        return self.choices[idx]

    def contains(self, value):
        return value in self.choices


class SearchSpace:
    def __init__(self, search_space: dict[str, Distribution | CategoricalDistribution]) -> None:
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
                return {_k: _sample_params(_v, prefix=f"{prefix}.{_k}") for _k, _v in kwargs.items()}
            if isinstance(kwargs, Distribution):
                return sample_fn(name=prefix, dist=kwargs)
            if isinstance(kwargs, SearchSpace):
                return {_k: _sample_params(_v, prefix=f"{prefix}.{_k}") for _k, _v in kwargs.search_space.items()}
            return kwargs

        return _sample_params(self, prefix=prefix)


def random_sample(name, dist: Distribution | CategoricalDistribution):
    return dist.random_sample()


def expand_item(
    configs: list[dict[str, str | int | float | dict]],
    value: dict[str, SearchSpace] | SearchSpace | ty.Any,
    key,
) -> list:
    _configs = []
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


def expand_dict(search_space: dict[str, "SearchSpace"]) -> list[dict[str, str | int | float | dict]]:
    configs: list[dict[str, str | int | float | dict]] = [{}]

    for k, v in search_space.items():
        try:
            configs = expand_item(configs, v, k)
        except ValueError as e:
            raise ValueError(f"Invalid search space for {k}. {str(e)}") from e
    return configs
