PRAGMA foreign_keys = ON;

CREATE TABLE "words" (
"key"	INTEGER,
"word"	TEXT NOT NULL UNIQUE,
"mean"	TEXT DEFAULT '? ? ?',
"ref"	INTEGER,
"note"	TEXT,
PRIMARY KEY("key")
);

CREATE TABLE "cat" (
	"key"	INTEGER,
	"word"	INTEGER,
	"cat"	TEXT NOT NULL,
	PRIMARY KEY("key"),
	FOREIGN KEY("word") REFERENCES "words"("key")
);

CREATE INDEX "name_cat_index" ON "cat" (
	"word"
);

CREATE UNIQUE INDEX "name_index" ON "words" (
	"word"
);

CREATE INDEX "ref_index" ON "words" (
	"ref"
);
