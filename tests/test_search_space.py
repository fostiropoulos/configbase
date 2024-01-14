import re
from config.main import ConfigBase, config
from config.search_space.main import (
    CategoricalDistribution,
    Distribution,
    SearchSpace,
)

import numpy as np
import pytest


class Pass:
    def __init__(self, a=10) -> None:
        self.a = a

    def __repr__(self) -> str:
        return f"Pass(a={self.a})"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.a == other.a
        return False


@config
class ChildConfig3(ConfigBase):
    c: int = 5


class Noop:
    def __init__(self, *args, **kwargs) -> None:
        pass


@config
class E(ConfigBase):
    c: float = 0.1
    d: int = 5
    e: ChildConfig3 = ChildConfig3()
    g: float = 2


@config
class B(ConfigBase):
    e: E = E()
    c: int = 5
    d: Noop = Noop()


@config
class A(ConfigBase):
    b: B = B()
    d: float = 0.5


@config
class Master(ConfigBase):
    a: A = A()
    d: float = 0.5


def test_expand_search_space():
    n_bins = 5
    space = SearchSpace({"a": Distribution(-10, 10, 5)})
    len(space.expand()) == n_bins + 1
    assert (
        np.array([a["a"] for a in space.expand()]) == np.linspace(-10, 10, n_bins + 1)
    ).all()

    space = SearchSpace(
        {"a": Distribution(-10, 10, n_bins), "b": Distribution(-1, 1, n_bins)}
    )
    assert len(space.expand()) == (n_bins + 1) ** 2

    space = SearchSpace({
        "a": Distribution(-10, 10, n_bins),
        "b": Distribution(-1, 1, n_bins),
        "c": CategoricalDistribution(["a", "b"]),
    })

    assert len(space.expand()) == (n_bins + 1) ** 2 * 2

    space = SearchSpace({
        "a": Distribution(-10, 10, n_bins),
        "b": Distribution(-1, 1, n_bins),
        "c": CategoricalDistribution([Distribution(-1, 1, n_bins), "b"]),
    })

    assert len(space.expand()) == (n_bins + 1) ** 2 + (n_bins + 1) ** 3

    space = SearchSpace({
        "a": Distribution(-10, 10, n_bins),
        "b": Distribution(-1, 1, n_bins),
        "c": CategoricalDistribution([Distribution(-1, 1, n_bins), "b"]),
        "d": SearchSpace({"c": Distribution(-10, 10, n_bins)}),
    })

    assert len(space.expand()) == ((n_bins + 1) ** 2 + (n_bins + 1) ** 3) * (n_bins + 1)

    space = SearchSpace({
        "a": Distribution(-10, 10, n_bins),
        "b": Distribution(-1, 1, n_bins),
        "c": CategoricalDistribution([
            Distribution(-1, 1, n_bins),
            SearchSpace(
                {"c": Distribution(-10, 10, n_bins), "b": Distribution(-1, 1, n_bins)}
            ),
            "b",
        ]),
        "d": SearchSpace({"c": Distribution(-10, 10, n_bins)}),
    })

    assert len(space.expand()) == (
        (n_bins + 1) ** 2 + (n_bins + 1) ** 3 + (n_bins + 1) ** 4
    ) * (n_bins + 1)


def test_distribution():
    with pytest.raises(ValueError, match=re.escape("`n_bins` must be greater than 0.")):
        a = Distribution(-10, 10, 0)
    with pytest.raises(
        ValueError, match=re.escape("Invalid arguments. low>=high for Distribution.")
    ):
        a = Distribution(10, -10, 5)

    with pytest.raises(
        ValueError,
        match=re.escape("Invalid arguments. low>=0 when setting `log_scale` to 'True'"),
    ):
        a = Distribution(-10, 10, 5, log_scale=True)

    for n_bins in [1, 100, 200]:
        a = Distribution(-10, 10, n_bins)
        s = a.expand()
        assert a.contains(-10) and a.contains(10)
        assert a.contains("10")
        assert not a.contains(10.001)
        assert len(s) == n_bins + 1
        assert max(s) == 10 and min(s) == -10
        assert (np.array(sorted(s)) == np.array(s)).all()
        assert a.random_sample() in s

    n_bins = 200
    a = Distribution(-10, 10.01, n_bins)
    assert a.contains(10.001)
    a = Distribution(-10, 10.01, n_bins, dtype="int")
    assert a.contains(10.001)
    assert a.high == 10
    assert a.low == -10
    assert len(a.expand()) == 21
    assert (np.array(a.expand()) == np.arange(21) - 10).all()

    a = Distribution(0.1, 10, n_bins, log_scale=True)
    assert (a.expand() == np.geomspace(0.1, 10, n_bins + 1)).all()
    assert min(a.expand()) == 0.1 and max(a.expand()) == 10


def test_cat_distribution():
    with pytest.raises(
        ValueError,
        match=re.escape("Must provide at least one item for CategoricalDistribution"),
    ):
        a = CategoricalDistribution([])

    items = ["a", 0, {"xx": "xx"}, Pass()]
    a = CategoricalDistribution(items)
    s = a.expand()
    assert s == items
    assert a.random_sample() in s
    assert a.contains(0)
    assert not a.contains(1)


def test_expand_config():
    uniform = Distribution(0, 1, 1)
    uniform_int = Distribution(0, 10, 1, dtype="int")
    s = SearchSpace({
        "a.b.c": uniform,
        "a.b.e": CategoricalDistribution([
            {"d": uniform},
            {"d": uniform_int},
            SearchSpace({"d": uniform, "g": uniform_int}),
            {"c": 1},
        ]),
        "a.b.d": CategoricalDistribution([{"aa": "b"}]),
        "d": 0.1,
    })

    m = Master()
    configs = m.expand(s)
    assert len(configs) == 18
    removed_config = []
    i = 0
    while len(configs) > 0 and i < 10_000:
        c = m.sample(s)
        i += 1
        if c in removed_config and c not in configs:
            continue
        configs.remove(c)
        removed_config.append(c)
    assert len(configs) == 0


if __name__ == "__main__":
    from conftest import run_tests_local
    import conftest

    _locals = locals()
    run_tests_local(_locals, conftest)
