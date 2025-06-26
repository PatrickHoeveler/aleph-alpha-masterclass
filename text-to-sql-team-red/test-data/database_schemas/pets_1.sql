CREATE TABLE Has_Pet (
    StuID  INTEGER,
    PetID  INTEGER,
    FOREIGN KEY (StuID) REFERENCES Student (StuID),
    FOREIGN KEY (PetID) REFERENCES Pets (PetID)
);
CREATE TABLE Pets (
    PetID    INTEGER,
    PRIMARY KEY (PetID),
    PetType  VARCHAR(20),
    pet_age  INTEGER,
    weight   REAL       
);
CREATE TABLE Student (
    StuID      INTEGER,
    PRIMARY KEY (StuID),
    LName      VARCHAR(12),
    Fname      VARCHAR(12),
    Age        INTEGER,
    Sex        VARCHAR(1),
    Major      INTEGER,
    Advisor    INTEGER,
    city_code  VARCHAR(3) 
);