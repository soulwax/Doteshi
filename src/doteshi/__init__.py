"""Procedural sprites of any size and kind.

    from doteshi import sprite, sdf, mat, pat, profile
"""
from .api import REGISTRY, build, load, override, rasterize, render, sprite
from .core import sdf
from .form import profile
from .resolve import style
from .shade import detail as pat
from .shade import material as mat

__all__ = ["REGISTRY", "build", "load", "rasterize", "render", "sprite", "override", "sdf", "profile", "pat", "mat", "style"]
