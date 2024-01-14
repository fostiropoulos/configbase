import typing as ty

from config import (
    Derived,
    Dict,
    Enum,
    List,
    Literal,
    Optional,
    Tuple,
    config,
)
import pytest
import re


@config
class SimpleConfig:
    a1: int = 10


@config
class ParentTestConfig:
    a1: int = 10
    c: SimpleConfig
    c2: SimpleConfig
    a2: str = 10


@config
class ParentTestTestConfig:
    a1: Derived[int] = 10
    c: ParentTestConfig


class myEnum(Enum):
    A = "a"


class Pass:
    def __init__(self, a) -> None:
        self.a = a

    def __repr__(self) -> str:
        return f"Pass(a={self.a})"


@config
class MultiTypeConfig:
    a0: Derived[Literal["a", "b", "2"]] = "a"
    # a1: int = 10
    # a2: int = 10
    a5: Pass

    a9: Derived[Dict[str]]
    a8: Derived[Optional[str]] = 10

    p1: Pass = Pass(a=10)
    p2: Pass = Pass(a="10")

    c2: SimpleConfig = SimpleConfig()
    c3: SimpleConfig
    c4: SimpleConfig
    a6: myEnum = "a"
    a7: bool = True


@config
class ErrorConfigType:
    a1: int = "2.2"


@config
class ErrorConfigHintOrder:
    a4: Optional[Derived[str]] = "a"


@config
class ErrorConfigLiteral:
    a0: Derived[Literal["a", "b", "2"]] = 10


@config
class ErrorConfigNonAnnotated:
    a10 = 10


@config
class ErrorConfigBadAnnotated:
    # Should throw an error for Optional[Derived]
    a4: ty.Dict[str, str]


@config
class ErrorConfigBadAnnotatedTwo:
    # Should throw an error for Optional[Derived]
    a4: ty.Optional[str]


@config
class ErrorConfigEnum:
    a4: myEnum = "b"


@config
class ErrorConfigTuple:
    a4: Tuple[int, str] = ("2.1", "a")


@config
class ErrorConfigTupleLen:
    a4: Tuple[int, str] = (10, "a", "a")


@config
class ErrorConfigList:
    a4: List[str] = "a"


def test_types():
    e = MultiTypeConfig(a5={"a": 1}, c3={"a1": 2.4}, c4={"a1": "2"})
    assert e.to_dict()
    assert e.uid
    assert e.a5.a == 1
    assert e.p1.a == 10
    assert e.p2.a == "10"
    assert e.a6 == "a"
    assert e.c3.a1 == 2
    assert e.c2.a1 == 10
    assert e.c4.a1 == 2
    assert e.a8 == "10"
    assert e.a9 is None
    with pytest.raises(
        ValueError, match=re.escape("Missing required values ['a5', 'c3', 'c4'].")
    ):
        MultiTypeConfig()

    with pytest.raises(
        ValueError, match=re.escape("invalid literal for int() with base 10: '2.2'")
    ):
        MultiTypeConfig(a5={"a": 1}, c3={"a1": 2.4}, c4={"a1": "2.2"})


def test_error_configs():
    ERROR_CONFIGS = [
        (MultiTypeConfig, "Missing required values ['a5', 'c3', 'c4']."),
        (
            lambda: MultiTypeConfig(a5={"a": 1}, c3={"a1": 2.4}, c4={"a1": "2.2"}),
            "invalid literal for int() with base 10: '2.2'",
        ),
        (
            lambda: SimpleConfig("10"),
            "SimpleConfig does not support positional arguments.",
        ),
        (
            ErrorConfigTupleLen,
            (
                "Incompatible lengths for a4 between (10, 'a', 'a') and type_hint:"
                " (<class 'int'>, <class 'str'>)"
            ),
        ),
        (ErrorConfigTuple, "invalid literal for int() with base 10: '2.1'"),
        (ErrorConfigEnum, "b is not supported by <enum 'myEnum'>"),
        (ErrorConfigLiteral, "10 is not a valid Literal ('a', 'b', '2')"),
        (ErrorConfigNonAnnotated, "All variables must be annotated. {'a10'}"),
        (
            ErrorConfigBadAnnotated,
            "Invalid collection <class 'dict'>. type_hints must be structured as:",
        ),
        (
            ErrorConfigBadAnnotatedTwo,
            "Invalid collection typing.Union. type_hints must be structured as:",
        ),
        (
            ErrorConfigHintOrder,
            (
                "Invalid collection <class 'config.types.Derived'>. type_hints must be"
                " structured as:"
            ),
        ),
        (ErrorConfigType, "invalid literal for int() with base 10: '2.2'"),
        (
            lambda: ErrorConfigList(a4=(11,)),
            "Invalid type <class 'tuple'> for type List",
        ),
        (lambda: ErrorConfigList(a4=11), "Invalid type <class 'int'> for type List"),
        (lambda: ErrorConfigList(a4="11"), "Invalid type <class 'str'> for type List"),
    ]
    for error_config, error_msg in ERROR_CONFIGS:
        with pytest.raises((ValueError, AssertionError), match=re.escape(error_msg)):
            error_config()
    assert True


def test_hierarchical():
    c = SimpleConfig(a1="10")
    assert type(c.a1) is int and c.a1 == int("10")
    # Should fail
    # pc = ParentTestConfig(0,c,c,0)
    # Should not fail
    pc = ParentTestConfig(a1=0, c=c, c2=c)
    assert pc.a2 == str(10), "Could not cast"
    pc.c.a1 = 2
    assert pc.c2.a1 == pc.c.a1, "Lost reference"
    pc = ParentTestConfig(a1=0, c={"a1": 10}, c2={"a1": "2"}, a2=0)
    assert type(pc.c) is SimpleConfig
    assert pc.c2.a1 == 2
    pc_dict = ParentTestTestConfig(c=pc.to_dict())
    pc_obj = ParentTestTestConfig(c=pc)
    assert pc_dict == pc_obj


def test_iterable():
    ErrorConfigList(
        a4=[
            11,
        ]
    )


if __name__ == "__main__":
    from conftest import run_tests_local
    import conftest

    _locals = locals()
    run_tests_local(_locals, conftest)
