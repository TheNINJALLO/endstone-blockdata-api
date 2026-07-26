from setuptools import Distribution, setup


class BinaryDistribution(Distribution):
    """Tag the command wheel for the CPython/platform-specific live bridge."""

    def has_ext_modules(self) -> bool:
        return True


setup(distclass=BinaryDistribution)
