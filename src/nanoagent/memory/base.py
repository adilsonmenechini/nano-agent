class Memory:
    def __init__(self):
        self.storage = {}

    def store(self, key, value):
        self.storage[key] = value

    def retrieve(self, key):
        return self.storage.get(key)

    def delete(self, key):
        if key in self.storage:
            del self.storage[key]

    def list_keys(self):
        return list(self.storage.keys())