from translitua import *
from utils import custom_logger
from utils import file_manager
from pathlib import Path

class Transliterator:
    def __init__(self):
        self.__logger = custom_logger.get_logger("Transliterator")
        self.__fm = file_manager.FileManager()
        self.official_transliteration_table = UkrainianKMU
        self.uk_translit_tables = {"uk_en": {
                                            "Ukrainian_Simple": UkrainianSimple,
                                            "Ukrainian_WWS": UkrainianWWS,
                                            "Ukrainian_British": UkrainianBritish,
                                            "Ukrainian_BGN": UkrainianBGN,
                                            "Ukrainian_ISO9": UkrainianISO9,
                                            "Ukrainian_GOST1971": UkrainianGOST1971,
                                            "Ukrainian_GOST1986": UkrainianGOST1986,
                                            "Ukrainian_Passport2007": UkrainianPassport2007,
                                            "Ukrainian_National1996": UkrainianNational1996,
                                            "Ukrainian_Passport2004Alt": UkrainianPassport2004Alt
                                            },
                                    "uk_gr" : {"Ukrainian_German": UkrainianGerman},
                                    "uk_fr" : {"Ukrainian_French": UkrainianFrench,}
                            }

    @staticmethod
    def _titlecase(name: str) -> str:
        """
        Capitalise only the first letter, lower-casing the rest.

        Equivalent to str.capitalize() but applied explicitly so the intent is
        clear: 'ОЛЕКСАНДРА' -> 'Олександра'. Crucially this does NOT break on
        apostrophes the way str.title() does, so Ukrainian names keep a single
        capital: "АВЕР'ЯН" -> "Авер'ян", 'ДЕМ’ЯН' -> 'Дем’ян' (both straight '
        and curly ’ apostrophes occur in the source).
        """
        name = name.strip()
        if not name:
            return name
        return name[:1].upper() + name[1:].lower()

    def transliterate_name(self, text: str) -> dict:
        #UkrainianKMU is considered as the official transliteration standard, while the others are unofficial variants that were used before
        official_transliteration =  translit(text, table=self.official_transliteration_table, preserve_case=True) 
        unofficial_transliteration = dict()
        for kind, tables in self.uk_translit_tables.items():
            unofficial_transliteration[kind] = list(set(translit(text, table=table, preserve_case=True) for table in tables.values()))
        transliteration_dict = {"official_transliteration" : official_transliteration,
                                 "unofficial_transliteration" : unofficial_transliteration}
        return transliteration_dict
    
    def transliterate_entry(self, entry:dict, target_keys:tuple) -> dict:
        transliterated_entry = {"id": entry["entry_id"]}
        for key in target_keys:
            transliterated_entry[key] = dict()
            if entry[key] and isinstance(entry[key], str):
                name = self._titlecase(entry[key])
                transliterated_entry[key].update({name: self.transliterate_name(name)})
            elif entry[key] and isinstance(entry[key], list):
                for name in entry[key]:
                    name = self._titlecase(name)
                    transliterated_entry[key].update({name: self.transliterate_name(name)})
        return transliterated_entry
                
    
    def transliterate_names(self, input_path:Path, output_path:Path, name:str, target_keys:tuple) -> None:
        try:
            data = self.__fm.jsonl2dict(input_path)
            transliterated_data = list()
            for entry in data:
                transliterated_data.append(self.transliterate_entry(entry, target_keys))
            self.__fm.dict2jsonl(transliterated_data, output_path, name)
        except Exception as e:
            self.__logger.error(e)