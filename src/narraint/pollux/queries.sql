SELECT collection, count(*)
From Document
Group by collection


SELECT document_collection, count(*)
From Tag
Group by document_collection