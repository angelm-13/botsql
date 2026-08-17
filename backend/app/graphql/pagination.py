from __future__ import annotations

import math
import graphene


class PageInfo(graphene.ObjectType):
    total = graphene.Int(required=True)
    page = graphene.Int(required=True)
    per_page = graphene.Int(required=True)
    pages = graphene.Int(required=True)
    has_next = graphene.Boolean(required=True)
    has_prev = graphene.Boolean(required=True)


def paginate_query(query, page: int = 1, per_page: int = 20):
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 20), 1), 100)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = math.ceil(total / per_page) if total else 1
    return items, PageInfo(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )
