from collections import ChainMap, abc
import copy
import inspect
import logging
import operator
import typing as ty
from typing import Any, Union
from functools import partial
from pathlib import Path
from typing_extensions import Self

import yaml

from config.types import (
    Annotation,
    Derived,
    Dict,
    Enum,
    List,
    Literal,
    Stateless,
    Tuple,
    Type,
    parse_type_hint,
    parse_value,
)
from config.utils import (
    augment_trial_kwargs,
    dict_hash,
    flatten_nested_dict,
    parse_repr_to_kwargs,
)


def config(cls: type) -> type:
    """
    Decorator to turn any class into a ``ConfigBase`` object, copies attributes from the
    ``ConfigBase`` class into the decorated class. The decorated class must not implement
    an ``__init__`` function.

    Parameters
    ----------
    cls : type
        The class to be decorated.

    Raises
    ------
    ValueError
        When the ``__init__`` function is implemented in the decorated class.

    Returns
    -------
    type
        The decorated class with the ``config_class`` attribute.
    """

    if "__init__" in cls.__dict__:
        raise ValueError("Can not over-ride protected function name `__init__`.")

    for k, v in ConfigBase.__dict__.items():
        if k not in cls.__dict__ and k != "__dict__":
            setattr(cls, k, v)
    setattr(cls, "config_class", cls)
    setattr(cls, "_class_name", cls.__name__)

    return cls


def _freeze_helper(obj):
    def __setattr__(self, k, v):
        if getattr(self, "_freeze", False):
            raise RuntimeError(
                f"Can not set attribute {k} on a class of a frozen configuration"
                f" ``{type(self).__name__}``."
            )
        object.__setattr__(self, k, v)

    try:
        obj._freeze = True  # pylint: disable=protected-access
        type(obj).__setattr__ = __setattr__
    except Exception:  # pylint: disable=broad-exception-caught
        # this is the case where the object does not have
        # attribute setter function
        pass


def _unfreeze_helper(obj):
    if hasattr(obj, "_freeze"):
        super(type(obj), obj).__setattr__("_freeze", False)


def _parse_reconstructor(val, ignore_stateless: bool, flatten: bool):
    if isinstance(val, (int, float, bool, str, type(None))):
        return val
    if hasattr(type(val), "config_class"):
        return val.make_dict(
            val.annotations, ignore_stateless=ignore_stateless, flatten=flatten
        )
    if issubclass(type(val), Enum):
        return val.value
    args, kwargs = parse_repr_to_kwargs(val)
    if len(args) == 0:
        return kwargs
    if len(kwargs) == 0:
        return args
    return args, kwargs


class Missing:
    """
    This type is defined only for raising an error
    """


