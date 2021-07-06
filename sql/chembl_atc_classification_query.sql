select chembl_id, ac.level4, ac.level4_description
from molecule_dictionary md
join molecule_atc_classification mac on md.molregno = mac.molregno
join atc_classification ac on mac.level5 = ac.level5
