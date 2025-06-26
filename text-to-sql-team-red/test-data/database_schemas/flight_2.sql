CREATE TABLE airlines (
    uid           INTEGER,
    PRIMARY KEY (uid),
    Airline       TEXT,
    Abbreviation  TEXT,
    Country       TEXT   
);
CREATE TABLE airports (
    City           TEXT,
    AirportCode    TEXT,
    PRIMARY KEY (AirportCode),
    AirportName    TEXT,
    Country        TEXT,
    CountryAbbrev  TEXT,
    CONSTRAINT sqlite_autoindex_airports_1 UNIQUE (AirportCode)
);
CREATE TABLE flights (
    Airline        INTEGER,
    FlightNo       INTEGER,
    SourceAirport  TEXT,
    DestAirport    TEXT,
    CONSTRAINT sqlite_autoindex_flights_1 UNIQUE (Airline, FlightNo),
    FOREIGN KEY (DestAirport) REFERENCES airports (AirportCode),
    FOREIGN KEY (SourceAirport) REFERENCES airports (AirportCode),
    PRIMARY KEY (Airline, FlightNo)
);