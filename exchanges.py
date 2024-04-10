import requests
import websockets
import json

# WebSockets URIs
BINANCE_WS_URI = "wss://stream.binance.com:9443/stream?streams=!ticker@arr"
KRAKEN_WS_URI = "wss://ws.kraken.com/"

# REST URIs
KRAKEN_GET_PAIRS_URI = "https://api.kraken.com/0/public/AssetPairs"


AVAILABLE_EXCHANGES = [
    'binance',
    'kraken',
]

BINANCE_CURRENT_PRICES = {}
KRAKEN_CURRENT_PRICES = {}

CURRENT_PRICES = [
    BINANCE_CURRENT_PRICES,
    KRAKEN_CURRENT_PRICES,
]


class ExchangeIntegrator:
    async def connect(self):
        """ Connect to the exchange's websocket. """
        pass

    def _update_current_prices(self, data_about_pairs: dict | list):
        """ Update the current prices of the pairs. """
        pass

    @staticmethod
    def get_sent_data(pair: str) -> dict:
        """ Get the data to be sent to the client. """
        pass


class BinanceIntegrator(ExchangeIntegrator):
    async def connect(self):
        async with websockets.connect(BINANCE_WS_URI) as websocket:
            while True:
                response = await websocket.recv()
                data_about_pairs = json.loads(response)
                self._update_current_prices(data_about_pairs)

    def _update_current_prices(self, data_about_pairs: dict):
        global BINANCE_CURRENT_PRICES
        BINANCE_CURRENT_PRICES |= self._extract_pairs_and_prices(data_about_pairs)

    @staticmethod
    def _extract_pairs_and_prices(data_about_pairs: dict) -> dict:
        return {
            item['s']: str(round((float(item['a']) + float(item['b'])) / 2, 9))
            for item in data_about_pairs['data']
        }

    @staticmethod
    def get_sent_data(pair: str) -> dict:
        return BINANCE_CURRENT_PRICES if pair == 'ALL' else {pair: BINANCE_CURRENT_PRICES[pair]}


class KrakenIntegrator(ExchangeIntegrator):
    async def connect(self):
        async with websockets.connect(KRAKEN_WS_URI) as websocket:
            subscribe_message = self._get_subscribe_message()
            await websocket.send(json.dumps(subscribe_message))

            while True:
                response = await websocket.recv()
                data_about_pairs = json.loads(response)
                if 'event' not in data_about_pairs:
                    self._update_current_prices(data_about_pairs)

    def _get_subscribe_message(self):
        return {
            "event": "subscribe",
            "pair": self._get_kraken_pairs(),
            "subscription": {"name": "ticker"}
        }

    @staticmethod
    def _get_kraken_pairs():
        result = requests.get(KRAKEN_GET_PAIRS_URI).json()['result']

        normalized_pairs = [
            pair_info['wsname'].replace('XBT', 'BTC')
            for pair_info in result.values()
        ]

        return normalized_pairs

    def _update_current_prices(self, data_about_pairs: list):
        global KRAKEN_CURRENT_PRICES
        KRAKEN_CURRENT_PRICES |= self._extract_pair_and_price(data_about_pairs)

    @staticmethod
    def _extract_pair_and_price(data_about_pair: list) -> dict:
        pair = data_about_pair[-1].replace('/', '').replace('XBT', 'BTC')
        bid_and_ask_sum = float(data_about_pair[1]['b'][0]) + float(data_about_pair[1]['a'][0])
        average_price = str(round(bid_and_ask_sum / 2, 9))
        return {pair: average_price}

    @staticmethod
    def get_sent_data(pair: str) -> dict:
        return KRAKEN_CURRENT_PRICES if pair == 'ALL' else {pair: KRAKEN_CURRENT_PRICES[pair]}


EXCHANGE_INTEGRATORS = [
    BinanceIntegrator(),
    KrakenIntegrator(),
]


EXCHANGE_DATA_GETTER = {
    'binance': BinanceIntegrator.get_sent_data,
    'kraken': KrakenIntegrator.get_sent_data,
}
