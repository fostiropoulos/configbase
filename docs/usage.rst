Usage
=====

Installation
------------

``pip install configbase``


Examples
--------


Strongly Typed
^^^^^^^^^^^^^^

.. code-block::

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

Object-Persistence
^^^^^^^^^^^^^^^^^^

.. code-block::

    print(C.from_yaml(c.to_yaml()))
    # Output:
    C(a={'a': 1, 'b': 2}, b=5)


Immutable
^^^^^^^^^

.. code-block::

    c.freeze()
    c.b=1
    # Output:
    # RuntimeError: Can not set attribute b on frozen configuration ``C``.
    c.unfreeze()
    c.b=1
    c.b
    # Output:
    1

Fingerprinting
^^^^^^^^^^^^^^

.. code-block::

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


Distributions
^^^^^^^^^^^^^

.. code-block::

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


Custom HPO Functions
^^^^^^^^^^^^^^^^^^^^

.. code-block::

    def hpo_fn(name, dist: CategoricalDistribution | Distribution):
        return dist.random_sample()
    m.sample(space, sample_fn=hpo_fn)
    # Output:
    Master(a={'d': 0.5}, d=0.925)


Expand Search Space
^^^^^^^^^^^^^^^^^^^

.. code-block::

    print(m.expand(space))
    # Output:
    [Master(a={'d': 0.0}, d=0.0), Master(a={'d': 0.0}, d=0.025), Master(a={'d': 0.0}, d=0.05), Master(a={'d': 0.0}, d=0.07500000000000001), Master(a={'d': 0.0}, d=0.1), Master(a={'d': 0.25}, d=0.0), Master(a={'d': 0.25}, d=0.025), Master(a={'d': 0.25}, d=0.05), Master(a={'d': 0.25}, d=0.07500000000000001), Master(a={'d': 0.25}, d=0.1), Master(a={'d': 0.5}, d=0.0), Master(a={'d': 0.5}, d=0.025), Master(a={'d': 0.5}, d=0.05), Master(a={'d': 0.5}, d=0.07500000000000001), Master(a={'d': 0.5}, d=0.1), Master(a={'d': 0.75}, d=0.0), Master(a={'d': 0.75}, d=0.025), Master(a={'d': 0.75}, d=0.05), Master(a={'d': 0.75}, d=0.07500000000000001), Master(a={'d': 0.75}, d=0.1), Master(a={'d': 1.0}, d=0.0), Master(a={'d': 1.0}, d=0.025), Master(a={'d': 1.0}, d=0.05), Master(a={'d': 1.0}, d=0.07500000000000001), Master(a={'d': 1.0}, d=0.1), Master(a={'d': 0.0}, d=0.9), Master(a={'d': 0.0}, d=0.925), Master(a={'d': 0.0}, d=0.95), Master(a={'d': 0.0}, d=0.975), Master(a={'d': 0.0}, d=1.0), Master(a={'d': 0.25}, d=0.9), Master(a={'d': 0.25}, d=0.925), Master(a={'d': 0.25}, d=0.95), Master(a={'d': 0.25}, d=0.975), Master(a={'d': 0.25}, d=1.0), Master(a={'d': 0.5}, d=0.9), Master(a={'d': 0.5}, d=0.925), Master(a={'d': 0.5}, d=0.95), Master(a={'d': 0.5}, d=0.975), Master(a={'d': 0.5}, d=1.0), Master(a={'d': 0.75}, d=0.9), Master(a={'d': 0.75}, d=0.925), Master(a={'d': 0.75}, d=0.95), Master(a={'d': 0.75}, d=0.975), Master(a={'d': 0.75}, d=1.0), Master(a={'d': 1.0}, d=0.9), Master(a={'d': 1.0}, d=0.925), Master(a={'d': 1.0}, d=0.95), Master(a={'d': 1.0}, d=0.975), Master(a={'d': 1.0}, d=1.0)]

