"""
This is a template project.
This docstring should be replaced to describe the purpose of this project.
"""

__version__ = "0.0.1"

from config.types import (
    Annotation,
    Derived,
    Dict,
    Enum,
    Optional,
    Stateful,
    Stateless,
    Type,
    List,
    Literal,
    Tuple,
)

from config.main import config

from config.search_space.main import Distribution, CategoricalDistribution, SearchSpace
