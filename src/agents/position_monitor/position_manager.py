"""Position CRUD manager."""

import json
from datetime import date
from pathlib import Path

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
        return opened.id

    async def close_position(self, position_id: str, close_price: float, reason: str = "") -> PositionAction:
        position = self._positions[position_id]
        position.status = PositionStatus.CLOSED
        position.close_date = date.today()
        position.current_price = close_price
        action = PositionAction(
            action_type="close",
            date=position.close_date,
            price=close_price,
            quantity=position.quantity,
            notes=reason,
        )
        position.actions.append(action)
        return action

    async def update_price(self, position_id: str, current_price: float) -> None:
        self._positions[position_id].current_price = current_price

    async def get_position(self, position_id: str) -> Position | None:
        position = self._positions.get(position_id)
        return position.model_copy(deep=True) if position else None

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

    async def save(self) -> None:
        data = [position.model_dump(mode="json") for position in self._positions.values()]
        self._storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def load(self) -> None:
        if not self._storage_path.exists() or not self._storage_path.read_text(encoding="utf-8").strip():
            self._positions = {}
            return
        payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        self._positions = {item["id"]: Position.model_validate(item) for item in payload}
