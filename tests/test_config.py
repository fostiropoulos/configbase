import ast
import copy
import io
from pathlib import Path
import re


import pytest

from config import (
    Annotation,
    Derived,
    Dict,
    Enum,
    Optional,
    Stateful,
    Stateless,
    Type,
    config,
)
from config.types import List
from config.utils import parse_repr_to_kwargs


from config.utils import flatten_nested_dict


class BadClassAll:
    def __init__(self, a) -> None:
        self.a = a

    def to_dict(self):
        # this is correct
        return {"b": self.a}

    def as_dict(self):
        # this is not, no argument b
        return {"b": self.a}

    @property
    def __dict__(self):
        # this is not, no argument b
        return {"b": 1000}

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, type(self)):
            return __value.a == self.a
        return False


class GoodClassAsDict(BadClassAll):
    def as_dict(self):
        # should be correct
        return {"a": self.a}


class GoodClassToDict(BadClassAll):
    def to_dict(self):
        # this is correct
        return {"a": self.a}


class GoodClassDict(BadClassAll):
    @property
    def __dict__(self):
        # this is not, no argument b
        return {"a": 10}


class BadClassDict:
    def __init__(self, a) -> None:
        self.a = a

    @property
    def __dict__(self):
        # this is not, no argument b
        return {"b": 1000}


class BadClassRerpr(BadClassDict):
    def __init__(self, a) -> None:
        self.a = a

    def __repr__(self) -> str:
        # this is valid
        return f"BadClass(a={self.a+1})"


error_representation_classes = [
    BadClassRerpr,
    BadClassAll,
    BadClassDict,
]


partial_error_representation_classes = [
    GoodClassAsDict,
    GoodClassDict,
    GoodClassToDict,
]


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
class SimpleConfig:
    a1: int = 10


class myEnum(Enum):
    A = "a"


@config
class ParentTestConfig:
    a1: int = 10
    a2: str = 10
    a8: Derived[Optional[str]] = 10

    a9: Derived[Optional[Dict[str]]]

    a5: Pass = Pass()
    c2: SimpleConfig = SimpleConfig()
    a10: Stateless[str]
    a6: myEnum = "a"


@config
class ParentTestConfig2(ParentTestConfig):
    a10: Stateless[int] = 10


@config
class ParentTestConfig3(ParentTestConfig):
    a6: Pass = Pass()
    a2: int = 5
    a1: str = "5"
    a10: str = "10"


@config
class ParentTestConfig4(ParentTestConfig3):
    b1: Pass


@config
class NestedParentConfig:
    b1: ParentTestConfig4
    a1: str


@config
class NestedParentConfig2:
    b1: ParentTestConfig3


class ForwardConfig(NestedParentConfig2):
    forward_ref: "NestedParentConfigInit"


# missing decorator
class NestedParentConfigInit(NestedParentConfig2):
    b1: ParentTestConfig2 = ParentTestConfig2()


@config
class DictEnumConfig:
    a: Dict[myEnum]
    p: Path = Path("/tmp/")

    p2: List[Path]


annotations = {
    "a1": Annotation(
        state=Stateful, optional=False, collection=None, variable_type=int
    ),
    "a2": Annotation(
        state=Stateful, optional=False, collection=None, variable_type=str
    ),
    "a8": Annotation(state=Derived, optional=True, collection=None, variable_type=str),
    "a9": Annotation(state=Derived, optional=True, collection=Dict, variable_type=str),
    "a10": Annotation(
        state=Stateless, optional=False, collection=None, variable_type=str
    ),
    "a5": Annotation(
        state=Stateful, optional=False, collection=Type, variable_type=Pass
    ),
    "a6": Annotation(
        state=Stateful, optional=False, collection=myEnum, variable_type=["a"]
    ),
    "c2": Annotation(
        state=Stateful, optional=False, collection=Type, variable_type=SimpleConfig
    ),
}


@config
class EmptyConfig:
    pass


