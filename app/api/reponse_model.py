from typing import Generic, List, TypeVar
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class Page(GenericModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int