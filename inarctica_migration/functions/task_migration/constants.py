# Маппинг пользовательских полей на облачном и коробочном порталах
TASK_USERFIELDS_MAP = {
    'ufAuto131617207625': 'ufAuto799190234932',  # {'title': 'Контактное лицо', 'type': 'string'}
    'ufAuto556846469963': 'ufAuto790884395422',  # {'title': 'NDA', 'type': 'boolean'}
    'ufAuto285941154188': 'ufAuto517320199183',  # {'title': 'Действующий лимит', 'type': 'string'}
    'ufAuto316877964449': 'ufAuto397563154460',  # {'title': 'Тип лимита', 'type': 'string'}
    'ufAuto414772387924': 'ufAuto257104580709',  # {'title': 'Комментарии', 'type': 'string'}
    'ufAuto705474470668': 'ufAuto832497321151',  # {'title': 'Оценка эффекта, млн руб', 'type': 'string'}
    'ufAuto820487235417': 'ufAuto617126887790',  # {'title': 'Аутсорсинг', 'type': 'boolean'}
}

# Перевод из upperCase в camelCase для облачного портала
CLOUD_TASK_USERFIELDS = {
    'UF_AUTO_131617207625': 'ufAuto131617207625',  # {'title': 'Контактное лицо', 'type': 'string'}
    'UF_AUTO_556846469963': 'ufAuto556846469963',  # {'title': 'NDA', 'type': 'boolean'}
    'UF_AUTO_285941154188': 'ufAuto285941154188',  # {'title': 'Действующий лимит', 'type': 'string'}
    'UF_AUTO_316877964449': 'ufAuto397563154460',  # {'title': 'Тип лимита', 'type': 'string'}
    'UF_AUTO_414772387924': 'ufAuto316877964449',  # {'title': 'Комментарии', 'type': 'string'}
    'UF_AUTO_705474470668': 'ufAuto705474470668',  # {'title': 'Оценка эффекта, млн руб', 'type': 'string'}
    'UF_AUTO_820487235417': 'ufAuto820487235417',  # {'title': 'Аутсорсинг', 'type': 'boolean'}
}

# Перевод из camelCase в upperCase для коробочного портала
BOX_TASK_USERFIELDS = {
    'ufAuto799190234932': "UF_AUTO_799190234932",  # {'title': 'Контактное лицо': 'type': 'string'}
    'ufAuto790884395422': 'UF_AUTO_790884395422',  # {'title': 'NDA': 'type': 'boolean'}
    'ufAuto517320199183': "UF_AUTO_517320199183",  # {'title': 'Действующий лимит': 'type': 'string'}
    'ufAuto397563154460': "UF_AUTO_397563154460",  # {'title': 'Тип лимита': 'type': 'string'}
    'ufAuto257104580709': "UF_AUTO_257104580709",  # {'title': 'Комментарии': 'type': 'string'}
    'ufAuto832497321151': "UF_AUTO_832497321151",  # {'title': 'Оценка эффекта: млн руб': 'type': 'string'}
    'ufAuto617126887790': "UF_AUTO_617126887790",  # {'title': 'Аутсорсинг': 'type': 'boolean'}
}