def test_attrs(tmp_path: Path):
    e = EmptyConfig()
    e.annotations
    assert len(e.annotations) == 0
    with pytest.raises(ValueError, match=re.escape("Missing required values ['a10'].")):
        ParentTestConfig()
    p = ParentTestConfig(a10="")
    # NOTE: to make new test cases:
    # print({k:f"Annotation(state={v.state.__name__},
    # optional={v.optional}, collection={v.collection},
    # variable_type={v.variable_type.__name__})"
    # for k,v in p.annotations.items()})
    for k, v in p.annotations.items():
        assert annotations[k] == v
    assert list(p.keys()) == list(p.annotations.keys())
    p.a10 = "10"
    p.write(tmp_path.joinpath("test.yaml"))
    loaded_p = p.load(tmp_path.joinpath("test.yaml"))

    assert loaded_p.to_dot_path() == p.to_dot_path()
    assert len(loaded_p.diff(p)) == 0
    assert loaded_p.uid == p.uid
    p.freeze()
    p.write(tmp_path.joinpath("test.yaml"))
    loaded_p = p.load(tmp_path.joinpath("test.yaml"))
    assert len(loaded_p.diff(p)) == 0
    assert loaded_p.uid == p.uid
    loaded_p = ParentTestConfig2.load(tmp_path.joinpath("test.yaml"))
    assert len(loaded_p.diff(p)) == 1
    assert len(loaded_p.diff(p, ignore_stateless=True)) == 0
    assert loaded_p.uid == p.uid
    loaded_p.a10 = 2
    diffs = sorted(loaded_p.diff(p))
    var_name, (left_type, left_val), (right_type, right_val) = diffs[0]
    assert (
        var_name == "a10"
        and left_val == 2
        and left_type == int
        and right_type == str
        and right_val == "10"
    )
    loaded_p.c2.a1 = 4
    diff_str = loaded_p.diff_str(p)
    assert len(diff_str) == 2 and [
        "a10:(int)2->(str)10",
        "c2.a1:(int)4->(int)10",
    ] == sorted(diff_str)

    assert set(loaded_p.to_dot_path().split("\n")) == set(
        "a10: 2\na1: 10\na2: '10'\na8: '10'\na9: null\na6: a\na5.a: 10\nc2.a1: 4\n"
        .split("\n")
    )
    assert loaded_p.get_val_with_dot_path("a10") == 2
    assert loaded_p.get_type_with_dot_path("a10") == int
    assert loaded_p.get_annot_type_with_dot_path("a10") == int
    assert loaded_p.get_val_with_dot_path("c2.a1") == 4
    assert loaded_p.get_type_with_dot_path("c2.a1") == int
    assert loaded_p.get_annot_type_with_dot_path("c2.a1") == int
    assert p.get_val_with_dot_path("a10") == "10"
    assert p.get_type_with_dot_path("a10") == str

    p_prime = copy.deepcopy(loaded_p)
    p_prime.a10 = 100
    loaded_p.a10 = 2

    assert loaded_p.a10 == 2 and p_prime.a10 == 100

    loaded_p.a5.a = 2
    p_prime.a5.a = 100
    assert loaded_p.a5.a == 2 and p_prime.a5.a == 100

    loaded_p.c2.a1 = 2
    p_prime.c2.a1 = 100
    assert loaded_p.c2.a1 == 2 and p_prime.c2.a1 == 100

    p2 = NestedParentConfigInit()
    assert p2.annotations["b1"].variable_type == ParentTestConfig2
    with pytest.raises(ValueError, match="Does not support forward"):
        fp = ForwardConfig(forward_ref=p2)


def test_set_attr():
    c = ParentTestConfig(a10="")
    c.a2 = 1.231
    assert isinstance(c.a2, str) and c.a2 == "1.231"

    c.a1 = 1.999
    assert isinstance(c.a1, int) and c.a1 == 1

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            f"{Pass} provided args or kwargs (0) must be formatted as (args, kwargs) or"
            " (args) or (kwargs)."
        ),
    ):
        c.a5 = 0

    c.a5 = {"a": 1}
    assert c.a5.a == 1
    c.a5 = {"a": 5}
    assert c.a5.a == 5


def test_inheritence():
    with pytest.raises(
        ValueError,
        match=re.escape("Can not over-ride protected function name `__init__`."),
    ):

        @config
        class C:
            a: int = 5

            def __init__(self) -> None:
                pass

    @config
    class C2:
        a: int = 5

    c = C2(a=4)
    assert c.a == 4


def test_freeze_unfreeze():
    c = copy.deepcopy(ParentTestConfig(a10=""))
    c.freeze()
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Can not set attribute a10 on frozen configuration ``ParentTestConfig``."
        ),
    ):
        c.a10 = "1"
    c.unfreeze()
    c.a10 = "1"
    c.freeze()

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Can not set attribute a10 on frozen configuration ``ParentTestConfig``."
        ),
    ):
        c.a10 = "1"
    # this should not be allowed.
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Can not set attribute a on a class of a frozen configuration ``Pass``."
        ),
    ):
        c.a5.a = 0

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Can not set attribute a1 on frozen configuration ``SimpleConfig``."
        ),
    ):
        c.c2.a1 = 0
    c.unfreeze()

    c.a5.a = 54
    assert c.a5.a == 54

    c.c2.a1 = 52
    assert c.c2.a1 == 52


def test_parse_repr():
    for error_class in error_representation_classes:
        with pytest.raises(
            RuntimeError,
            match=(
                f"Could not parse <class '{__name__}.{error_class.__name__}'> from its"
                " representation "
            ),
        ):
            parse_repr_to_kwargs(error_class(a=10))

    for c in [
        ParentTestConfig(a10="1"),
        ParentTestConfig2(a10="1"),
        ParentTestConfig3(a10="1"),
        ParentTestConfig4(b1=Pass()),
        DictEnumConfig(a={"a": "a"}, p2=[Path("/tmp/"), Path("/tmp/")]),
        Pass(),
        SimpleConfig(),
        NestedParentConfig2(b1=ParentTestConfig3(a10="1")),
        myEnum("a"),
    ] + [p(a=10) for p in partial_error_representation_classes]:
        args, kwargs = parse_repr_to_kwargs(c)
        assert type(c)(*args, **kwargs) == c


