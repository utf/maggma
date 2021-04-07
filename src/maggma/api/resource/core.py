from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, FastAPI
from monty.json import MontyDecoder, MSONable
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from maggma.api.models import Response
from maggma.api.query_operator import QueryOperator
from maggma.api.utils import STORE_PARAMS, api_sanitize, attach_signature, merge_queries
from maggma.core import Store
from maggma.utils import dynamic_import


class Resource(MSONable, metaclass=ABCMeta):
    """
    Base class for a REST Compatible Resource
    """

    def __init__(
        self,
        model: BaseModel,
    ):
        """
        Args:
            model: the pydantic model this Resource represents
        """
        if isinstance(model, type) and issubclass(model, BaseModel):
            self.model = api_sanitize(model, allow_dict_msonable=True)
        else:
            raise ValueError("The resource model has to be a PyDantic Model")
        self.router = APIRouter()
        self.prepare_endpoint()
        self.setup_redirect()

    @abstractmethod
    def prepare_endpoint(self):
        """
        Internal method to prepare the endpoint by setting up default handlers
        for routes.
        """
        pass

    def setup_redirect(self):
        @self.router.get("$", include_in_schema=False)
        def redirect_unslashed():
            """
            Redirects unforward slashed url to resource
            url with the forward slash
            """

            url = self.router.url_path_for("/")
            return RedirectResponse(url=url, status_code=301)

    def run(self):  # pragma: no cover
        """
        Runs the Endpoint cluster locally
        This is intended for testing not production
        """
        import uvicorn

        app = FastAPI()
        app.include_router(self.router, prefix="")
        uvicorn.run(app)

    def as_dict(self) -> Dict:
        """
        Special as_dict implemented to convert pydantic models into strings
        """

        d = super().as_dict()  # Ensures sub-classes serialize correctly
        d["model"] = f"{self.model.__module__}.{self.model.__name__}"
        return d

    @classmethod
    def from_dict(cls, d):

        if isinstance(d["model"], str):
            d["model"] = dynamic_import(d["model"])
        d = {k: MontyDecoder().process_decoded(v) for k, v in d.items()}
        return cls(**d)