import time, json, os

class LogBuffer:
    def __init__(self, max_size=100):
        self.buffer = []
        self.max_size = max_size

    def truncate(self):
        self.buffer = self.buffer[-self.max_size:]

    def add(self, msg):
        self.buffer.append({
            "time": int(time.time()),
            "msg": msg
        })
        self.truncate()
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def load_from_file(self, path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.buffer.extend(loaded)
                    self.truncate()
                    return True
            return False
        except Exception as e:
            print(f"Error loading log: {e}")
            return False

log_buffer = LogBuffer()

def add_log(msg):
    log_buffer.add(msg)