# ConfigBase ⚙️ A Machine Learning Configuration System

<img src="assets/config.png" alt="logo" style="width:200px;"/>

The goal is to simplify configuration for Machine Learning (ML) experiments. Configuration for ML experiments is mostly unsolved. It is cumbersome, error-prone and does not address the standard use-cases, for example HPO, and multi-node or multi-tenant enviroments. ConfigBase builds on top of several pilars to address those problems.

1. [Strongly typed](https://en.wikipedia.org/wiki/Strong_and_weak_typing) configuration, with type resolution during run-time.
2. Address need for custom types specific to ML experiments
    * ``Derived``, are derived during execution, e.g. the `vocab_size` depends on the dataset.
    * ``Stateless``, take values which can change between execution runs or enviroments, e.g. the save directory.
3. Finger-printing of the configuration object based on unique value assignment with their corresponding types. Where for example Stateless variables are ignored.
4. Mutable and Imutable properties where one can `freeze` the configuration to prevent changes to it.
5. Flexible configuration definition, compositionality and hierarchical definition
6. Representation of configuration in YAML files for easy modification
7. Easy representation of value-distributions, i.e. fields that can take a value within a range, or conditionally, i.e. nested categorical distributions. There is easy integration for sampling and use with third party HPO algorithms.


**In Summary**
This repo aspires to be the poster-child of [StrictYAML](https://hitchdev.com/strictyaml/), [Hydra](https://hydra.cc/) and [Dataclasses](https://docs.python.org/3/library/dataclasses.html) combined and with a 🍒 on top.


## Usage


To install simply run:

```bash
pip install configbase
```

To define your configuration:

```python
from config import config

@config
class C:
    a: int = 5

c = C(a=5)
c.a
# Output:
5
c.a=5.5
c.a
# Output:
5
```

## Minimal Examples

### Strongly Typed
```python
from config import config

class MyClass:
    def __init__(self, a=3, b=3):
        self.a = a
        self.b = b

@config
class C:
    a: MyClass = MyClass()
    b: int = 5

c = C(a={"a": 1})
c.a.a
# Output:
1
```

### Object-Persistence
```python
print(C.from_yaml(c.to_yaml()))
# Output:
C(a={'a': 1, 'b': 2}, b=5)
```


### Immutable

```python
c.freeze()
c.b=1
# Output:
# RuntimeError: Can not set attribute b on frozen configuration ``C``.
c.unfreeze()
c.b=1
c.b
# Output:
1
```

### Fingerprinting
```python
from config import config, Stateless, Derived

@config
class C:
    a: Stateless[int] = 5
    b: int = 5
c = C()
c.uid
# Output:
'1cf3'
c.a=6
c.uid
# Output:
'1cf3'
c.a=5
c.uid
# Output:
'51fd'
```


### Distributions

```python
from config import config, Distribution, CategoricalDistribution, SearchSpace

@config
class A:
    d: float = 0.5

@config
class Master:
    a: A = A()
    d: float = 0.5

space = SearchSpace(
    {
        "a.d": Distribution(0, 1, n_bins=4),
        "d": CategoricalDistribution([Distribution(0, 0.1, n_bins=4), Distribution(0.9, 1, n_bins=4)]),
    }
)

m = Master()
m.sample(space)
# Output:
Master(a={'d': 0.0}, d=1.0)
```
**Custom HPO Functions**

```python
def hpo_fn(name, dist: CategoricalDistribution | Distribution):
    return dist.random_sample()
m.sample(space, sample_fn=hpo_fn)
# Output:
Master(a={'d': 0.5}, d=0.925)
```


**Expand Search Space**
```python

print(m.expand(space))
# Output:
[Master(a={'d': 0.0}, d=0.0), Master(a={'d': 0.0}, d=0.025), Master(a={'d': 0.0}, d=0.05), Master(a={'d': 0.0}, d=0.07500000000000001), Master(a={'d': 0.0}, d=0.1), Master(a={'d': 0.25}, d=0.0), Master(a={'d': 0.25}, d=0.025), Master(a={'d': 0.25}, d=0.05), Master(a={'d': 0.25}, d=0.07500000000000001), Master(a={'d': 0.25}, d=0.1), Master(a={'d': 0.5}, d=0.0), Master(a={'d': 0.5}, d=0.025), Master(a={'d': 0.5}, d=0.05), Master(a={'d': 0.5}, d=0.07500000000000001), Master(a={'d': 0.5}, d=0.1), Master(a={'d': 0.75}, d=0.0), Master(a={'d': 0.75}, d=0.025), Master(a={'d': 0.75}, d=0.05), Master(a={'d': 0.75}, d=0.07500000000000001), Master(a={'d': 0.75}, d=0.1), Master(a={'d': 1.0}, d=0.0), Master(a={'d': 1.0}, d=0.025), Master(a={'d': 1.0}, d=0.05), Master(a={'d': 1.0}, d=0.07500000000000001), Master(a={'d': 1.0}, d=0.1), Master(a={'d': 0.0}, d=0.9), Master(a={'d': 0.0}, d=0.925), Master(a={'d': 0.0}, d=0.95), Master(a={'d': 0.0}, d=0.975), Master(a={'d': 0.0}, d=1.0), Master(a={'d': 0.25}, d=0.9), Master(a={'d': 0.25}, d=0.925), Master(a={'d': 0.25}, d=0.95), Master(a={'d': 0.25}, d=0.975), Master(a={'d': 0.25}, d=1.0), Master(a={'d': 0.5}, d=0.9), Master(a={'d': 0.5}, d=0.925), Master(a={'d': 0.5}, d=0.95), Master(a={'d': 0.5}, d=0.975), Master(a={'d': 0.5}, d=1.0), Master(a={'d': 0.75}, d=0.9), Master(a={'d': 0.75}, d=0.925), Master(a={'d': 0.75}, d=0.95), Master(a={'d': 0.75}, d=0.975), Master(a={'d': 0.75}, d=1.0), Master(a={'d': 1.0}, d=0.9), Master(a={'d': 1.0}, d=0.925), Master(a={'d': 1.0}, d=0.95), Master(a={'d': 1.0}, d=0.975), Master(a={'d': 1.0}, d=1.0)]
```

## Cite

```bibtex
@misc{fostiropoulos2024configbase,
  author = {Fostiropoulos, Iordanis},
  title = {ConfigBase: A Machine Learning Configuration System },
  year = {2024},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/fostiropoulos/configbase}},
}
```