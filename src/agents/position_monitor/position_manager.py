"""Position CRUD manager."""

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

from src.models.position import Position, PositionAction, PositionStatus


class PositionManager:
    def __init__(self, storage_path: str = "~/.aegis-trader/positions.json"):
        self._storage_path = Path(storage_path).expanduser()
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._positions: dict[str, Position] = {}

    async def open_position(self, position: Position) -> str:
        opened = position.model_copy(deep=True)
        opened.status = PositionStatus.ACTIVE
        opened.actions.append(
            PositionAction(action_type="open", date=opened.entry_date, price=opened.entry_price, quantity=opened.quantity)
        )
        self._positions[opened.id] = opened
        await self.save()
        return opened.id

    async def close_position(self, position_id: str, close_price: float, reason: str = "") -> Position:
        position = self._positions.get(position_id)
        if position is None:
            raise ValueError(f"Position not found: {position_id}")
        position.status = PositionStatus.CLOSED
        position.close_date = date.today()
        position.close_price = close_price
        position.current_price = close_price
        action = PositionAction(
            action_type="close",
            date=position.close_date,
            price=close_price,
            quantity=position.quantity,
            notes=reason,
        )
        position.actions.append(action)
        await self.save()
        return position

    async def roll_position(self, position_id: str, new_contract, new_entry_price: float) -> Position:
        old_position = self._positions.get(position_id)
        if old_position is None:
            raise ValueError(f"Position {position_id} not found")
        if old_position.status != PositionStatus.ACTIVE:
            raise ValueError(f"Cannot roll non-active position (status={old_position.status})")

        old_position.status = PositionStatus.ROLLED
        old_position.close_date = date.today()
        old_position.close_price = old_position.current_price
        old_position.actions.append(
            PositionAction(
                action_type="roll",
                date=date.today(),
                price=old_position.current_price or 0.0,
                quantity=old_position.quantity,
                notes=f"Rolled to new contract {new_contract.contract_symbol}",
            )
        )

        new_position = Position(
            id=str(uuid4()),
            symbol=old_position.symbol,
            contract=new_contract,
            status=PositionStatus.ACTIVE,
            entry_price=new_entry_price,
            quantity=old_position.quantity,
            entry_date=date.today(),
            trade_plan=old_position.trade_plan,
            parent_position_id=position_id,
        )
        new_position.actions.append(
            PositionAction(
                action_type="open",
                date=date.today(),
                price=new_entry_price,
                quantity=new_position.quantity,
                notes=f"Opened from roll of {position_id}",
            )
        )
        self._positions[new_position.id] = new_position
        await self.save()
        return new_position

    async def expire_position(self, position_id: str) -> Position:
        position = self._positions.get(position_id)
        if position is None:
            raise ValueError(f"Position {position_id} not found")
        position.status = PositionStatus.EXPIRED
        position.close_date = position.contract.expiry
        position.close_price = 0.0
        position.actions.append(
            PositionAction(
                action_type="expire",
                date=position.close_date,
                price=0.0,
                quantity=position.quantity,
                notes="Contract expired",
            )
        )
        await self.save()
        return position

    async def update_price(self, position_id: str, current_price: float) -> None:
        position = self._positions.get(position_id)
        if position is None:
            return
        position.current_price = current_price

    async def get_position(self, position_id: str) -> Position | None:
        position = self._positions.get(position_id)
        return position.model_copy(deep=True) if position else None

    async def get_all_positions(self) -> list[Position]:
        return [position.model_copy(deep=True) for position in self._positions.values()]

    async def get_active_positions(self) -> list[Position]:
        return [
            position.model_copy(deep=True)
            for position in self._positions.values()
            if position.status == PositionStatus.ACTIVE
        ]

    async def get_positions_by_symbol(self, symbol: str) -> list[Position]:
        upper_symbol = symbol.upper()
        return [
            position.model_copy(deep=True)
            for position in self._positions.values()
            if position.symbol.upper() == upper_symbol
        ]

    async def get_position_history(self, symbol: str) -> list[Position]:
        upper_symbol = symbol.upper()
        return [
            position.model_copy(deep=True)
            for position in self._positions.values()
            if position.symbol.upper() == upper_symbol
        ]

    async def save(self) -> None:
        data = [position.model_dump(mode="json") for position in self._positions.values()]
        self._storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def load(self) -> None:
        if not self._storage_path.exists() or not self._storage_path.read_text(encoding="utf-8").strip():
            self._positions = {}
            return
        payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        self._positions = {item["id"]: Position.model_validate(item) for item in payload}
