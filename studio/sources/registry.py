from .beaches import BeachesConnector
from .weather import WeatherConnector
from .restaurants import RestaurantsConnector
from .neighborhoods import NeighborhoodsConnector
from .climate_normals import ClimateNormalsConnector
from .water_temperature import WaterTemperatureConnector
from .storm_proximity import StormProximityConnector
from .bookdirect_lodging import BookDirectLodgingConnector


class ConnectorRegistry:
    def __init__(self, connectors):
        self.connectors = tuple(connectors)
        if len({connector.name for connector in self.connectors}) != len(self.connectors):
            raise ValueError("Connector adları benzersiz olmalı.")

    def for_source(self, source):
        matches = [connector for connector in self.connectors if connector.supports(source)]
        if len(matches) > 1:
            raise ValueError("Bir kaynak birden fazla connector ile eşleşti.")
        return matches[0] if matches else None

    def by_name(self, name):
        return next((connector for connector in self.connectors if connector.name == name), None)


DEFAULT_REGISTRY = ConnectorRegistry([BeachesConnector(), WeatherConnector(), RestaurantsConnector(), NeighborhoodsConnector(),
                                     ClimateNormalsConnector(), WaterTemperatureConnector(), StormProximityConnector(),
                                     BookDirectLodgingConnector()])
