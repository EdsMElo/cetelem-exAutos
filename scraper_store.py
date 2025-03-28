import threading

# Dicionário para armazenar os scrapers ativos
scrapers = {}
scrapers_lock = threading.Lock()
