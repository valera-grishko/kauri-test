from collections import defaultdict
from fastapi import WebSocket

from exchanges import AVAILABLE_EXCHANGES
from services import SenderWithDisconnectChecker


class ConnectionManager:
    def __init__(self):
        self.subscriptions = defaultdict(list)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        pair, exchange = self.get_query_params(websocket)
        self._set_subscriptions(websocket, pair, exchange)

    @staticmethod
    def get_query_params(websocket: WebSocket) -> tuple[str, str]:
        pair = websocket.query_params.get("pair", "ALL")
        exchange = websocket.query_params.get("exchange", "ALL")

        if pair == 'None':  # from interface.html
            pair = 'ALL'

        if exchange == 'None':  # from interface.html
            exchange = 'ALL'

        pair = pair.upper()

        return pair, exchange

    def _set_subscriptions(self, websocket: WebSocket, pair: str, exchange: str):
        client_sub_info = {'websocket': websocket}
        self._set_all_subscriptions_to_true(client_sub_info, pair, exchange)
        self._set_specific_subscription_to_true(client_sub_info, pair, exchange)

    def _set_all_subscriptions_to_true(self, client_sub_info: dict, pair: str, exchange: str):
        if exchange == 'ALL':
            client_sub_info |= {available_ex: True for available_ex in AVAILABLE_EXCHANGES}
            self.subscriptions[pair].append(client_sub_info)

    def _set_specific_subscription_to_true(self, client_sub_info: dict, pair: str, exchange: str):
        if exchange != 'ALL':
            client_sub_info |= {available_ex: False for available_ex in AVAILABLE_EXCHANGES}
            client_sub_info[exchange] = True
            self.subscriptions[pair].append(client_sub_info)

    async def broadcast_with_disconnect_checker(self):
        sender = SenderWithDisconnectChecker(self.subscriptions)
        await sender.run_sending_process()


manager = ConnectionManager()
