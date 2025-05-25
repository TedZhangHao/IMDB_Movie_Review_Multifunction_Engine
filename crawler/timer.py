import time
 
class Stagetimer:
    def __init__(self): 
        self.time = {}
        self.last = time.perf_counter()
    
    def mark(self, name=None):
        """record last mark to current time"""
        now = time.perf_counter()
        self.time[name] = now - self.last
        self.last = now
    
    def report(self):
        total_time = sum(self.time.values())
        print("stage consume: \n")
        for name, time in self.time.items():
            print(f"{name}:{time:.3f}s")
        print(f"total:{total_time:.3f}s")
        