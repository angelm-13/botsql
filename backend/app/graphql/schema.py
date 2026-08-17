from __future__ import annotations

import graphene
from app.graphql.queries import Query
from app.graphql.mutations import Mutation

schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)
