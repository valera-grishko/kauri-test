import json

from fastapi import WebSocket

from exchanges import AVAILABLE_EXCHANGES, CURRENT_PRICES, EXCHANGE_DATA_GETTER


class SenderWithDisconnectChecker:
    def __init__(self, subscriptions: dict):
        self.subscriptions = subscriptions

    async def run_sending_process(self):
        for pair, clients in self.subscriptions.items():
            await self._iterate_over_all_subscribed_clients(pair, clients)

    async def _iterate_over_all_subscribed_clients(self, pair: str, clients: list):
        for client in clients:
            await self._send_pairs_and_prices_to_client(pair, client)

    async def _send_pairs_and_prices_to_client(self, pair: str, client: dict):
        websocket = client['websocket']
        try:
            message = self._get_sent_data(pair, client)
            await websocket.send_text(json.dumps(message))
        except Exception:  # when the client is disconnected  # noqa
            self._disconnect_client(pair, websocket)

    def _get_sent_data(self, pair: str, client: dict) -> dict:
        if self._is_aggregated_prices_required(client):
            return self._get_aggregated_prices()

        for available_ex in AVAILABLE_EXCHANGES:
            if client[available_ex]:
                return EXCHANGE_DATA_GETTER[available_ex](pair)

    @staticmethod
    def _is_aggregated_prices_required(client: dict) -> bool:
        for available_ex in AVAILABLE_EXCHANGES:
            if client[available_ex] is False:
                return False
        return True

    @staticmethod
    def _get_aggregated_prices() -> dict:
        price_aggregator = PriceAggregator()
        price_aggregator.run_aggregating_process()
        return price_aggregator.aggregated_prices

    def _disconnect_client(self, pair: str, websocket: WebSocket):
        client_remover = ClientRemover(self.subscriptions)
        client_remover.remove_client_from_subscriptions(pair, websocket)


class PriceAggregator:
    def __init__(self):
        self.aggregated_prices = {}
        self.unique_pairs = set()

    def run_aggregating_process(self):
        self._set_unique_pairs()
        self._set_aggregated_prices()

    def _set_unique_pairs(self):
        for exchange in CURRENT_PRICES:
            self.unique_pairs |= set(exchange.keys())

    def _set_aggregated_prices(self):
        for pair in self.unique_pairs:
            self.aggregated_prices[pair] = self._get_average_price(pair)

    def _get_average_price(self, pair: str):
        prices_for_current_pair = self._iterate_over_all_exchanges(pair)
        return self._calculate_average_price(prices_for_current_pair)

    @staticmethod
    def _iterate_over_all_exchanges(pair: str) -> list:
        prices_for_current_pair = []
        for exchange in CURRENT_PRICES:
            if pair in exchange:
                prices_for_current_pair.append(float(exchange[pair]))
        return prices_for_current_pair

    @staticmethod
    def _calculate_average_price(prices: list) -> str:
        return str(round(sum(prices) / len(prices), 9))


class ClientRemover:
    def __init__(self, subscriptions: dict):
        self.subscriptions = subscriptions

    def remove_client_from_subscriptions(self, pair: str, websocket: WebSocket):
        try:
            for client in self.subscriptions[pair]:
                if client['websocket'] == websocket:
                    self.subscriptions[pair].remove(client)
        except ValueError:
            pass
