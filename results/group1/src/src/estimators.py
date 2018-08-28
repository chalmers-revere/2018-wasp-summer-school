

class lowpass:

    def __init__(self, a=0.2):
        self.a = a
        self.y = 0

    def filter(self, y_raw):
        self.y = self.a*y_raw + (1-self.a)*self.y
        return self.y

    
