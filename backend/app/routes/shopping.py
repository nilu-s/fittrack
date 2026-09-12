"""Private shopping list API and explicit meal-plan import."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.database import async_session
from app.models import Food, ShoppingCatalogEntry, ShoppingIconPreference, ShoppingItem, ShoppingList, ShoppingMealImport, SpaceMembership
from app.routes.auth import get_current_user
from app.schemas import ShoppingItemCreate, ShoppingItemResponse, ShoppingItemUpdate, ShoppingListResponse, ShoppingMealImportCommand, ShoppingMealPreviewItem, ShoppingMealPreviewResponse
from app.services.shopping_aggregation import planned_meal_requirements
from app.services.shopping_icons import canonical_icon_key, catalog_term_fingerprint, category_for_icon, classify_article, normalize_article_title
from app.services.spaces import member_space

router = APIRouter(prefix="/shopping", tags=["shopping"])


async def _owned(session, model, resource_id: uuid.UUID, account_id: uuid.UUID):
    row = await session.scalar(select(model).where(model.id == resource_id, model.account_id == account_id))
    if row is None:
        raise HTTPException(404, "Resource not found")
    return row


async def _active_list(session, account_id: uuid.UUID, space_id: uuid.UUID | None = None) -> ShoppingList:
    if space_id is not None:
        await member_space(session, space_id, account_id)
    scope = ShoppingList.space_id == space_id if space_id is not None else and_(ShoppingList.space_id.is_(None), ShoppingList.account_id == account_id)
    row = await session.scalar(select(ShoppingList).execution_options(include_all_accounts=True).where(scope, ShoppingList.is_active.is_(True)).order_by(ShoppingList.created_at))
    if row is None:
        row = ShoppingList(account_id=account_id, space_id=space_id, name="Einkauf", is_active=True)
        session.add(row)
        await session.flush()
    return row


async def _accessible_item(session, item_id: uuid.UUID, account_id: uuid.UUID) -> ShoppingItem:
    member = exists(select(SpaceMembership.id).where(
        SpaceMembership.space_id == ShoppingList.space_id, SpaceMembership.account_id == account_id
    ))
    row = await session.scalar(select(ShoppingItem).execution_options(include_all_accounts=True).join(
        ShoppingList, ShoppingList.id == ShoppingItem.shopping_list_id
    ).where(ShoppingItem.id == item_id, or_(
        and_(ShoppingList.space_id.is_(None), ShoppingItem.account_id == account_id),
        and_(ShoppingList.space_id.is_not(None), member),
    )))
    if row is None:
        raise HTTPException(404, "Resource not found")
    return row


def _item_response(row: ShoppingItem) -> ShoppingItemResponse:
    return ShoppingItemResponse.model_validate(row)


async def _icon_for_title(session, account_id: uuid.UUID, title: str) -> tuple[str, str]:
    normalized_title = normalize_article_title(title)
    fingerprint = catalog_term_fingerprint(title)
    preference = await session.scalar(select(ShoppingIconPreference).where(
        ShoppingIconPreference.account_id == account_id,
        ShoppingIconPreference.normalized_title == normalized_title,
    ))
    if preference:
        return preference.category_key, preference.icon_key
    catalog_entry = await session.scalar(select(ShoppingCatalogEntry).where(
        ShoppingCatalogEntry.term_fingerprint == fingerprint,
    ))
    if catalog_entry:
        return catalog_entry.category_key, catalog_entry.icon_key
    category_key, icon_key = classify_article(title)
    # The server grows the shared catalogue only with normalized terms and
    # bundled icon keys.  Unknown terms have no generated artwork yet, so the
    # privacy-preserving Initials fallback remains the visible result.
    if normalized_title:
        await session.execute(insert(ShoppingCatalogEntry).values(
            term_fingerprint=fingerprint, category_key=category_key,
            icon_key=icon_key, status="approved" if icon_key != "initials" else "pending_icon",
        ).on_conflict_do_nothing(index_elements=["term_fingerprint"]))
    return category_key, icon_key


async def _remember_icon_choice(session, account_id: uuid.UUID, title: str, category_key: str, icon_key: str) -> None:
    normalized_title = normalize_article_title(title)
    if not normalized_title:
        return
    preference = await session.scalar(select(ShoppingIconPreference).where(
        ShoppingIconPreference.account_id == account_id,
        ShoppingIconPreference.normalized_title == normalized_title,
    ))
    if preference is None:
        session.add(ShoppingIconPreference(
            account_id=account_id, normalized_title=normalized_title,
            category_key=category_key, icon_key=icon_key,
        ))
    else:
        preference.category_key = category_key
        preference.icon_key = icon_key


async def _publish_catalog_icon_choice(session, title: str, category_key: str, icon_key: str) -> None:
    """Make an explicit choice reusable without retaining the product name."""
    if not normalize_article_title(title):
        return
    await session.execute(insert(ShoppingCatalogEntry).values(
        term_fingerprint=catalog_term_fingerprint(title), category_key=category_key,
        icon_key=icon_key, status="approved",
    ).on_conflict_do_update(
        index_elements=["term_fingerprint"],
        set_={"category_key": category_key, "icon_key": icon_key, "status": "approved"},
    ))


@router.get("", response_model=ShoppingListResponse)
async def get_shopping_list(space_id: uuid.UUID | None = Query(default=None), account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        shopping_list = await _active_list(session, account_id, space_id)
        await session.commit()
        items = (await session.execute(select(ShoppingItem).execution_options(include_all_accounts=True).where(
            ShoppingItem.shopping_list_id == shopping_list.id
        ).order_by(ShoppingItem.status, ShoppingItem.category_key, ShoppingItem.sort_order, ShoppingItem.created_at))).scalars().all()
        return ShoppingListResponse(id=shopping_list.id, name=shopping_list.name, space_id=shopping_list.space_id, items=[_item_response(row) for row in items])


@router.post("/items", response_model=ShoppingItemResponse, status_code=201)
async def create_item(body: ShoppingItemCreate, space_id: uuid.UUID | None = Query(default=None), account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        shopping_list = await _active_list(session, account_id, space_id)
        food = await _owned(session, Food, body.food_id, account_id) if body.food_id else None
        title = body.title.strip()
        category, icon = await _icon_for_title(session, account_id, title)
        if body.icon_key is not None:
            icon = canonical_icon_key(body.icon_key)
            category = category_for_icon(icon)
            await _remember_icon_choice(session, account_id, title, category, icon)
            await _publish_catalog_icon_choice(session, title, category, icon)
        elif body.category_key is not None:
            category = body.category_key
            icon = "initials" if category == "other" else canonical_icon_key(category)
        row = ShoppingItem(account_id=account_id, shopping_list_id=shopping_list.id, food_id=food.id if food else None,
            title=title, category_key=category, icon_key=icon,
            quantity=body.quantity, unit=body.unit, note=body.note, source="manual")
        session.add(row); await session.commit(); await session.refresh(row)
        return _item_response(row)


@router.put("/items/{item_id}", response_model=ShoppingItemResponse)
async def update_item(item_id: uuid.UUID, body: ShoppingItemUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _accessible_item(session, item_id, account_id)
        for key, value in body.model_dump(exclude_unset=True).items():
            if key == "icon_key":
                continue
            setattr(row, key, value)
        if body.icon_key is not None:
            row.icon_key = canonical_icon_key(body.icon_key)
            row.category_key = category_for_icon(row.icon_key)
            await _remember_icon_choice(session, account_id, row.title, row.category_key, row.icon_key)
            await _publish_catalog_icon_choice(session, row.title, row.category_key, row.icon_key)
        elif body.title is not None and body.category_key is None:
            row.category_key, row.icon_key = await _icon_for_title(session, account_id, row.title)
        elif body.category_key is not None and body.icon_key is None:
            row.icon_key = "initials" if row.category_key == "other" else canonical_icon_key(row.category_key)
        if row.status == "done" and row.completed_at is None:
            row.completed_at = datetime.now(timezone.utc)
        elif row.status == "open":
            row.completed_at = None
        await session.commit(); await session.refresh(row)
        return _item_response(row)


@router.post("/items/{item_id}/toggle", response_model=ShoppingItemResponse)
async def toggle_item(item_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _accessible_item(session, item_id, account_id)
        row.status = "done" if row.status == "open" else "open"
        row.completed_at = datetime.now(timezone.utc) if row.status == "done" else None
        await session.commit(); await session.refresh(row)
        return _item_response(row)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await session.delete(await _accessible_item(session, item_id, account_id)); await session.commit()


@router.get("/meal-preview", response_model=ShoppingMealPreviewResponse)
async def meal_preview(from_date: date = Query(alias="from"), to_date: date = Query(alias="to"), account_id: uuid.UUID = Depends(get_current_user)):
    if to_date < from_date or (to_date - from_date).days >= 14:
        raise HTTPException(422, "Shopping preview period must be between 1 and 14 days")
    async with async_session() as session:
        plan, rows = await planned_meal_requirements(session, account_id, from_date, to_date)
        return ShoppingMealPreviewResponse(from_date=from_date, to_date=to_date, plan_name=plan.name if plan else None,
            items=[ShoppingMealPreviewItem(**row) for row in rows])


@router.post("/meal-import", response_model=ShoppingListResponse)
async def import_meal_plan(body: ShoppingMealImportCommand, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        shopping_list = await _active_list(session, account_id)
        plan, rows = await planned_meal_requirements(session, account_id, body.from_date, body.to_date)
        if plan is None:
            raise HTTPException(409, "No active meal plan")
        existing_import = await session.scalar(select(ShoppingMealImport).where(
            ShoppingMealImport.account_id == account_id, ShoppingMealImport.shopping_list_id == shopping_list.id,
            ShoppingMealImport.meal_plan_id == plan.id, ShoppingMealImport.meal_plan_version == plan.version,
            ShoppingMealImport.from_date == body.from_date, ShoppingMealImport.to_date == body.to_date,
        ))
        if existing_import is None:
            open_items = (await session.execute(select(ShoppingItem).where(
                ShoppingItem.account_id == account_id, ShoppingItem.shopping_list_id == shopping_list.id, ShoppingItem.status == "open"
            ))).scalars().all()
            by_food = {item.food_id: item for item in open_items if item.food_id is not None}
            for requirement in rows:
                current = by_food.get(requirement["food_id"])
                if current and requirement["quantity"] is not None and current.unit in (None, requirement["unit"]):
                    current.quantity = (current.quantity or Decimal("0")) + requirement["quantity"]
                    current.unit = requirement["unit"]
                    current.source = "mixed" if current.source == "manual" else current.source
                else:
                    session.add(ShoppingItem(account_id=account_id, shopping_list_id=shopping_list.id, food_id=requirement["food_id"],
                        title=requirement["title"], category_key=requirement["category_key"], icon_key=requirement["icon_key"],
                        quantity=requirement["quantity"], unit=requirement["unit"], source="meal_plan"))
            session.add(ShoppingMealImport(account_id=account_id, shopping_list_id=shopping_list.id, meal_plan_id=plan.id,
                meal_plan_version=plan.version, from_date=body.from_date, to_date=body.to_date))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
        items = (await session.execute(select(ShoppingItem).where(
            ShoppingItem.account_id == account_id, ShoppingItem.shopping_list_id == shopping_list.id
        ).order_by(ShoppingItem.status, ShoppingItem.category_key, ShoppingItem.sort_order, ShoppingItem.created_at))).scalars().all()
        return ShoppingListResponse(id=shopping_list.id, name=shopping_list.name, items=[_item_response(row) for row in items])
