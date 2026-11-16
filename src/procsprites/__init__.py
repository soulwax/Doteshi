"""Procedural sprites of any size and kind.

    from procsprites import sprite, sdf, mat, pat, profile
"""
from .api import REGISTRY, build, load, rasterize, render, sprite
from .core import sdf
from .form import profile
from .shade import detail as pat
from .shade import material as mat

__all__ = ["REGISTRY", "build", "load", "rasterize", "render", "sprite", "sdf", "profile", "pat", "mat"]