class ConfigBase:
    """

    This class is the building block for all configuration objects. It serves as the base class for
    configurations. It is used by the ``@config`` decorator, and allows for the creation of config classes.
    ``@config`` take care of the initialization and parsing of the attributes. Users should **not** directly
    inherit from this class and directly use ``@config`` dectorator. The example section below
    shows this in more detail.

    .. note::
        When initializing a config object, you can look into the list of attributes defined
        in the config class to see what arguments you can pass.

    Parameters
    ----------
    *args : Any
        This argument is just for disabling passing by positional arguments.
    debug : bool, optional
        Whether to load the configuration in debug mode and ignore discrepancies/errors, by default ``False``.
    **kwargs : Any
        Keyword arguments. Possible arguments are from the annotations of the configuration class. You can look into the
        Examples section for more details.

    Attributes
    ----------
    config_class : Type
        The class of the configuration object.

    Raises
    ------
    ValueError
        If positional arguments are provided or there are missing required values.
    KeyError
        If unexpected arguments are provided.
    RuntimeError
        If the class is not decorated with ``@config``.

    .. note::
       All config classes must be decorated with ``@config``.

    Examples
    --------

    >>> @config
    >>> class MyCustomConfig:
    ...     attr1: int = 1
    ...     attr2: Tuple[str, int, str]
    >>> my_config = MyCustomConfig(attr1=4, attr2=("hello", 1, "world"))  # Pass by named arguments
    >>> kwargs = {"attr1": 4, "attr2": ("hello", 1, "world")}   # Pass by keyword arguments
    >>> my_config = MyCustomConfig(**kwargs)

    Note that since we defined ``MyCustomConfig`` as a config class with two annotated attributes ``attr1``
    and ``attr2`` (without a constructor, which is automatically handled by
    ``@config``), when creating the config object, you can directly pass ``attr1`` and ``attr2``. You
    can also pass these arguments as keyword arguments.

    """

    config_class = type(None)

    def __init__(self, *args: Any, debug: bool = False, **kwargs: Any):
        self._debug: bool
        self._freeze: bool
        self._class_name: str
        self.__setattr__internal("_debug", debug)
        self.__setattr__internal("_freeze", False)

        missing_vals = self._validate_inputs(*args, debug=debug, **kwargs)

        assert len(missing_vals) == 0 or debug
        for k in self.annotations:
            if k in kwargs:
                v = kwargs[k]
                del kwargs[k]
            else:
                v = getattr(self, k, None)
            if k in missing_vals:
                logging.warning(
                    "Loading %s in `debug` mode. Setting missing required value %s to"
                    " `None`.",
                    self._class_name,
                    k,
                )
                self.__setattr__internal(k, None)

            else:
                try:
                    self.__setattr__(k, v)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    if not debug:
                        raise e
                    logging.warning(
                        "Loading %s in `debug` mode. Unable to parse `%s` value %s."
                        " Setting to `None`.",
                        self._class_name,
                        k,
                        v,
                    )
                    self.__setattr__internal(k, None)

        if len(kwargs) > 0 and not debug:
            unspected_args = ", ".join(kwargs.keys())
            raise KeyError(f"Unexpected arguments: `{unspected_args}`")
        if len(kwargs) > 0:
            unspected_args = ", ".join(kwargs.keys())
            logging.warning(
                "Loading %s in `debug` mode. Ignoring unexpected arguments: `%s`",
                self._class_name,
                unspected_args,
            )

    def _validate_inputs(self, *args, debug: bool, **kwargs) -> list[str]:
        added_variables = {
            item[0]
            for item in inspect.getmembers(type(self))
            if not inspect.isfunction(item[1]) and not item[0].startswith("_")
        }

        base_variables = {
            item[0]
            for item in inspect.getmembers(ConfigBase)
            if not inspect.isfunction(item[1])
        }
        non_annotated_variables = (
            added_variables - base_variables - set(self.annotations.keys())
        )
        assert (
            len(non_annotated_variables) == 0
        ), f"All variables must be annotated. {non_annotated_variables}"
        if len(args) > 0:
            raise ValueError(
                f"{self._class_name} does not support positional arguments."
            )
        if not isinstance(self, self.config_class):  # type: ignore[arg-type]
            raise RuntimeError(
                f"You must decorate your Config class '{self._class_name}' with"
                " ``@config``."
            )
        missing_vals = self._validate_missing(**kwargs)
        if len(missing_vals) != 0 and not debug:
            raise ValueError(f"Missing required values {missing_vals}.")
        return missing_vals

    def _validate_missing(self, **kwargs) -> list[str]:
        missing_vals = []
        for k, annotation in self.annotations.items():
            if not annotation.optional and annotation.state not in [Derived]:
                # make sure non-optional and derived values are not empty or
                # without a default assignment
                if not (
                    (k in kwargs and kwargs[k] is not None)
                    or getattr(self, k, None) is not None
                ):
                    missing_vals.append(k)
        return missing_vals

    def __setattr__internal(self, k, v):
        # super(self.config_class, self).__setattr__(k, v)
        object.__setattr__(self, k, v)

    def __setattr__(self, k, v):
        if self._freeze:
            raise RuntimeError(
                f"Can not set attribute {k} on frozen configuration"
                f" ``{type(self).__name__}``."
            )
        annotation = self.annotations[k]
        v = parse_value(v, annotation, k, self._debug)
        self.__setattr__internal(k, v)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return len(self.diff(other)) == 0
        return False

    def __repr__(self) -> str:
        """
        Return the string representation of the configuration object.

        Returns
        -------
        str
            The string representation of the configuration object.

        """

        return (
            self._class_name
            + "("
            + ", ".join([
                f"{k}='{v}'" if isinstance(v, str) else f"{k}={v.__repr__()}"
                for k, v in self.to_dict().items()
            ])
            + ")"
        )

    def keys(self) -> list[str]:
        """
        Get the keys of the configuration dictionary.

        Returns
        -------
        list[str]
            The keys of the configuration dictionary.
        """
        return list(self.to_dict().keys())

    @classmethod
    def load(cls, path: Union[Path, str], debug: bool = False) -> Self:
        """
        Load a configuration object from a file.

        Parameters
        ----------
        path : Union[Path, str]
            The path to the configuration file.
        debug : bool, optional
            Whether to load the configuration in debug mode, and ignore discrepancies/errors,
            by default ``False``.

        Returns
        -------
        Self
            The loaded configuration object.
        """
        return cls.from_yaml(Path(path).read_text(encoding="utf-8"), debug=debug)

    @property
    def annotations(self) -> dict[str, Annotation]:
        """
        Get the parsed annotations of the configuration object.

        Returns
        -------
        dict[str, Annotation]
            A dictionary of parsed annotations.
        """
        annotations = {}
        if hasattr(self, "__annotations__"):
            annotation_types = ChainMap(*(
                c.__annotations__
                for c in type(self).__mro__
                if "__annotations__" in c.__dict__
            ))
            annotations = {
                field_name: parse_type_hint(type(self), annotation)
                for field_name, annotation in annotation_types.items()
            }
        return annotations

    def get_val_with_dot_path(self, dot_path: str) -> Any:
        """
        Get the value of a configuration object attribute using dot notation.

        Parameters
        ----------
        dot_path : str
            The dot notation path to the attribute.

        Returns
        -------
        Any
            The value of the attribute.
        """
        return operator.attrgetter(dot_path)(self)

    def get_type_with_dot_path(self, dot_path: str) -> Type:
        """
        Get the type of a configuration object attribute using dot notation.

        Parameters
        ----------
        dot_path : str
            The dot notation path to the attribute.

        Returns
        -------
        Type
            The type of the attribute.
        """
        val = self.get_val_with_dot_path(dot_path)
        return type(val)

    def get_annot_type_with_dot_path(self, dot_path: str) -> Type:
        """
        Get the type of a configuration object annotation using dot notation.

        Parameters
        ----------
        dot_path : str
            The dot notation path to the annotation.

        Returns
        -------
        Type
            The type of the annotation.
        """
        *base_path, element = dot_path.split(".")
        annot_dot_path = ".".join(base_path + ["annotations"])
        annot: dict[str, Annotation] = self.get_val_with_dot_path(annot_dot_path)
        return annot[element].variable_type

    # pylint: disable=too-complex
    def make_dict(
        self,
        annotations: dict[str, Annotation],
        ignore_stateless: bool = False,
        flatten: bool = False,
    ) -> dict:
        """
        Create a dictionary representation of the configuration object.

        Parameters
        ----------
        annotations : dict[str, Annotation]
            A dictionary of annotations.
        ignore_stateless : bool
            Whether to ignore stateless values, by default ``False``.
        flatten : bool
            Whether to flatten nested dictionaries, by default ``False``.

        Returns
        -------
        dict
            The dictionary representation of the configuration object.

        Raises
        ------
        NotImplementedError
            If the type of annot.collection is not supported.
        """
        return_dict = {}
        parse_reconstructor = partial(
            _parse_reconstructor, ignore_stateless=ignore_stateless, flatten=flatten
        )
        for field_name, annot in annotations.items():
            if ignore_stateless and (annot.state in {Stateless, Derived}):
                continue

            _val = getattr(self, field_name)
            if annot.collection in [None, Literal] or _val is None:
                val = _val
            elif annot.collection == List:
                val = [parse_reconstructor(_lval) for _lval in _val]
            elif annot.collection == Tuple:
                val = tuple(parse_reconstructor(_lval) for _lval in _val)
            elif annot.collection in [Dict]:
                val = {k: parse_reconstructor(_dval) for k, _dval in _val.items()}
            elif hasattr(type(_val), "config_class"):
                val = _val.make_dict(
                    _val.annotations, ignore_stateless=ignore_stateless, flatten=flatten
                )

            elif annot.collection == Type:
                if annot.optional and _val is None:
                    val = None
                else:
                    val = parse_reconstructor(_val)
            elif issubclass(type(_val), Enum):
                val = _val.value
            else:
                raise NotImplementedError
            return_dict[field_name] = val
        if flatten:
            return_dict = flatten_nested_dict(return_dict)
        return return_dict

    def write(self, path: Union[Path, str]):
        """
        Write the configuration object to a file.

        Parameters
        ----------
        path : Union[Path, str]
            The path to the file.

        """
        Path(path).write_text(self.to_yaml(), encoding="utf-8")

    # pylint: disable=redefined-outer-name
    def diff_str(
        self, config: "ConfigBase", ignore_stateless: bool = False
    ) -> list[str]:
        """
        Get the differences between the current configuration object and another configuration object as strings.

        Parameters
        ----------
        config : ConfigBase
            The configuration object to compare.
        ignore_stateless : bool
            Whether to ignore stateless values, by default ``False``.

        Returns
        -------
        list[str]
            The list of differences as strings.

        """
        diffs = self.diff(config, ignore_stateless=ignore_stateless)
        str_diffs = []
        for p, (l_t, l_v), (r_t, r_v) in diffs:
            _diff = f"{p}:({l_t.__name__}){l_v}->({r_t.__name__}){r_v}"
            str_diffs.append(_diff)
        return str_diffs

    # pylint: disable=redefined-outer-name
    def diff(
        self, config: "ConfigBase", ignore_stateless: bool = False
    ) -> list[tuple[str, tuple[type, Any], tuple[type, Any]]]:
        """
        Get the differences between the current configuration object and another configuration object.

        Parameters
        ----------
        config : ConfigBase
            The configuration object to compare.
        ignore_stateless : bool
            Whether to ignore stateless values, by default ``False``

        Returns
        -------
        list[tuple[str, tuple[type, Any], tuple[type, Any]]]
            The list of differences as tuples.

        Examples
        --------
        Let's say we have two configuration objects ``config1`` and ``config2`` with the following attributes:

        >>> config1:
            learning_rate: 0.01
            optimizer: 'Adam'
            num_layers: 3

        >>> config2:
            learning_rate: 0.02
            optimizer: 'SGD'
            num_layers: 3

        The diff between these two configurations would look like:

        >>> config1.diff(config2)
        [('learning_rate', (float, 0.01), (float, 0.02)), ('optimizer', (str, 'Adam'), (str, 'SGD'))]

        In this example, the learning_rate and optimizer values are different between the two configuration objects.

        """
        left_config = copy.deepcopy(self)
        right_config = copy.deepcopy(config)
        left_dict = left_config.make_dict(
            left_config.annotations, ignore_stateless=ignore_stateless, flatten=True
        )

        right_dict = right_config.make_dict(
            right_config.annotations, ignore_stateless=ignore_stateless, flatten=True
        )
        left_keys = set(left_dict.keys())
        right_keys = set(right_dict.keys())
        diffs: list[tuple[str, tuple[type, ty.Any], tuple[type, ty.Any]]] = []
        for k in left_keys.union(right_keys):
            if k not in left_dict:
                right_v = right_dict[k]
                right_type = type(right_v)
                diffs.append((k, (Missing, None), (right_type, right_v)))

            elif k not in right_dict:
                left_v = left_dict[k]
                left_type = type(left_v)
                diffs.append((k, (left_type, left_v), (Missing, None)))

            elif left_dict[k] != right_dict[k] or not isinstance(
                left_dict[k], type(right_dict[k])
            ):
                right_v = right_dict[k]
                left_v = left_dict[k]
                left_type = type(left_v)
                right_type = type(right_v)
                diffs.append((k, (left_type, left_v), (right_type, right_v)))
        return diffs

    def to_dict(self, ignore_stateless: bool = False) -> dict:
        """
        Convert the configuration object to a dictionary.

        Parameters
        ----------
        ignore_stateless : bool
            Whether to ignore stateless values, by default ``False``.

        Returns
        -------
        dict
            The dictionary representation of the configuration object.

        """
        return self.make_dict(self.annotations, ignore_stateless=ignore_stateless)

    def to_yaml(self) -> str:
        """
        Convert the configuration object to YAML format.

        Returns
        -------
        str
            The YAML representation of the configuration object.

        """
        return yaml.dump(self.to_dict())

    @classmethod
    def from_yaml(cls, yaml_str: str, debug: bool = False) -> Self:
        """
        Load a configuration object from a yaml string.

        Parameters
        ----------
        yaml_str : str
            The yaml string to create a configuration object from.
        debug : bool, optional
            Whether to load the configuration in debug mode, and ignore discrepancies/errors,
            by default ``False``.

        Returns
        -------
        Self
            The loaded configuration object.
        """
        kwargs: dict = yaml.safe_load(yaml_str)
        return cls(**kwargs, debug=debug)

    def to_dot_path(self, ignore_stateless: bool = False) -> str:
        """
        Convert the configuration object to a dictionary with dot notation paths as keys.

        Parameters
        ----------
        ignore_stateless : bool
            Whether to ignore stateless values, by default ``False``.

        Returns
        -------
        str
            The YAML representation of the configuration object in dot notation paths.

        """
        _flat_dict = self.make_dict(
            self.annotations, ignore_stateless=ignore_stateless, flatten=True
        )
        return yaml.dump(_flat_dict)

    @property
    def uid(self) -> str:
        """
        Get the unique identifier for the configuration object.

        Returns
        -------
        str
            The unique identifier for the configuration object.

        """
        return dict_hash(self.make_dict(self.annotations, ignore_stateless=True))[:5]

    def assert_unambigious(self):
        """
        Assert that the configuration object is unambiguous and has all the required values.

        Raises
        ------
        RuntimeError
            If the configuration object is ambiguous or missing required values.

        """
        for k, annot in self.annotations.items():
            if not annot.optional and getattr(self, k) is None:
                raise RuntimeError(
                    f"Ambiguous configuration `{self._class_name}`. Must provide value"
                    f" for {k}"
                )
        self._apply_lambda_recursively("assert_unambigious")

    def freeze(self):
        """
        Freezes the configuration attributes, such that they can no longer be changed.
        It freezes all attributes recursively of the current and nested objects. Attempting
        to change the value of any item belonging to the configuration will result in an error.
        """
        self.__setattr__internal("_freeze", True)
        self._apply_lambda_recursively("freeze")

        for k, annot in self.annotations.items():
            if (
                isinstance(annot.variable_type, type)
                and not hasattr(annot.variable_type, "config_class")
                and getattr(self, k) is not None
                and hasattr(getattr(self, k), "__setattr__")
            ):
                if annot.collection in [List, Tuple]:
                    for _lval in getattr(self, k):
                        _freeze_helper(_lval)
                elif annot.collection in [Dict]:
                    for _lval in getattr(self, k).values():
                        _freeze_helper(_lval)
                else:
                    _freeze_helper(getattr(self, k))

    def unfreeze(self):
        """
        Unfreezes the configuration attributes, such that they can now be modified.
        The attributes are unfreezed recursively. Unfreezing an unfrozen configuration,
        leads to no changes.
        """
        self.__setattr__internal("_freeze", False)
        self._apply_lambda_recursively("unfreeze")

        for k, annot in self.annotations.items():
            if (
                isinstance(annot.variable_type, type)
                and not hasattr(annot.variable_type, "config_class")
                and getattr(self, k) is not None
            ):
                if annot.collection in [List, Tuple]:
                    for _lval in getattr(self, k):
                        _unfreeze_helper(_lval)
                elif annot.collection in [Dict]:
                    for _lval in getattr(self, k).values():
                        _unfreeze_helper(_lval)
                else:
                    _unfreeze_helper(getattr(self, k))

    def _apply_lambda_recursively(self, lam: str, *args):
        for k, annot in self.annotations.items():
            if (
                isinstance(annot.variable_type, type)
                and hasattr(annot.variable_type, "config_class")
                and getattr(self, k) is not None
            ):
                if annot.collection in [List, Tuple]:
                    for _lval in getattr(self, k):
                        getattr(_lval, lam)(*args)
                elif annot.collection in [Dict]:
                    for _lval in getattr(self, k).values():
                        getattr(_lval, lam)(*args)
                else:
                    getattr(getattr(self, k), lam)(*args)

    def expand(self, search_space) -> list[Self]:
        """
        Expands as the cartesian product of all possible configurable attributes. The resulting
        configuration can be seen as a grid-space of the configurations. The granularity of the
        search space is controlled via the ``n_bins`` argument of each ``Distribution`` as well
        as the number of choices for ``CategoricalDistribution``.

        Any values not present in the ``search_space`` will maintain their default value assignment.

        .. note::
            The number of items returned by this function grows exponentially with respect to
            the number of Distributions in the ``search_space`` and their distinct values, i.e.
            ``n_bins``.

        Parameters
        ----------
        search_space : SearchSpace
            The search space from which to expand the current configuration.

        Returns
        -------
        list[Self]
            A list of configurations where the difference between objects is specified by the ``search_space``

        Examples
        --------
        >>> @config
        >>> class MyCustomConfig:
        ...     attr1: int = 1
        ...     attr2: float = 2
        >>> space = SearchSpace(
        ...    {
        ...        "attr1": Distribution(0, 1, n_bins=4),
        ...        "attr2": CategoricalDistribution([0,1,2,3,4]),
        ...    }
        ... )
        >>> my_config = MyCustomConfig()
        >>> my_config.expand(space)
        [MyCustomConfig(attr1=0, attr2=0.0), MyCustomConfig(attr1=0, attr2=0.0),
        MyCustomConfig(attr1=1, attr2=0.0), MyCustomConfig(attr1=0, attr2=4.0),
        MyCustomConfig(attr1=0, attr2=4.0), MyCustomConfig(attr1=1, attr2=4.0)]

        """
        out_list = []
        for dot_paths in search_space.expand():
            kwargs = augment_trial_kwargs(
                trial_kwargs=self.to_dict(), augmentation=dot_paths
            )
            out_list.append(type(self)(**kwargs))
        return out_list

    def sample(self, search_space, sample_fn: abc.Callable | None = None) -> Self:
        """
        Samples values from the ``search_space`` distributions and initializes a new
        configuration object where the difference from the current object are only
        for the sampled values. Optionally, a ``sample_fn`` can be specified that can be
        used to select values from each distribution. The ``sample_fn`` can be an HPO algorithm
        or another heuristic in sampling configurations.

        Parameters
        ----------
        search_space : SearchSpace
            The search space from which to sample a new configuration.
        sample_fn : abc.Callable | None, optional
            The function that can be used to sample values from each distribution. When left
            unspecified, the sampling is uniformly random, by default None

        Returns
        -------
        Self
            A sampled configuration object

        Examples
        --------
        >>> @config
        >>> class MyCustomConfig:
        ...     attr1: int = 1
        ...     attr2: float = 2
        >>> space = SearchSpace(
        ...    {
        ...        "attr1": Distribution(0, 1, n_bins=4),
        ...        "attr2": CategoricalDistribution([0,1,2,3,4]),
        ...    }
        ... )
        >>> my_config = MyCustomConfig()
        >>> my_config.sample(space)
        MyCustomConfig(attr1=0, attr2=4.0)
        """
        dot_paths = search_space.sample(sample_fn=sample_fn)
        kwargs = augment_trial_kwargs(
            trial_kwargs=self.to_dict(), augmentation=dot_paths
        )
        return type(self)(**kwargs)
