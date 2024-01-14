
Welcome to ConfigBase's documentation!
======================================


.. image:: _static/config.png
    :align: center
    :width: 200

Welcome to ConfigBase's documentation. Get started by reading our :doc:`usage`
and then get an overview with the :doc:`api/config`.

ConfigBase was developed for `ABLATOR`_ be sure to check the project's documentation.


The goal of ConfigBase is to simplify configuration for Machine Learning (ML) experiments. Configuration for ML experiments is mostly unsolved. It is cumbersome, error-prone and does not address the standard use-cases, for example HPO, and multi-node or multi-tenant enviroments. ConfigBase builds on top of several pilars to address those problems.


1. `Strongly typed <https://en.wikipedia.org/wiki/Strong_and_weak_typing>`_ configuration, with type resolution during run-time.
2. Address need for custom types specific to ML experiments
    * ``Derived``, are derived during execution, e.g. the `vocab_size` depends on the dataset.
    * ``Stateless``, take values which can change between execution runs or enviroments, e.g. the save directory.
3. Finger-printing of the configuration object based on unique value assignment with their corresponding types. Where for example Stateless variables are ignored.
4. Mutable and Imutable properties where one can `freeze` the configuration to prevent changes to it.
5. Flexible configuration definition, compositionality and hierarchical definition
6. Representation of configuration in YAML files for easy modification
7. Easy representation of value-distributions, i.e. fields that can take a value within a range, or conditionally, i.e. nested categorical distributions. There is easy integration for sampling and use with third party HPO algorithms.



.. _ABLATOR: https://ablator.org

Navigate
--------

.. toctree::
    :maxdepth: 2

    Source <https://github.com/fostiropoulos/configbase>
    usage
    api/config
    api/search_space

