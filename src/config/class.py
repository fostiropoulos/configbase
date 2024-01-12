from pathlib import Path


def _repr(self):
    return (
        type(self).__name__
        + "("
        + ", ".join(
            [
                f"{k}='{v}'" if isinstance(v, str) else f"{k}={repr(v)}"
                for k, v in self.to_dict(_repr=True).items()
            ]
        )
        + ")"
    )


def _clean_key_pem(key_pem: str):
    return key_pem.replace("\\n", "\n").replace("\n", "\\n")


class ConfigClass:
    """
    The configuration for connecting to a remote storage via SSH.

    Parameters
    ----------
    host : str
        the host address of the server
    user : str
        the ssh user-name
    port : int
        the port running ssh
    key_pem : str | None, optional
        the raw string of the private key.
        Must be provided if `key_file` is unspecified, by default None
    key_file : Path | None, optional
        path to the key_file containing the private key.
        Must be provided if `key_pem` is unspecified, by default None

    Raises
    ------
    ValueError
        When both `key_pem` and `key_file` are unspecified or specified.
    """

    def __init__(
        self,
        host: str,
        user: str,
        port: int,
        key_pem: str | None = None,
        key_file: Path | None = None,
        **_,
    ):
        self.key_pem: str
        if not (key_file is None) ^ (key_pem is None):
            raise ValueError("Must only provide either `key_pem` or `key_file`.")
        if key_file is not None:
            self.key_pem = _clean_key_pem(key_file.read_text())
        elif key_pem is not None:
            self.key_pem = _clean_key_pem(key_pem)
        self.host: str = host
        self.user: str = user
        self.port: int = port

    # pylint: disable=useless-type-doc,useless-param-doc
    def to_dict(self, _repr: bool = False) -> dict[str, str]:
        """
        dictionary representation of the configuration
        that can be then parsed to be used for RClone.

        Parameters
        ----------
        _repr : bool
            Whether to return a dictionary representation that omits fixed
            internal values.

        Returns
        -------
        dict[str, str]
            the dictionary representation of the configuration.
        """
        _dict = {
            "host": self.host,
            "user": self.user,
            "port": str(self.port),
            "key_pem": self.key_pem,
            "key_use_agent": "False",
            "type": "sftp",
        }
        if _repr:
            del _dict["type"]
            del _dict["key_use_agent"]
        return _dict

    def __repr__(self) -> str:
        return _repr(self)