def test_nested_load_no_depedencies():
    for c in [
        ParentTestConfig(a10="1"),
        ParentTestConfig2(a10="1"),
        ParentTestConfig3(a10="1"),
        ParentTestConfig4(b1=Pass()),
        DictEnumConfig(a={"a": "a"}, p2=[Path("/tmp/"), Path("/tmp/")]),
        SimpleConfig(),
        NestedParentConfig2(b1=ParentTestConfig3(a10="1")),
    ]:
        assert type(c)(**c.to_dict()) == c
        assert ast.literal_eval(str(c.to_dict())) == c.to_dict()
        assert all(
            isinstance(v, (float, int, bool, type(None), str))
            for v in c.make_dict(c.annotations, flatten=True).values()
        )


def test_debug_load(tmp_path: Path, capture_logger):
    out: io.StringIO = capture_logger()
    ParentTestConfig(debug=True)
    last_line = out.getvalue().split("\n")[-2]
    assert (
        last_line
        == "Loading ParentTestConfig in `debug` mode. Setting missing required value"
        " a10 to `None`."
    )
    p = ParentTestConfig(debug=True, a123=123, a543=543)
    last_line = out.getvalue().split("\n")[-2]
    assert (
        last_line
        == "Loading ParentTestConfig in `debug` mode. Ignoring unexpected arguments:"
        " `a123, a543`"
    )
    yaml_p = tmp_path.joinpath("test.yaml")
    p.write(yaml_p)
    with pytest.raises(ValueError, match=re.escape("Missing required values ['a10'].")):
        p.load(yaml_p)
    p.load(yaml_p, debug=True)
    last_line = out.getvalue().split("\n")[-2]
    assert (
        last_line
        == "Loading ParentTestConfig in `debug` mode. Setting missing required value"
        " a10 to `None`."
    )
    ParentTestConfig4.load(yaml_p, debug=True)
    args = out.getvalue().split("\n")[-4:-1]
    msgs = [
        (
            "Loading ParentTestConfig4 in `debug` mode. Setting missing required value"
            " b1 to `None`."
        ),
        (
            "Loading ParentTestConfig4 in `debug` mode. Unable to parse `a10` value"
            " None. Setting to `None`."
        ),
        (
            "Loading ParentTestConfig4 in `debug` mode. Unable to parse `a6` value a."
            " Setting to `None`."
        ),
    ]
    assert all(msg in args for msg in msgs)
    with pytest.raises(ValueError, match=re.escape("Missing required values ['b1'].")):
        ParentTestConfig4.load(yaml_p, debug=False)

    p.a10 = "a"
    p.write(yaml_p)
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            f"{Pass} provided args or kwargs (a) must be formatted as (args, kwargs) or"
            " (args) or (kwargs)."
        ),
    ):
        ParentTestConfig3.load(yaml_p, debug=False)

    pconfig_3 = ParentTestConfig3.load(yaml_p, debug=True)
    pconfig_4 = ParentTestConfig4.load(yaml_p, debug=True)
    # Testing nested configs.
    nested_c = NestedParentConfig(b1=pconfig_4, a1="")
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            f"{ParentTestConfig4} provided args or kwargs (ParentTestConfig3(a1='10',"
            " a2=10, a8='10', a9=None, a5={'a': 10}, c2={'a1': 10}, a10='a',"
            " a6=None)) must be formatted as (args, kwargs) or (args) or (kwargs)."
        ),
    ):
        NestedParentConfig(b1=pconfig_3, a1="")

    nested_c = NestedParentConfig(b1=pconfig_3, a1="", debug=True)
    assert (
        out.getvalue().split("\n")[-2]
        == "Loading NestedParentConfig in `debug` mode. Unable to parse `b1` value"
        f" {pconfig_3}. Setting to `None`."
    )
    nested_c = NestedParentConfig(b1=pconfig_4, a1="")
    assert nested_c.b1.a6 is None
    nested_c.write(yaml_p)
    with pytest.raises(
        RuntimeError,
        match=re.escape("Missing required value for a6."),
    ):
        NestedParentConfig2.load(yaml_p)
    nested_c2 = NestedParentConfig2.load(yaml_p, debug=True)
    assert nested_c2.b1.a6 is None


def test_flatten_nested_dict():
    out = flatten_nested_dict({"a": {"b": 1, "c": {"d": 2}}, "e": [3, 4]}, False, "#")
    assert out == {"e": [3, 4], "a#b": 1, "a#c#d": 2}
    out = flatten_nested_dict({"a": {"b": 1, "c": {"d": 2}}, "e": [3, 4]}, True, "#")
    assert out == {"a#b": 1, "e#0": 3, "e#1": 4, "a#c#d": 2}


if __name__ == "__main__":
    from conftest import run_tests_local
    import conftest

    _locals = locals()
    run_tests_local(_locals, conftest)
