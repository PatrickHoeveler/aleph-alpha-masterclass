CREATE TABLE concert (
    concert_ID    INT,
    PRIMARY KEY (concert_ID),
    concert_Name  TEXT,
    Theme         TEXT,
    Stadium_ID    TEXT,
    Year          TEXT,
    CONSTRAINT sqlite_autoindex_concert_1 UNIQUE (concert_ID),
    FOREIGN KEY (Stadium_ID) REFERENCES stadium (Stadium_ID)
);
CREATE TABLE singer (
    Singer_ID          INT,
    PRIMARY KEY (Singer_ID),
    Name               TEXT,
    Country            TEXT,
    Song_Name          TEXT,
    Song_release_year  TEXT,
    Age                INT,
    Is_male            bool,
    CONSTRAINT sqlite_autoindex_singer_1 UNIQUE (Singer_ID)
);
CREATE TABLE singer_in_concert (
    concert_ID  INT,
    Singer_ID   TEXT,
    CONSTRAINT sqlite_autoindex_singer_in_concert_1 UNIQUE (concert_ID, Singer_ID),
    FOREIGN KEY (Singer_ID) REFERENCES singer (Singer_ID),
    FOREIGN KEY (concert_ID) REFERENCES concert (concert_ID),
    PRIMARY KEY (concert_ID, Singer_ID)
);
CREATE TABLE stadium (
    Stadium_ID  INT,
    PRIMARY KEY (Stadium_ID),
    Location    TEXT,
    Name        TEXT,
    Capacity    INT,
    Highest     INT,
    Lowest      INT,
    Average     INT,
    CONSTRAINT sqlite_autoindex_stadium_1 UNIQUE (Stadium_ID)
);