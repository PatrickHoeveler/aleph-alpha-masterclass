CREATE TABLE employee (
    Employee_ID  INT,
    PRIMARY KEY (Employee_ID),
    Name         TEXT,
    Age          INT,
    City         TEXT,
    CONSTRAINT sqlite_autoindex_employee_1 UNIQUE (Employee_ID)
);
CREATE TABLE evaluation (
    Employee_ID   TEXT,
    Year_awarded  TEXT,
    Bonus         REAL,
    CONSTRAINT sqlite_autoindex_evaluation_1 UNIQUE (Employee_ID, Year_awarded),
    FOREIGN KEY (Employee_ID) REFERENCES employee (Employee_ID),
    PRIMARY KEY (Employee_ID, Year_awarded)
);
CREATE TABLE hiring (
    Shop_ID       INT,
    Employee_ID   INT,
    PRIMARY KEY (Employee_ID),
    Start_from    TEXT,
    Is_full_time  bool,
    CONSTRAINT sqlite_autoindex_hiring_1 UNIQUE (Employee_ID),
    FOREIGN KEY (Employee_ID) REFERENCES employee (Employee_ID),
    FOREIGN KEY (Shop_ID) REFERENCES shop (Shop_ID)
);
CREATE TABLE shop (
    Shop_ID          INT,
    PRIMARY KEY (Shop_ID),
    Name             TEXT,
    Location         TEXT,
    District         TEXT,
    Number_products  INT,
    Manager_name     TEXT,
    CONSTRAINT sqlite_autoindex_shop_1 UNIQUE (Shop_ID)
);